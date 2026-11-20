# Rules

Read your rule files in full, then the changed files your topic covers. Report each place the change breaks a rule.

Every finding quotes the rule (file and its words) and the changed line that breaks it, in `evidence`. A rule the change keeps is not a finding; a rule outside your topic is someone else's. You never see the PR body or review threads, so rules about them are out of reach: check the code, docs and commit messages.

Severity follows the repository's own review scope when it has one (look for a "review scope" section in `AGENTS.md`, `CLAUDE.md` or `.github/copilot-instructions.md`): its tiers, caps and round rules win. Style that a formatter or linter owns stays with the formatter: leave it out.
