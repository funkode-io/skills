---
name: stack-on-pr
description: "Stack draft PRs for the tickets a still-open PR unblocks — the frontier computed as if that PR were merged, branched on its head — and hand each to Copilot. Use when the user wants to start tickets blocked by an open PR, delegate the issues a PR will unblock, or open stacked PRs on top of a PR."
---

# Stack the frontier a PR unlocks

Turn the tickets an open PR **unblocks** into draft PRs **stacked** on that PR's branch, then hand each to Copilot — so work a still-open PR blocks can start now, against the contract that PR already defines (its API, its schema, its types).

This is `delegate-frontier` with two deltas: the **frontier** is computed as if the PR were already merged, and each new PR is based on the PR's head branch instead of the default branch. The PR body shape and the Copilot handoff are unchanged — follow them live from `../delegate-frontier/SKILL.md`.

## Steps

### 1. Resolve the tracker, the PR, and its spec

The tracker is the upstream org repo from `git remote -v` (not a personal fork). The PR is the user's argument (number or URL). Read the PR's `Closes #<ticket>` to get the **base ticket(s)** it will close, that ticket's `## Parent` to get the spec, and the PR's head branch — the branch the new PRs stack on.

**Done when:** you have the tracker `owner/repo`, the PR number and its head branch, the base ticket(s) the PR closes, and the spec issue number.

### 2. Compute the frontier the PR unlocks

Over the spec's open tickets, compute the **frontier** exactly as `delegate-frontier` step 2 does — but count the PR's base ticket(s) as already **closed**. The result is the tickets that only this PR still blocks. Drop any ticket that already has an open PR that `Closes` it — whether that PR is stacked on this PR's head branch or targets the default branch — so a re-run never re-opens one.

**Done when:** you have the tickets unblocked solely by this PR and with no existing open PR that `Closes` them, and can name why every excluded ticket was held — another open blocker, or an existing PR.

### 3. Open a draft PR per ticket, stacked on the PR

For each unlocked ticket, first re-check that no open PR already `Closes` it (guarding against a re-run or a PR opened since step 2); if one exists, skip the ticket. Otherwise open a draft PR exactly as `delegate-frontier` step 3 — same repo-convention title, template body, and labels — with one change: branch off the **PR's head branch** and set the new PR's **base** to that head branch. The PR then stacks and shows only its incremental diff on top of the base PR.

**Done when:** every unlocked ticket has exactly one labelled draft PR **based on the PR's head branch**, its title passing the repo's convention, body linking `Closes #<ticket>` with acceptance criteria and every required template section — and no ticket that already had a PR got a second one.

### 4. Hand each PR to Copilot

Exactly as `delegate-frontier` step 4.

**Done when:** every stacked PR carries one `@copilot` comment per `delegate-frontier` step 4.

## Reference

**Frontier-on-merge.** The pick is `delegate-frontier`'s frontier rule with the PR's base ticket(s) forced closed: a downstream ticket qualifies when every `## Blocked by` issue is closed once the PR's ticket is counted as closed. Any ticket with another still-open blocker waits for a later run.

**Stacking base.** The new PR's base is the PR's head branch, not the default branch. When the base PR merges and its branch is deleted, GitHub auto-retargets the stacked PR to the base PR's base (the default branch) and its diff settles to the ticket's own changes; rebase the stacked branch afterward if the retarget leaves conflicts.

**Idempotent re-runs.** The dedup key is an open PR that `Closes #<ticket>`, checked both when computing the frontier (step 2) and again immediately before opening (step 3). Re-running the skill on the same PR therefore only fills gaps — tickets that still have no PR — and never opens a second PR for a ticket already delegated.
