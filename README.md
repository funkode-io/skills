# funkode / skills

Agent skills I wrote, kept in one place so any agent can install them.

| Skill | What it does |
| --- | --- |
| [`delegate-frontier`](skills/delegate-frontier) | Open a draft PR for every unblocked ticket of a spec and hand each to GitHub Copilot. |
| [`stack-on-pr`](skills/stack-on-pr) | Same, but for the tickets a still-open PR unblocks — stacked on that PR's branch. |

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

## Why these two live together

`stack-on-pr` is `delegate-frontier` with two deltas — the frontier is computed
as if the PR were merged, and branches come off the PR's head instead of the
default branch. Rather than duplicate the PR body shape and the Copilot handoff,
it defers to its sibling:

> follow them live from `../delegate-frontier/SKILL.md`

That relative path only resolves if both skills are installed **as siblings**,
which is why the layout here is flat `skills/<name>/` rather than the nested
`skills/<category>/<name>/` some collections use. Installing one without the
other leaves a dangling reference, so prefer installing the whole repo.

## Layout

```
skills/
  delegate-frontier/SKILL.md
  stack-on-pr/SKILL.md
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
