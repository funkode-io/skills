#!/usr/bin/env python3
"""Run a panel of isolated Claude reviewers over a PR branch, then a checker.

  review-panel.py plan    --repo DIR --ledger FILE [--base main]
  review-panel.py run     --repo DIR --ledger FILE --model M --reviewers a,b,... [options]
  review-panel.py post    --repo DIR --ledger FILE --pr N|URL [--out DIR] [--dry-run]
  review-panel.py fixed   --ledger FILE --commit SHA "finding title" ...
  review-panel.py decline --ledger FILE --reason WHY "finding title" ...

`plan` prints the facts the caller chooses reviewers from (JSON). `run` prints the
verdict line first, then the findings, and records the round in the ledger. `post`
publishes the round in DIR as one pull request review (verdict in the body, one inline
comment per finding) and replies in the threads of findings since `fixed` or declined.
Exit codes: 0 verdict printed or posted, 2 panel incomplete or review refused (ledger
untouched), 3 round limit, 1 usage or setup error.
"""
import argparse
import concurrent.futures
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROMPTS = os.path.join(HERE, "reviewers")
ALWAYS = ["correctness", "attacker", "smells"]
OPTIONAL = ["spec", "security", "data", "ui", "rules"]
MAX_ROUND = 5
VERDICTS = {
    "red": "🔴 Changes required",
    "yellow": "🟡 Changes recommended",
    "blue": "🔵 Needs a closer look",
    "green": "🟢 Approval recommended",
}
# Path hints only; the caller's assessment decides. Topic matching for Rules uses applyTo.
HINTS = {
    "security": r"auth|login|session|token|secret|crypt|password|permission|telegram|bot|webhook|"
                r"handler|route|api/|parse|deserial|upload|cors|csrf|\.env",
    "data": r"migration|\.sql$|schema|events?[/_.]|event_?store|repositor|ledger|balance|price|"
            r"money|amount|decimal|fee|pnl",
    "ui": r"\.(html|css|scss|tsx|jsx|vue|svelte)$|templates/|assets/|web/|ui/|static/",
}
RULE_FILES = ["AGENTS.md", "CLAUDE.md", ".github/copilot-instructions.md"]
SPEC_GLOBS = ["GLOSSARY.md", "CONTEXT.md", "docs/adr/*.md", "docs/adrs/*.md", "adr/*.md",
                   "docs/decisions/*.md"]

FINDING = {
    "type": "object",
    "required": ["title", "severity", "file", "line", "problem", "evidence"],
    "properties": {
        "title": {"type": "string"},
        "severity": {"enum": ["blocking", "note"]},
        "file": {"type": "string"},
        "line": {"type": "integer"},
        "problem": {"type": "string"},
        "evidence": {"type": "string", "description": "quoted line, spec line, rule, or reasoning"},
        "proof": {"type": "object", "properties": {"command": {"type": "string"},
                                                   "output": {"type": "string"}}},
        "preexisting": {"type": "boolean", "description": "true when the bug is not in this diff"},
        "suggestion": {
            "type": "object", "required": ["start_line", "end_line", "replacement"],
            "description": "only when the whole fix is replacing these lines of `file` at HEAD",
            "properties": {"start_line": {"type": "integer"}, "end_line": {"type": "integer"},
                           "replacement": {"type": "string", "description": "the new text of "
                                           "those lines, complete and indented; empty deletes"}}},
    },
}
REVIEWER_SCHEMA = {
    "type": "object",
    "required": ["findings"],
    "properties": {
        "findings": {"type": "array", "items": FINDING},
        "safety_fact": {"type": "string"},
        "attention": {"type": "array", "items": {"type": "string"}},
    },
}
CHECKER_SCHEMA = {
    "type": "object",
    "required": ["findings", "preexisting", "attention", "dropped"],
    "properties": {
        "findings": {"type": "array", "items": {**FINDING, "properties": {
            **FINDING["properties"], "reviewers": {"type": "array", "items": {"type": "string"}},
            "same_as": {"type": "string", "description": "title of the open earlier finding this "
                                                         "repeats"}}}},
        "preexisting": {"type": "array", "items": {
            "type": "object", "required": ["title", "file", "line", "problem", "effort", "fix"],
            "properties": {"title": {"type": "string"}, "file": {"type": "string"},
                           "line": {"type": "integer"}, "problem": {"type": "string"},
                           "effort": {"enum": ["easy", "hard"]}, "fix": {"type": "string"}}}},
        "attention": {"type": "array", "items": {"type": "string"}},
        "dropped": {"type": "array", "items": {
            "type": "object", "properties": {"title": {"type": "string"},
                                             "reason": {"type": "string"}}}},
    },
}


def die(msg, code=1):
    print("review-panel: " + msg, file=sys.stderr)
    sys.exit(code)


def git(repo, *args, stdin=None):
    r = subprocess.run(["git", "-C", repo, *args], input=stdin, capture_output=True, text=True)
    if r.returncode != 0:
        die("git %s: %s" % (" ".join(args), r.stderr.strip()))
    return r.stdout


def patch_id(repo, diff):
    out = git(repo, "patch-id", "--stable", stdin=diff).split()
    return out[0] if out else ""


def load_ledger(path):
    if not os.path.exists(path):
        return {"round": 0, "declined": []}
    with open(path) as f:
        ledger = json.load(f)
    ledger.setdefault("round", 0)
    ledger.setdefault("declined", [])
    return ledger


def save_ledger(path, ledger):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, path)


def glob_match(path, pattern):
    """applyTo glob: `**` spans directories; a pattern without `/` matches the basename."""
    pattern = pattern.strip()
    if not pattern:
        return False
    rx = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            rx += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            rx += ".*"
            i += 2
        elif pattern[i] == "*":
            rx += "[^/]*"
            i += 1
        elif pattern[i] == "?":
            rx += "[^/]"
            i += 1
        else:
            rx += re.escape(pattern[i])
            i += 1
    target = path if "/" in pattern else os.path.basename(path)
    return re.fullmatch(rx, target) is not None


def same_or_import(repo, a, b):
    """True when b repeats a or only imports it (`@AGENTS.md`)."""
    with open(os.path.join(repo, a), encoding="utf-8") as fa, open(os.path.join(repo, b),
                                                                   encoding="utf-8") as fb:
        ta, tb = fa.read(), fb.read()
    return ta == tb or tb.strip() == "@" + a


def apply_to(text):
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    if not m:
        return None
    lines = m.group(1).splitlines()
    for i, line in enumerate(lines):
        if line.strip().startswith("applyTo:"):
            value = line.split(":", 1)[1].strip()
            if value:  # one line: "a,b" or ["a", "b"]
                value = value.strip("[]")
                return [g.strip().strip("'\"") for g in value.split(",") if g.strip()]
            globs = []  # YAML list on the following lines
            for item in lines[i + 1:]:
                if not item.strip().startswith("-"):
                    break
                globs.append(re.sub(r"\s+#.*$", "", item.strip()[1:].strip()).strip("'\""))
            return globs or None
    return None


def rule_topics(repo, files):
    """Deterministic: repo-wide rules plus every applyTo file that a changed path matches."""
    topics = []
    wide = [p for p in RULE_FILES if os.path.isfile(os.path.join(repo, p))]
    if "AGENTS.md" in wide and "CLAUDE.md" in wide and same_or_import(repo, "AGENTS.md", "CLAUDE.md"):
        wide.remove("CLAUDE.md")
    # Nested AGENTS.md / CLAUDE.md in a changed file's ancestor directories are path-scoped too.
    for f in files:
        d = os.path.dirname(f)
        while d:
            for name in ("AGENTS.md", "CLAUDE.md"):
                p = os.path.join(d, name)
                if os.path.isfile(os.path.join(repo, p)) and p not in wide:
                    wide.append(p)
            d = os.path.dirname(d)
    topics.append({"topic": "repo-wide", "rules": wide, "files": files})
    idir = os.path.join(repo, ".github", "instructions")
    if os.path.isdir(idir):
        for name in sorted(os.listdir(idir)):
            if not name.endswith(".md"):
                continue
            rel = ".github/instructions/" + name
            with open(os.path.join(idir, name), encoding="utf-8") as fh:
                globs = apply_to(fh.read())
            if not globs:
                continue
            if globs == ["**"] or all(g.strip() == "**" for g in globs):
                # Applies to every path (commit messages, PR bodies); fold into repo-wide.
                topics[0]["rules"].append(rel)
                continue
            hit = [f for f in files if any(glob_match(f, g) for g in globs)]
            if hit:
                topics.append({"topic": name[:-len(".instructions.md")] if name.endswith(
                    ".instructions.md") else name[:-3], "rules": [rel], "files": hit})
    return [t for t in topics if t["rules"]]


_TRACKED = {}


def spec_docs(repo):
    """The standing spec: the glossary and the decision records."""
    return sorted(p for p in tracked(repo) if any(fnmatch.fnmatch(p, g) for g in SPEC_GLOBS))


def tracked(repo):
    if repo not in _TRACKED:
        _TRACKED[repo] = git(repo, "ls-files").splitlines()
    return _TRACKED[repo]


def facts(repo, base, ledger):
    git(repo, "fetch", "-q", "origin", base)
    base_ref = "origin/" + base
    base_sha = git(repo, "merge-base", base_ref, "HEAD").strip()
    head = git(repo, "rev-parse", "HEAD").strip()
    files = [f for f in git(repo, "diff", "--name-only", base_ref + "...HEAD").splitlines() if f]
    if not files:
        die("no changes against %s" % base_ref)
    diff = git(repo, "diff", base_ref + "...HEAD")
    per_file = {f: patch_id(repo, git(repo, "diff", base_ref + "...HEAD", "--", f)) for f in files}
    pid = patch_id(repo, diff)
    last = ledger.get("files", {})
    changed = [f for f in files if per_file[f] != last.get(f)]
    only_merges = False
    if ledger.get("head") and ledger["head"] != head:
        r = subprocess.run(["git", "-C", repo, "rev-list", "--no-merges", ledger["head"] + "..HEAD",
                            "^" + base_ref], capture_output=True, text=True)
        only_merges = r.returncode == 0 and not r.stdout.split()
    nxt = ledger.get("round", 0) + 1
    # Scope: rounds 1-2 review the whole diff; 3+ or a pure main-merge only the files whose own
    # change moved since the last reviewed round.
    scope = files if nxt <= 2 and not only_merges else changed
    hints = {k: [f for f in files if re.search(rx, f, re.I)] for k, rx in HINTS.items()}
    return {
        "base": base, "base_sha": base_sha, "head": head, "patch_id": pid,
        "files": files, "per_file": per_file, "changed_since_last": changed,
        "only_merges_since_last": only_merges, "round": nxt, "scope": scope,
        "blocking_only": nxt >= 3,
        "skip": bool(ledger.get("patch_id")) and ledger["patch_id"] == pid,
        "last_verdict": ledger.get("verdict"), "last_round": ledger.get("round", 0),
        "path_hints": {k: v for k, v in hints.items() if v},
        "rule_topics": rule_topics(repo, files),
        "spec_docs": spec_docs(repo),
        "_diff": diff,
    }


def cmd_plan(a):
    f = facts(a.repo, a.base, load_ledger(a.ledger))
    f.pop("_diff")
    f.pop("per_file")
    json.dump(f, sys.stdout, indent=2)
    print()


def cmd_outcome(a):
    """Record what the author did with a finding; `post` says it in the finding's thread."""
    ledger = load_ledger(a.ledger)
    threads = [t for t in ledger.get("threads", []) if t.get("outcome") != "fixed"]
    for title in a.titles:
        hit = [t for t in threads if t["title"] == title]
        if a.cmd == "fixed" and not hit:
            die("no open finding titled %r; open: %s" % (title, "; ".join(
                t["title"] for t in threads) or "none"))
        if a.cmd == "decline" and title not in ledger["declined"]:
            ledger["declined"].append(title)
        for t in hit:
            t["outcome"] = "fixed" if a.cmd == "fixed" else "declined"
            t["say"] = "Fixed in %s." % a.commit if a.cmd == "fixed" else "Declined: " + a.reason
    save_ledger(a.ledger, ledger)


def scratch_copy(repo, dest, head, base, base_sha):
    """A throwaway clone at HEAD: no untracked files, no worker notes, no session state."""
    subprocess.run(["git", "clone", "-q", "--shared", "--no-checkout", repo, dest], check=True)
    git(dest, "checkout", "-q", "--detach", head)
    git(dest, "update-ref", "refs/remotes/origin/" + base, base_sha)
    return dest


def login_dir():
    return os.path.abspath(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude"))


def isolated_env():
    """The caller's Claude login and nothing else of its environment."""
    keep = ("PATH", "HOME", "USER", "LOGNAME", "SHELL", "LANG", "LC_ALL", "TERM", "TMPDIR")
    env = {k: os.environ[k] for k in keep if k in os.environ}
    if os.environ.get("CLAUDE_CONFIG_DIR"):
        env["CLAUDE_CONFIG_DIR"] = login_dir()
    env.update({
        "CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1",
        "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
    })
    return env


READ_ONLY = ["Read", "Grep", "Glob", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git show:*)",
             "Bash(git blame:*)", "Bash(git grep:*)"]
EXEC = ["Read", "Grep", "Glob", "Bash", "Edit", "Write"]
# Exec sessions run Bash in Claude Code's sandbox: writes stay in the clone and toolchain caches,
# network only to package registries, and the Claude login directory is unreadable.
CACHES = ["~/.cargo", "~/.rustup", "~/.npm", "~/.cache", "~/go", "~/.gradle", "~/.m2",
          "~/Library/Caches"]
REGISTRIES = ["crates.io", "index.crates.io", "static.crates.io", "static.rust-lang.org",
              "registry.npmjs.org", "pypi.org", "files.pythonhosted.org", "proxy.golang.org",
              "sum.golang.org", "repo.maven.apache.org", "github.com", "codeload.github.com",
              "objects.githubusercontent.com"]


def session_settings(a, sandboxed):
    """Deny the Claude login to every session's file tools; exec sessions also sandbox Bash.

    Read-only sessions run their git commands unsandboxed, and `git blame --contents <file>` or a
    command substitution in a path still reads any file: sandboxing them too is the open fix.
    """
    login = login_dir()
    settings = {"permissions": {"deny": ["Read(/%s/**)" % login, "Edit(/%s/**)" % login]}}
    if sandboxed:
        caches = [os.path.expanduser(c) for c in CACHES if os.path.isdir(os.path.expanduser(c))]
        settings["sandbox"] = {
            "enabled": True, "failIfUnavailable": True, "autoAllowBashIfSandboxed": True,
            "allowUnsandboxedCommands": False,
            "filesystem": {"denyRead": [login], "allowWrite": caches},
            "network": {"allowedDomains": REGISTRIES + a.allow_domain}}
    return json.dumps(settings)


def run_claude(job, a):
    """One fresh `claude -p` process; returns (name, parsed JSON or None, error, seconds)."""
    name = job["name"]
    tools = job.get("tools", READ_ONLY)
    argv = ["claude", "-p", "--no-session-persistence", "--setting-sources", "",
            "--strict-mcp-config", "--model", a.model, "--effort", job["effort"],
            "--permission-mode", "dontAsk", "--output-format", "json",
            "--tools", ",".join(sorted({t.split("(")[0] for t in tools})),
            "--allowedTools", *tools,
            "--json-schema", json.dumps(job["schema"]),
            "--append-system-prompt", job["system"],
            "--settings", session_settings(a, tools is EXEC)]
    for d in [a.inputs] + job.get("add_dirs", []):
        argv += ["--add-dir", d]
    log = os.path.join(a.out, name + ".json")
    start = time.time()
    try:
        # The prompt goes on stdin: a positional after variadic --add-dir would be read as a dir.
        r = subprocess.run(argv, cwd=job["cwd"], env=isolated_env(), input=job["prompt"],
                           capture_output=True, text=True, timeout=a.timeout)
        raw = r.stdout
        err = r.stderr if r.returncode else ""
    except subprocess.TimeoutExpired:
        raw, err = "", "timeout after %ss" % a.timeout
    with open(log, "w") as fh:
        fh.write(raw or err)
    return name, parse(raw), err or failure(raw), round(time.time() - start)


def failure(raw):
    """What claude said went wrong (not logged in, usage limit) when it exits 0 with an error."""
    try:
        env = json.loads(raw)
    except (ValueError, TypeError):
        return ""
    if not (isinstance(env, dict) and env.get("is_error")):
        return ""
    return str(env.get("result") or "claude reported an error")


def parse(raw):
    try:
        env = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if isinstance(env, dict) and env.get("is_error"):
        return None
    out = env.get("structured_output") if isinstance(env, dict) else None
    if out is None and isinstance(env, dict):
        text = env.get("result", "")
        blocks = re.findall(r"```(?:json)?\s*\n(.*?)\n\s*```", text, re.S)
        for cand in reversed(blocks or [text]):
            try:
                out = json.loads(cand)
                break
            except ValueError:
                continue
    return out if isinstance(out, dict) and "findings" in out else None


def prompt_file(name):
    with open(os.path.join(PROMPTS, name + ".md"), encoding="utf-8") as fh:
        return fh.read()


def common_context(f, issue_path, declined):
    lines = [
        "You are one reviewer on an independent panel. You did not write this change and know "
        "nothing about it beyond what is in the repository and the files named here.",
        "The change: `git diff origin/%s...HEAD` in the current directory (also saved at %s)."
        % (f["base"], f["_diff_path"]),
        "Round %d. Files in scope: %s." % (f["round"], ", ".join(f["scope"])),
    ]
    if f["blocking_only"]:
        lines.append("This is round 3 or later: report blocking findings only.")
    if issue_path:
        lines.append("The linked issue is at %s." % issue_path)
    if declined:
        lines.append("Already declined by the author; re-raise only with new evidence: "
                     + "; ".join(declined))
    lines.append("When the whole fix is replacing a few lines of one changed file, give it as "
                 "`suggestion`; the checker applies it and keeps it only when it works.")
    return "\n".join(lines)


def build_jobs(a, f, issue_path, work, declined):
    effort = "high" if f["round"] <= 2 else "medium"
    ro = scratch_copy(a.repo, os.path.join(work, "tree"), f["head"], f["base"], f["base_sha"])
    ctx = common_context(f, issue_path, declined)
    jobs = []
    for name in a.reviewers:
        if name == "rules":
            continue
        job = {"name": name, "effort": effort, "schema": REVIEWER_SCHEMA, "cwd": ro,
               "system": ctx + "\n\n" + prompt_file(name),
               "prompt": "Review the change as your brief says and answer in the JSON schema."}
        if name == "attacker":
            job["cwd"] = scratch_copy(a.repo, os.path.join(work, "attack"), f["head"], f["base"],
                                      f["base_sha"])
            job["tools"] = EXEC
        if name == "spec":
            job["system"] += "\n\nGlossary and decision records: %s." % (
                ", ".join(f["spec_docs"]) or "none")
        if name == "ui":
            job["add_dirs"] = [d for d in (os.path.dirname(os.path.abspath(a.prototype)),
                                          a.screenshots) if d]
            job["system"] += "\n\nApproved prototype: %s\nScreenshots of the change: %s" % (
                os.path.abspath(a.prototype), a.screenshots or "none given; say so as attention")
        jobs.append(job)
    seen = set()
    if "rules" in a.reviewers:
        topics = f["rule_topics"] + [{"topic": os.path.basename(t), "rules": [t],
                                      "files": f["scope"]} for t in a.topics]
        for t in topics:
            in_scope = [x for x in t["files"] if x in f["scope"]]
            if not in_scope:
                continue
            slug = "rules-" + re.sub(r"[^a-z0-9-]+", "-", t["topic"].lower())
            name, n = slug, 2
            while name in seen:
                name, n = "%s-%d" % (slug, n), n + 1
            seen.add(name)
            jobs.append({
                "name": name,
                "effort": effort, "schema": REVIEWER_SCHEMA, "cwd": ro,
                "system": ctx + "\n\n" + prompt_file("rules") + "\n\nYour topic: %s.\nRule files: "
                "%s.\nChanged files this topic covers: %s." % (
                    t["topic"], ", ".join(t["rules"]), ", ".join(in_scope)),
                "prompt": "Check the change against your rule files and answer in the JSON schema."})
    return jobs


def verdict(checked, blocking_only):
    if any(x["severity"] == "blocking" for x in checked["findings"]):
        return "red"
    if not blocking_only and checked["findings"]:
        return "yellow"
    if checked["attention"]:
        return "blue"
    return "green"


def fenced(text, lang=""):
    """A code block whose fence is longer than any backtick run inside it."""
    fence = "`" * max([3] + [len(m) + 1 for m in re.findall(r"`+", text)])
    return "%s%s\n%s\n%s" % (fence, lang, text, fence)


def render(f, colour, checked, timings, inline=None):
    """The round as Markdown. `inline` (a summary line) marks a review body: its findings are the
    ones no inline comment could carry."""
    out = ["### " + VERDICTS[colour], ""]
    out.append("Round %d · %s · patch-id %s · reviewers: %s" % (
        f["round"], f["head"][:12], f["patch_id"][:12],
        ", ".join("%s %ss" % (n, s) for n, s in timings)))
    if inline:
        out += ["", inline]
    if checked["findings"]:
        out += ["", "#### Findings outside the diff" if inline else "#### Findings"]
        for x in checked["findings"]:
            out.append("- **%s** `%s:%s` (%s; %s) — %s" % (
                x["title"], x["file"], x["line"], x["severity"], ", ".join(x.get("reviewers", [])),
                x["problem"]))
            if x.get("evidence"):
                out.append("  - Evidence: %s" % x["evidence"])
            if x.get("proof", {}).get("command"):
                out.append("  - Proof: `%s` → %s" % (x["proof"]["command"],
                                                    x["proof"].get("output", "")[:500]))
            if x.get("suggestion"):
                s = x["suggestion"]
                out.append("  - Suggested lines %d-%d:\n%s" % (
                    s["start_line"], s["end_line"],
                    re.sub(r"(?m)^", "    ", fenced(s["replacement"].rstrip("\n")))))
    if checked["preexisting"]:
        out += ["", "#### Pre-existing bugs (not this PR's change)"]
        for x in checked["preexisting"]:
            act = "fix in this PR with a note" if x["effort"] == "easy" else "propose a follow-up issue"
            out.append("- **%s** `%s:%s` (%s: %s) — %s Fix: %s" % (
                x["title"], x["file"], x["line"], x["effort"], act, x["problem"], x["fix"]))
    if checked["attention"]:
        out += ["", "#### Needs a human look"] + ["- " + x for x in checked["attention"]]
    if checked["dropped"]:
        out += ["", "<details><summary>Dropped by the checker (%d)</summary>" % len(
            checked["dropped"]), ""]
        out += ["- %s — %s" % (x.get("title", "?"), x.get("reason", "")) for x in checked["dropped"]]
        out += ["", "</details>"]
    return "\n".join(out)


def right_lines(diff):
    """{path: [hunk, ...]}, each hunk {line number at HEAD: text}: where GitHub accepts an inline
    comment, which is only on a line inside a hunk of the pull request's diff."""
    files, path, hunk, old, new, n = {}, None, None, 0, 0, 0
    for line in diff.splitlines():
        if old <= 0 and new <= 0:  # between hunks
            if line.startswith("+++ "):
                path = line[6:] if line.startswith("+++ b/") else None  # None: a deleted file
            m = re.match(r"@@ -\d+(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
            if m and path:
                old, n, new = int(m[1] or 1), int(m[2]), int(m[3] or 1)
                hunk = {}
                files.setdefault(path, []).append(hunk)
        elif not line.startswith("\\"):
            if not line.startswith("+"):
                old -= 1
            if not line.startswith("-"):
                hunk[n] = line[1:]
                n, new = n + 1, new - 1
    return files


def anchor(x, files):
    """(first line, last line, suggestion applies) for a finding's inline comment, or None when
    its line is outside the diff. A suggestion applies when its lines sit in one hunk and it
    changes them: GitHub replaces exactly the lines the comment spans."""
    hunks = files.get(x["file"], [])
    s = x.get("suggestion")
    if s and s["start_line"] <= s["end_line"]:
        span = range(s["start_line"], s["end_line"] + 1)
        for h in hunks:
            if all(i in h for i in span) and "\n".join(h[i] for i in span) != s[
                    "replacement"].rstrip("\n"):
                return span[0], span[-1], True
    return next(((x["line"], x["line"], False) for h in hunks if x["line"] in h), None)


def comment_body(x, suggest):
    """One finding as a review comment; `suggest` makes its suggestion a one-click block."""
    label = "%s; %s" % (x["severity"], ", ".join(x.get("reviewers", []))) if x.get(
        "severity") else "pre-existing, %s" % x["effort"]
    out = ["**%s** (%s)" % (x["title"], label), "", x["problem"]]
    if x.get("fix"):
        out += ["", "Fix: " + x["fix"]]
    if x.get("evidence"):
        out += ["", "Evidence: " + x["evidence"]]
    if x.get("proof", {}).get("command"):
        out += ["", "<details><summary>Proof</summary>", "", fenced(x["proof"]["command"], "sh"),
                "", fenced(x["proof"].get("output", "")[:2000]), "", "</details>"]
    s = x.get("suggestion")
    if s and suggest:
        out += ["", fenced(s["replacement"].rstrip("\n"), "suggestion")]
    elif s:
        out += ["", "Proposed lines %d-%d:" % (s["start_line"], s["end_line"]), "",
                fenced(s["replacement"].rstrip("\n"))]
    return "\n".join(out)[:60000]


def gh_api(a, method, endpoint, payload=None):
    """One GitHub API call through gh; with --dry-run a write is printed instead of sent."""
    if a.dry_run and method != "GET":
        a.printed.append({"method": method, "endpoint": endpoint, "body": payload})
        return {}
    r = subprocess.run(["gh", "api", "--method", method, endpoint] + (
        ["--input", "-"] if payload is not None else []),
        input=json.dumps(payload) if payload is not None else None, capture_output=True, text=True)
    if r.returncode != 0:
        refused = "reviews" in endpoint and method == "POST"
        die("gh api %s %s: %s%s" % (method, endpoint, (r.stderr or r.stdout).strip()[:500],
                                    "\nGitHub refused the review; nothing was posted. Rerun with "
                                    "--body-only to post it without inline comments."
                                    if refused else ""), 2 if refused else 1)
    return json.loads(r.stdout) if r.stdout.strip() else {}


THREADS = """query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){pullRequest(number:$n){
reviewThreads(first:100){nodes{id comments(first:1){nodes{databaseId}}}}}}}"""
RESOLVE = "mutation($t:ID!){resolveReviewThread(input:{threadId:$t}){thread{isResolved}}}"


def cmd_post(a):
    a.printed = []
    ledger = load_ledger(a.ledger)
    threads = ledger.setdefault("threads", [])
    try:
        r = subprocess.run(["gh", "pr", "view", a.pr, "--json", "url,headRefOid"] + (
            ["-R", a.pr_repo] if a.pr_repo else []), cwd=a.repo, capture_output=True, text=True)
    except FileNotFoundError:
        die("post needs the gh CLI on PATH")
    if r.returncode != 0:
        die("gh pr view %s: %s" % (a.pr, r.stderr.strip()))
    pr = json.loads(r.stdout)
    # The pull request lives in the base repository, also when its branch is in a fork.
    repo, number = re.search(r"://[^/]+/([^/]+/[^/]+)/pull/(\d+)", pr["url"]).groups()
    pulls = "repos/%s/pulls/%s" % (repo, number)

    rnd = None
    if a.out:
        with open(os.path.join(a.out, "findings.json"), encoding="utf-8") as fh:
            rnd = json.load(fh)
        if rnd["round"] <= ledger.get("posted", 0):
            rnd = None
    loose = [t for t in threads if t.get("say") and not t.get("comment")]
    review, new = None, []
    if rnd:
        if rnd["head"] != pr["headRefOid"]:
            print("review-panel: the PR head moved to %s; comments anchor to the reviewed %s" % (
                pr["headRefOid"][:12], rnd["head"][:12]), file=sys.stderr)
        with open(os.path.join(a.out, "inputs", "change.diff"), encoding="utf-8") as fh:
            files = {} if a.body_only else right_lines(fh.read())
        checked, comments, rest = rnd["checked"], [], {"findings": [], "preexisting": []}
        for kind in ("findings", "preexisting"):
            for x in checked[kind]:
                open_ = [t for t in threads if t["title"] == x.get("same_as") and t.get("comment")
                         and t.get("outcome") != "fixed"]
                if open_:  # the earlier round's thread carries it: reply there, no new thread
                    open_[-1].update(title=x["title"], round=rnd["round"], outcome=None, say="\n\n".join(
                        filter(None, [open_[-1].get("say"), "Still open in round %d." % rnd["round"],
                                      comment_body(x, False)])))
                    continue
                at = anchor(x, files)
                mark = "<!-- review-panel %d.%d -->" % (rnd["round"], len(new))
                new.append({"title": x["title"], "round": rnd["round"], "comment": None,
                            "mark": mark if at else None})
                if not at:
                    rest[kind].append(x)
                    continue
                c = {"path": x["file"], "line": at[1], "side": "RIGHT",
                     "body": comment_body(x, at[2]) + "\n\n" + mark}
                if at[0] != at[1]:
                    c.update(start_line=at[0], start_side="RIGHT")
                comments.append(c)
        total = len(checked["findings"]) + len(checked["preexisting"])
        inline = None if a.body_only or not total else (
            "Inline comments: %d. Continued in earlier threads: %d. Below: %d." % (
                len(comments), total - len(new), len(new) - len(comments)))
        body = render(rnd, rnd["verdict"], {**checked, **rest}, rnd["timings"], inline)
        review = {"commit_id": rnd["head"], "event": "COMMENT", "comments": comments, "body": body}
    elif loose:
        review = {"event": "COMMENT", "comments": [], "body": "### Review panel: earlier findings"}
    if review:
        if loose:
            review["body"] += "\n\n#### Earlier findings without a thread\n" + "\n".join(
                "- **%s** (round %d): %s" % (t["title"], t["round"], t["say"]) for t in loose)
        tag = "<!-- review-panel round %d -->" % rnd["round"] if rnd else ""
        review["body"] = review["body"][:60000] + "\n\n" + tag
        # A review already on the PR for this round (posted, then the ledger write lost) is adopted.
        done = next((r for r in gh_api(a, "GET", pulls + "/reviews?per_page=100")
                     if tag and tag in (r.get("body") or "")), None) if not a.dry_run else None
        done = done or gh_api(a, "POST", pulls + "/reviews", review)
        if not a.dry_run:
            marks = {t["mark"]: t for t in new if t["mark"]}
            for c in gh_api(a, "GET", "%s/reviews/%s/comments?per_page=100" % (pulls, done["id"])):
                for mark, t in marks.items():
                    if mark in c["body"]:
                        t["comment"] = c["id"]
            for t in new:
                del t["mark"]
            for t in loose:
                del t["say"]
            threads += new
            if rnd:
                ledger["posted"] = rnd["round"]
            save_ledger(a.ledger, ledger)
            print(done.get("html_url", ""))

    ids, said = None, 0
    for t in threads:
        if not (t.get("say") and t.get("comment")):
            continue
        gh_api(a, "POST", "%s/comments/%s/replies" % (pulls, t["comment"]), {"body": t["say"]})
        if t.get("outcome"):  # fixed or declined: the thread is settled
            if ids is None:  # thread ids are read, so a dry run names the thread by its comment
                owner, name = repo.split("/")
                got = {} if a.dry_run else gh_api(a, "POST", "graphql", {
                    "query": THREADS, "variables": {"o": owner, "r": name, "n": int(number)}})
                ids = {n["comments"]["nodes"][0]["databaseId"]: n["id"] for n in got.get(
                    "data", {}).get("repository", {}).get("pullRequest", {}).get(
                    "reviewThreads", {}).get("nodes", []) if n["comments"]["nodes"]}
            gh_api(a, "POST", "graphql", {"query": RESOLVE, "variables": {
                "t": ids.get(t["comment"], "<thread of comment %s>" % t["comment"])}})
        said += 1
        if not a.dry_run:
            del t["say"]
            save_ledger(a.ledger, ledger)
    if a.dry_run:
        json.dump(a.printed, sys.stdout, indent=2, ensure_ascii=False)
        print()
    print("review-panel: %s, %d thread replies%s" % (
        "1 review" if review else "no review", said, " (dry run)" if a.dry_run else ""),
        file=sys.stderr)


def cmd_run(a):
    if a.parallel < 1:
        die("--parallel must be at least 1")
    if not a.implementer_model:
        die("--implementer-model is required: the reviewer model must differ from it")
    if a.implementer_model == a.model:
        die("reviewer model must differ from the implementer's (%s)" % a.model)
    if a.prototype and not os.path.isfile(a.prototype):
        die("prototype not found: %s" % a.prototype)
    chosen = [r.strip() for r in a.reviewers.split(",") if r.strip()]
    unknown = [r for r in chosen if r not in ALWAYS + OPTIONAL]
    if unknown:
        die("unknown reviewers: %s" % ", ".join(unknown))
    if "ui" in chosen and not a.prototype:
        die("ui needs --prototype (the approved prototype HTML)")
    a.reviewers = ALWAYS + [r for r in OPTIONAL if r in chosen]
    ledger = load_ledger(a.ledger)
    f = facts(a.repo, a.base, ledger)
    if "spec" in chosen and not (a.issue or f["spec_docs"]):
        die("spec needs --issue (the linked issue) or a glossary or decision record in the repo")
    if f["skip"] and not a.force:
        print("### " + VERDICTS.get(ledger.get("verdict"), "🔵 Needs a closer look"))
        print("\nNo re-review: the PR's own change (patch-id %s) is unchanged since round %d."
              % (f["patch_id"][:12], ledger["round"]))
        return 0
    if f["round"] > MAX_ROUND and not a.force:
        print("### 🔵 Needs a closer look\n\nRound %d done without convergence; the owner decides "
              "whether to continue (rerun with --force)." % MAX_ROUND)
        return 3
    if not f["scope"] and a.force:
        f["scope"] = f["files"]
    if not f["scope"]:
        die("nothing in scope: no file's own change moved since round %d" % ledger["round"])
    a.out = os.path.abspath(a.out or tempfile.mkdtemp(prefix="review-panel-"))
    # Reviewers see only the inputs dir; a.out also holds the other reviewers' answers.
    a.inputs = os.path.join(a.out, "inputs")
    os.makedirs(a.inputs, exist_ok=True)
    work = tempfile.mkdtemp(prefix="review-panel-work-")
    try:
        f["_diff_path"] = os.path.join(a.inputs, "change.diff")
        with open(f["_diff_path"], "w") as fh:
            fh.write(f["_diff"])
        issue_path = None
        if a.issue:
            issue_path = os.path.join(a.inputs, "issue.md")
            try:
                r = subprocess.run(["gh", "issue", "view", a.issue, "--json", "title,body"] + (
                    ["-R", a.issue_repo] if a.issue_repo else []),
                    cwd=a.repo, capture_output=True, text=True)
            except FileNotFoundError:
                die("--issue needs the gh CLI on PATH")
            if r.returncode != 0:
                die("gh issue view %s: %s (check `gh auth status` and --issue-repo)" % (
                    a.issue, r.stderr.strip()))
            iss = json.loads(r.stdout)
            with open(issue_path, "w") as fh:
                fh.write("# %s\n\n%s\n" % (iss["title"], iss["body"]))
        jobs = build_jobs(a, f, issue_path, work, ledger.get("declined", []))
        print("review-panel: round %d, %d sessions: %s" % (
            f["round"], len(jobs), ", ".join(j["name"] for j in jobs)), file=sys.stderr)
        if a.dry_run:
            for j in jobs:
                print("%s: cwd=%s effort=%s tools=%s prompt=%r" % (
                    j["name"], j["cwd"], j["effort"], ",".join(j.get("tools", READ_ONLY)),
                    j["prompt"]))
            return 0
        results, timings, failed = {}, [], []
        with concurrent.futures.ThreadPoolExecutor(max_workers=a.parallel) as pool:
            for name, out, err, secs in pool.map(lambda j: run_claude(j, a), jobs):
                timings.append((name, secs))
                if out is None:
                    failed.append("%s (%s)" % (name, (err or "unparseable output").strip()[:200]))
                else:
                    results[name] = out
        if failed:
            print("### ⚠ Panel incomplete\n\nNo verdict; ledger untouched. Failed: %s. Raw output "
                  "in %s." % ("; ".join(failed), a.out))
            return 2
        panel = os.path.join(a.out, "checker-input")
        os.makedirs(panel, exist_ok=True)
        with open(os.path.join(panel, "panel.json"), "w") as fh:
            json.dump(results, fh, indent=2, ensure_ascii=False)
        ctx = common_context(f, issue_path, ledger.get("declined", []))
        check = {"name": "checker", "effort": "high" if f["round"] <= 2 else "medium",
                 "schema": CHECKER_SCHEMA, "tools": EXEC,
                 "cwd": scratch_copy(a.repo, os.path.join(work, "check"), f["head"], f["base"],
                                     f["base_sha"]),
                 "system": ctx + "\n\n" + prompt_file("checker") + "\n\nThe panel's raw findings: "
                 + os.path.join(panel, "panel.json") + "\n\nOpen findings from earlier rounds: "
                 + json.dumps([t["title"] for t in ledger.get("threads", [])
                               if t.get("outcome") != "fixed"], ensure_ascii=False),
                 "add_dirs": [panel],
                 "prompt": "Check the panel's findings as your brief says and answer in the JSON "
                           "schema."}
        name, checked, err, secs = run_claude(check, a)
        timings.append((name, secs))
        if checked is None:
            print("### ⚠ Panel incomplete\n\nNo verdict; ledger untouched. Checker failed: %s. Raw "
                  "output in %s." % ((err or "unparseable output").strip()[:200], a.out))
            return 2
        for k in ("preexisting", "attention", "dropped"):
            checked.setdefault(k, [])
        if f["blocking_only"]:
            checked["findings"] = [x for x in checked["findings"] if x["severity"] == "blocking"]
        colour = verdict(checked, f["blocking_only"])
        report = render(f, colour, checked, timings)
        with open(os.path.join(a.out, "report.md"), "w") as fh:
            fh.write(report + "\n")
        with open(os.path.join(a.out, "findings.json"), "w") as fh:  # what `post` publishes
            json.dump({"round": f["round"], "head": f["head"], "patch_id": f["patch_id"],
                       "verdict": colour, "timings": timings, "checked": checked}, fh, indent=2,
                      ensure_ascii=False)
        print(report)
        ledger.update({"round": f["round"], "patch_id": f["patch_id"], "head": f["head"],
                       "base_sha": f["base_sha"], "files": f["per_file"], "verdict": colour})
        save_ledger(a.ledger, ledger)
        return 0
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("plan", "run"):
        s = sub.add_parser(name)
        s.add_argument("--repo", required=True, help="the PR branch's checkout")
        s.add_argument("--base", default="main")
        s.add_argument("--ledger", required=True, help="JSON ledger file the caller keeps")
    r = sub.choices["run"]
    r.add_argument("--reviewers", required=True,
                   help="comma list; correctness, attacker and smells are always added")
    r.add_argument("--model", default=os.environ.get("REVIEW_PANEL_MODEL"), required=not os.environ.get(
        "REVIEW_PANEL_MODEL"), help="reviewer model (env REVIEW_PANEL_MODEL)")
    r.add_argument("--implementer-model", help="the model that wrote the change; must differ")
    r.add_argument("--issue", help="linked issue number or URL; enables spec")
    r.add_argument("--issue-repo", help="owner/repo when --issue is a bare number of another repo")
    r.add_argument("--topics", nargs="*", default=[],
                   help="extra rule files the assessment found that paths cannot show")
    r.add_argument("--prototype", help="approved prototype HTML; enables ui")
    r.add_argument("--screenshots", help="directory of screenshots of the change, for ui")
    r.add_argument("--out", help="directory for raw outputs and report.md")
    r.add_argument("--allow-domain", nargs="*", default=[],
                   help="extra hosts the attacker and checker may reach (registries are allowed)")
    r.add_argument("--timeout", type=int, default=1800, help="seconds per session")
    r.add_argument("--parallel", type=int, default=4)
    r.add_argument("--force", action="store_true", help="review an unchanged patch-id or round 6+")
    r.add_argument("--dry-run", action="store_true", help="list the sessions without running them")
    o = sub.add_parser("post")
    o.add_argument("--repo", required=True, help="the PR branch's checkout")
    o.add_argument("--ledger", required=True)
    o.add_argument("--pr", required=True, help="pull request number or URL")
    o.add_argument("--pr-repo", help="owner/repo of the PR when --pr is a number gh cannot place")
    o.add_argument("--out", help="the round's --out directory; omit to only reply in threads")
    o.add_argument("--body-only", action="store_true", help="no inline comments: all in the body")
    o.add_argument("--dry-run", action="store_true", help="print the requests, send nothing")
    for name in ("fixed", "decline"):
        d = sub.add_parser(name)
        d.add_argument("--ledger", required=True)
        d.add_argument("titles", nargs="+")
    sub.choices["fixed"].add_argument("--commit", required=True, help="the commit that fixes them")
    sub.choices["decline"].add_argument("--reason", required=True,
                                        help="posted in the finding's thread")
    a = p.parse_args()
    if getattr(a, "repo", None):
        a.repo = os.path.abspath(a.repo)
    sys.exit({"plan": cmd_plan, "run": cmd_run, "post": cmd_post, "fixed": cmd_outcome,
              "decline": cmd_outcome}[a.cmd](a) or 0)


if __name__ == "__main__":
    main()
