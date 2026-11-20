---
name: implement-frontier
description: Start every issue of a spec or PRD that can be implemented now, and decide which blocked issues may start stacked on their blocker's branch. Use when a spec is ready to implement, when a blocker's PR opens or merges, or when asked to implement a frontier.
---

# Implement frontier

1. List the spec's open issues and their blockers. Skip any issue that already has an open PR or a worker.
2. The frontier is every issue with no open blocker. Start them all at once, oldest spec first. Never ask whether to go one at a time.
3. For each issue whose blockers are all open PRs, judge whether the blocker branch is mature enough to build on: CI green, review approved or close, no open design question, and little chance its interface changes.
4. High confidence: start the issue stacked on the blocker's branch, then tell the owner what started and why. Low confidence: ask the owner one question, with the evidence and a recommendation.
5. When a blocker merges, rebase the work stacked on it onto main and compute the frontier again.
