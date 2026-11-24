---
name: review-panel
description: Review a PR branch with a panel of isolated Claude reviewers (correctness, attacker, spec, security, data, UI, repo rules) run in parallel in fresh sessions, then a checker, ending in a Copilot-style verdict. Use when asked to review a PR or branch locally, replace a Copilot review, or get a PR to approval.
---

# Review panel

A **panel** is a set of reviewers, each a fresh `claude -p` session that sees only the diff, the repository at HEAD and the linked issue, never the PR body or your summary. [`review-panel.py`](review-panel.py) runs them in parallel, then a **checker** that keeps only proven findings, prints the verdict line first, and posts the round as a pull request review:

- `🟢 Approval recommended`: no findings.
- `🟡 Changes recommended`: notes only, non-blocking.
- `🔴 Changes required`: at least one blocking finding.
- `🔵 Needs a closer look`: no findings, but a named risky area needs the owner. It goes to the owner and never triggers another round.

```bash
PANEL=<this skill's directory>/review-panel.py
LEDGER=$(git rev-parse --git-dir)/review-panel-<PR number>.json
```

## Setup (once per machine)

Reviewers run on the Claude login of whoever runs the panel (`claude` must be logged in with `/login`; an API key or token in the environment is not passed on), with none of that user's settings, rules, memory, skills or MCP servers. The attacker and checker run commands in Claude Code's sandbox, which on Linux needs `bubblewrap` and `socat`; without them those two sessions refuse to start.

## 1. Plan

`python3 $PANEL plan --repo . --ledger $LEDGER` prints the round, the files in scope, path hints and the Rules topics matched from `applyTo` globs.

- `skip: true`: the PR's own change (its patch-id) is unchanged since the last round, for example after a main merge that touched none of its lines. Report `last_verdict` and stop.
- `round` above 5: stop and ask the user whether to continue.

## 2. Choose the reviewers

Read the diff. Correctness and Attacker always run. Add:

- `spec` when the PR links an issue (pass `--issue`);
- `security` when it touches auth, input parsing, secrets, bot or web surfaces;
- `data` when it touches migrations, the event store or money maths;
- `ui` when it changes what a user sees and an approved prototype exists (`--prototype`, `--screenshots`);
- `rules` when `rule_topics` is non-empty. Pass `--topics <rule file>` only for a rule area the paths cannot show.

`path_hints` are hints; the diff decides. When you cannot tell whether a reviewer applies, ask the user, naming the reviewer and what made it unclear.

Done when every reviewer is in or out with a one-line reason.

## 3. Run

```bash
python3 $PANEL run --repo . --ledger $LEDGER --model <reviewer model> --implementer-model <yours> \
  --reviewers correctness,attacker,spec,rules --issue <N> --out <scratch dir>
```

The reviewer model differs from the one that wrote the change. The script picks the depth: rounds 1-2 review the whole diff at high effort; round 3 on reviews only files whose own change moved, blocking findings only. After a main merge, only files whose own change moved are reviewed, in any round. Exit 2 means a session failed: rerun, the ledger is untouched.

## 4. Post

```bash
python3 $PANEL post --repo . --ledger $LEDGER --pr <PR number or URL> --out <scratch dir>
```

One pull request review per round: the verdict is its body, each finding is an inline comment on its line, with a one-click suggestion when the checker proved the replacement. Findings on lines outside the diff stay in the body. A finding that repeats an open one continues in that finding's thread. Exit 2 means GitHub refused an anchor and nothing was posted: rerun with `--body-only`.

## 5. Act on the verdict

- 🟢: done.
- 🟡 / 🔴: settle every finding, then commit, push, run `post` again without `--out` (it answers each settled thread, fixed or declined, and resolves it) and go back to step 1.
  - Fixed, by your own commit: `python3 $PANEL fixed --ledger $LEDGER --commit <sha> "<title>"`.
  - Declined: `python3 $PANEL decline --ledger $LEDGER --reason "<why, and where it was decided>" "<title>"`; reviewers re-raise a declined title only with new evidence. Reviewers never see the PR body, so a decision made after the issue was written reads as a spec deviation: decline it, citing where the decision is recorded.
- 🔵: report the named areas to the owner and stop.
- **Pre-existing bugs**: `easy` ones you fix in this PR with a note in the PR body; for `hard` ones propose a follow-up issue.
