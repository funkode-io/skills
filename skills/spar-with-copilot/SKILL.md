---
name: spar-with-copilot
description: Spar with GitHub Copilot's PR reviewer — an unattended agent-to-agent loop that addresses Copilot's comments round after round until it recommends approval, without drifting from the PR's charter. Use when asked to address Copilot's review comments or get Copilot to approve a PR.
---

# Spar with Copilot

Every push to the PR triggers a fresh Copilot review. A **round** is: wait for Copilot's review of HEAD, judge each finding against the **charter**, push one commit. Copilot is a sparring partner, not the author: it finds _something_ almost every round, and the charter is the fixed yardstick that keeps the PR the author's PR. The user steps in only at Finish.

```bash
N=$(gh pr view --json number -q .number)
R=$(gh pr view --json url -q .url | cut -d/ -f4,5)
BOT=copilot-pull-request-reviewer   # REST login has a "[bot]" suffix, GraphQL login does not
```

## 0. Write the charter (once)

Read the linked issue (`Closes #…`), the PR body and `gh pr diff $N`. Write `$(git rev-parse --git-dir)/copilot-loop-$N.md`:

- **Goal** — one sentence, taken from the issue or PR body.
- **In scope** — the behaviours or claims the PR introduces.
- **Non-goals** — what the issue/PR leaves out, and adjacent code it visibly chose not to touch.
- **Files** — `gh pr diff $N --name-only`, as of now.
- **Ledger** — one line per decided finding: `<thread url> fix|decline|escalate <reason>`.

Show the charter in your reply and carry on. Goal, In scope and Non-goals change only on the user's word.

Done when: the file holds all five sections and Goal cites its source.

## 1. Wait for Copilot's review of HEAD

```bash
SHA=$(gh pr view $N --json headRefOid -q .headRefOid)
for i in $(seq 15); do
  V=$(gh api repos/$R/pulls/$N/reviews --paginate --jq ".[] | select(.user.login==\"$BOT[bot]\" and .commit_id==\"$SHA\") | .body" | grep -m1 -oE '^### (🟢|🟡|🔵).*')
  [ -n "$V" ] && break; sleep 60
done; echo "${V:-none}"
```

Verdicts: `🟢 Approval recommended`, `🟡 Changes recommended`, `🔵 Needs a closer look`. Reviews have landed anywhere from 8 minutes to hours after a push. If none after 15 minutes: `gh pr edit $N --add-reviewer @copilot`, poll another 15, then go to Finish reporting "no Copilot review for `<sha>`".

## 2. Triage every unresolved Copilot thread

```bash
gh api graphql -F owner=${R%/*} -F repo=${R#*/} -F n=$N -f query='query($owner:String!,$repo:String!,$n:Int!){repository(owner:$owner,name:$repo){pullRequest(number:$n){reviewThreads(first:100){nodes{id isResolved isOutdated path line comments(first:1){nodes{databaseId url author{login} body}}}}}}}' \
  --jq ".data.repository.pullRequest.reviewThreads.nodes[] | select((.isResolved|not) and .comments.nodes[0].author.login==\"$BOT\")"
```

Each thread gets exactly one verdict:

- **fix** — a real defect in what this PR adds (a line of its diff, a claim in docs it writes), fixable with Goal and In scope unchanged.
- **decline** — anything outside the charter: pre-existing code, adjacent hardening, alternative designs, style preference, Non-goals, or Copilot being wrong (cite the code line, test output or source that shows it).
- **escalate** — real and in scope, but the fix changes behaviour the PR deliberately chose, rests on a fact you can't verify from the repo or a primary source, or would need a file outside **Files**.

A finding the ledger already decided keeps its verdict; reply with a link to the earlier thread. If Copilot brings new evidence against a ledger entry, escalate it. An `isOutdated` thread whose problem is gone from the current code is a fix with nothing to change.

Done when: every unresolved Copilot thread has a ledger line.

## 3. Apply the round

1. Make each fix the smallest change that removes the defect. Tests for changed lines may land in new files; any other new file turns the finding into an escalate.
2. Run the repo's tests and linters for the touched code.
3. One commit `fix(<scope>): address Copilot review round <k>`, push.
4. Reply to each fix and decline thread, then resolve it. Escalate threads stay open, without a reply.

```bash
gh api repos/$R/pulls/$N/comments/<databaseId>/replies -f body="Fixed in <sha>: …"   # or "Declined: <reason>"
gh api graphql -f query='mutation{resolveReviewThread(input:{threadId:"<id>"}){thread{isResolved}}}'
```

## 4. Loop or stop

Go back to step 1 for the new HEAD, unless one of these holds — then Finish:

- **converged** — Copilot's review of HEAD is 🟢 and triage produced no fixes, or any round produced zero fixes (no push, so no new review).
- **escalations pending** — this round's fixes are pushed; the escalations go to the user. Resume at step 2 once they answer.
- **round 5 done** — Copilot is not converging; the user decides whether to continue.

## Finish

Reply with:

- the PR URL, the last verdict and the number of rounds;
- each escalation: its thread URL and the question the user must answer;
- declined findings worth a follow-up: thread URL and one line each. Open issues only if the user asks.
