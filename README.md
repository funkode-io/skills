# funkode / skills

Agent skills I wrote, kept in one place so any agent can install them.

| Skill | What it does |
| --- | --- |
| [`address-pr-review`](skills/address-pr-review) | Take a PR from "has open feedback and/or is behind upstream" to "all threads addressed and resolved, branch in sync" — without rewriting history. Interactive: you approve the plan. |
| [`spar-with-copilot`](skills/spar-with-copilot) | Unattended agent-to-agent loop: address Copilot's review comments round after round until it recommends approval, judging every finding against the PR's original intent so the PR doesn't drift. |
| [`review-panel`](skills/review-panel) | Local PR review by a panel of isolated Claude reviewers (correctness, attacker, design, spec, security, data, UI, repo rules) in parallel fresh sessions, then a checker that keeps only proven findings; ends in a Copilot-style verdict, posted as a pull request review with one inline comment per finding and one-click suggestions. |
| [`implement-frontier`](skills/implement-frontier) | Start every issue of a spec that can be implemented now, and decide which blocked issues may start stacked on their blocker's branch. |
| [`delegate-frontier`](skills/delegate-frontier) | Open a draft PR for every unblocked ticket of a spec and hand each to GitHub Copilot. |
| [`stack-on-pr`](skills/stack-on-pr) | Same, but for the tickets a still-open PR unblocks — stacked on that PR's branch. |
| [`publish-release`](skills/publish-release) | Cut a Rust workspace release: bump, tag, `cargo publish` in dependency order, and release notes with sample code for new API and a migration for every breaking change. |
| [`rules-review`](skills/rules-review) | Keep rules and memory lean: ask four questions of every rule (discoverable? already known? shorter? lasting idea or steps?) and propose deletions and rewrites for the owner to approve. |

## Install

```bash
npx skills add funkode-io/skills
```

The [Skills CLI](https://skills.sh) writes them into `~/.agents/skills/` and
records the source in `~/.agents/.skill-lock.json`, so `npx skills update`
picks up later changes. It installs into whichever agents you select — pi,
Codex, Cursor, Copilot, Amp, Zed and others all read the same directory.

Install a single skill instead:

```bash
npx skills add funkode-io/skills/delegate-frontier
```

## My skill set

[`skills.json`](skills.json) lists the skills I keep installed globally, from this
repo and others, grouped by source repo.

```bash
npx -y github:funkode-io/skills install                 # new machine: add every listed skill globally
npx -y github:funkode-io/skills install --agent claude-code pi   # choose agents (default: the CLI's last selection or detected)
npx -y github:funkode-io/skills install --dry-run       # print the `npx skills` commands only
npx -y github:funkode-io/skills install --prune         # also remove global skills not on the list
npx skills update -g                                    # update installed skills to upstream
npx -y github:funkode-io/skills check                   # read-only: what is outdated, missing or unlisted
```

`install` runs `npx skills add <source> -g -y -s <names>` per source, so rerunning
it is safe. `check` compares each global skill's `skillFolderHash` in the lock with
its folder's current tree sha on GitHub; it prints nothing and exits 0 when all is
current, prints one line per finding and exits 1 otherwise, and exits 2 on a
network or API error. It authenticates with `GITHUB_TOKEN`, `GH_TOKEN` or
`gh auth token` when available.

## Per-repo configuration

`publish-release` keeps everything project-specific — the upstream slug, the ordered
publish set, the files carrying the version, the pre-flight gate — out of the skill
and in a `docs/agents/release.md` in the repo being released. The skill derives those
facts and offers to write that file when it is missing. See `funkode-io/replay` for a
worked example.

`review-panel` runs its reviewers on your existing Claude login, stripped of your settings, rules and memory, and keeps each PR's round, patch-id and declined findings in a ledger file the caller passes.

`spar-with-copilot` keeps who requests Copilot reviews — the agent after each push, or GitHub and you — in a `docs/agents/copilot-review.md`. It asks the first time it runs in a repo and writes the answer there.

## Why delegate-frontier and stack-on-pr live together

`stack-on-pr` is `delegate-frontier` with two deltas — the frontier is computed
as if the PR were merged, and branches come off the PR's head instead of the
default branch. Rather than duplicate the PR body shape and the Copilot handoff,
it defers to its sibling:

> follow them live from `../delegate-frontier/SKILL.md`

That relative path only resolves if both skills are installed **as siblings**,
which is why the layout here is flat `skills/<name>/` rather than the nested
`skills/<category>/<name>/` some collections use. Installing one without the
other leaves a dangling reference, so prefer installing the whole repo.

## Migrating off the old copies

`address-pr-review` previously shipped from
[`funkode-io/replay`](https://github.com/funkode-io/replay) at
`.github/skills/address-pr-review/SKILL.md`, which tied a repo-agnostic skill to
one project. The copy here is the newer one: the version installed locally had
gained a **"Triage first, then agree a plan"** step that was never pushed back to
`replay`, so `replay`'s copy is behind.

If you still have it installed from the old source, re-point it:

```bash
npx skills remove address-pr-review
npx skills add funkode-io/skills
```

Otherwise `npx skills update` reconciles against `funkode-io/replay` and can
overwrite the newer text with the older one.

## Layout

```
skills/
  address-pr-review/SKILL.md
  delegate-frontier/SKILL.md
  implement-frontier/SKILL.md
  stack-on-pr/SKILL.md
  spar-with-copilot/SKILL.md
  review-panel/SKILL.md, review-panel.py, reviewers/*.md
skills.json                 my global skill set
bin/funkode-skills.mjs      install / check for skills.json
```

One directory per skill, each with a `SKILL.md` carrying `name` and
`description` frontmatter. The Skills CLI discovers them by scanning for
`SKILL.md`.

## Scope

This repo is for **skills** — instructions any agent can follow. Tool-specific
code lives elsewhere:

| | |
| --- | --- |
| Skills (agent-agnostic) | this repo |
| pi extensions, herdr plugins | [funkode-io/ai](https://github.com/funkode-io/ai) |

The split is by consumer, not by tool. A skill that teaches an agent to drive
herdr belongs here; a plugin that extends herdr belongs in `funkode-io/ai`.
