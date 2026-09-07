---
name: delegate-frontier
description: "Open a draft PR for every unblocked (frontier) ticket of a spec and hand each to GitHub Copilot to implement. Use when the user wants to delegate ready tickets to Copilot, open PRs for unblocked tickets, or have Copilot start implementing a spec's tickets."
---

# Delegate the frontier to Copilot

Turn the **frontier** — the tickets whose blockers are all closed — into draft PRs with correct titles and bodies, then hand each to GitHub Copilot. Copilot writes wrong PR titles and bodies when it opens the PR itself; here **you own the PR** and Copilot only writes the code.

Frontier tickets are mutually unblocked, so they are parallelisable: open one PR per frontier ticket in the same run.

## Steps

### 1. Resolve the tracker and the spec

The tracker is the remote that hosts the issues and PRs — read it from `git remote -v` (the upstream org repo, not a personal fork). The spec is the parent issue whose tickets you are delegating; take it from the user's argument, or ask for the issue number.

**Done when:** you have the tracker `owner/repo` and the spec issue number.

### 2. Compute the frontier

List the spec's open tickets — the `ready-for-agent` issues whose body `## Parent` references the spec. For each, read its `## Blocked by` section: a ticket is on the **frontier** when every issue it names there is **closed** (a ticket that names none is on the frontier). Drop any ticket that already has an open PR that `Closes` it — it is already delegated.

**Done when:** you have the list of frontier tickets, each with every blocker closed and no open PR, and you can name why every non-frontier ticket was excluded.

### 3. Open a draft PR per frontier ticket

First learn the tracker's PR conventions so the PRs pass its checks, not just read as the ticket: read any PR-title rule (Conventional Commits type prefix, allowed scopes) and `.github/PULL_REQUEST_TEMPLATE.md` if present — commonly documented in `.github/instructions/git-workflow.instructions.md` or `CONTRIBUTING.md`. A raw ticket title and a bare `Closes` body will fail a repo's title/body CI checks.

For each frontier ticket, off the tracker's default branch:

- Create a branch named for the ticket (`<type>/<number>-<slug>` when the repo uses typed branches, else `<number>-<slug>`).
- Make an empty scaffold commit so a PR can open.
- Push the branch to the tracker remote and open a **draft PR** whose **title** follows the repo's title convention (e.g. `<type>: <ticket purpose>` — infer the Conventional Commits type from the ticket, no ticket-less parenthesised scope) and whose **body** is the repo's PR template populated from the ticket: `Closes #<ticket>` in the Metadata section, a Summary of its purpose, and its acceptance criteria — filling every section the template marks required for that title type, so the PR reads as the ticket **and** passes the repo's title/body checks. If the repo has no template, fall back to purpose + `Closes #<ticket>` + acceptance criteria.
- Set the PR's labels (mirror the ticket's `layer:*`/domain labels, drop issue-only ones like `ready-for-agent`, and add the classification/severity the repo requires) — the path-based labeler will not fire on a scaffold branch with no file diff.

**Done when:** every frontier ticket has exactly one labelled draft PR whose title passes the repo's title convention and whose body links `Closes #<ticket>`, carries its acceptance criteria, and fills every template section the repo requires for that title type.

### 4. Hand each PR to Copilot

On each PR from step 3, post one comment: `@copilot ` followed by the **body of the `implement` skill** (`.agents/skills/implement/SKILL.md`, everything below the frontmatter), read live so an edit to that skill flows straight into the handoff.

The Copilot coding agent has cloned the tracker repo, so it can open any skill markdown committed there. Make the nested skills followable: in the pasted body, **replace** every `/<skill>` reference with the repo-relative path to its committed markdown — `/code-review` becomes `.agents/skills/code-review/SKILL.md`. Replace rather than annotate, because `/<skill>` is a pi slash-command the Copilot agent cannot run; leaving it in the text is noise. Pointing at the file rather than restating its content keeps the instruction valid across edits. Replace only references whose `.agents/skills/<skill>/SKILL.md` is committed to the tracker; a reference with no committed markdown cannot be followed, so leave it as-is and tell the user which skill is missing.

**Done when:** every frontier PR carries exactly one `@copilot` comment in which every `/<skill>` reference that resolves to a committed markdown has been replaced by that markdown's repo-relative path, and no runnable `/<skill>` slash token remains.

## Reference

**Frontier rule.** Blocked by means another issue must close first. Resolve each `## Blocked by` reference to its issue state; all closed ⇒ frontier, any open ⇒ hold the ticket for a later run.

**PR body shape.** The repo's PR template (`.github/PULL_REQUEST_TEMPLATE.md`) populated from the ticket: `Closes #<ticket>` in Metadata, a Summary of the ticket's purpose, its acceptance-criteria checklist copied verbatim, and every other section the template marks required for the title's Conventional Commits type. No template ⇒ `Closes #<ticket>` + one purpose line + the acceptance-criteria checklist. Keep it aligned to the ticket so the PR is reviewable against it.

**Handoff message.** `@copilot <implement-skill body>`, with each committed `/<skill>` reference **replaced** by its path `.agents/skills/<skill>/SKILL.md` so the Copilot agent opens the live markdown from its clone instead of hitting an unrunnable slash-command. The mention triggers Copilot on the PR's branch; the PR's `Closes #<ticket>` gives it the ticket as context.
