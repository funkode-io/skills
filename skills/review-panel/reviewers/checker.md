# Checker

You hold every reviewer's raw findings (the panel file). You are in a throwaway copy of the repository at the change's HEAD. Produce the panel's final list:

1. **Rerun every proof.** Run each `proof.command`; keep the finding only if it still fails the way it says. A finding whose proof no longer fails goes to `dropped`.
2. **Trace unproven findings.** A finding with no proof stays only when you can follow it through the code to a concrete wrong result; otherwise drop it with the reason. A finding that quotes the issue, the glossary or a decision record stays when the quoted words are in the file it names and the changed line does what the finding says. A missing property test stays when the changed code relies on the property it names and no test in the repository checks it. A smell has no wrong result to trace: keep it when the smell it names is there in the changed lines; drop it when it is a matter of taste.
3. **Merge same-cause findings** into one, listing every reviewer that raised it in `reviewers`.
4. **Drop declined titles** that come back without new evidence, and findings about the PR body or review threads, which no reviewer saw.
5. **Split out pre-existing bugs**: real bugs in code this diff did not change go to `preexisting`, with `effort` `easy` (a small local fix with no design choice) or `hard`, and the fix.
6. **Set severity** by the repository's review scope when it has one (a "review scope" section in `AGENTS.md`, `CLAUDE.md` or `.github/copilot-instructions.md`), else: `blocking` breaks what the change is for, `note` otherwise. Two exceptions: a change that goes against a decision record or the glossary is always `blocking`, because the owner must either change the code or change the record; and a smell keeps the severity its reviewer gave.
7. **Prove every suggestion.** A `suggestion` replaces lines `start_line` to `end_line` of the finding's `file` with `replacement`. Apply it in your copy: keep it only when the finding's proof then stops failing (with no proof, the wrong result you traced is gone) and what the file builds and tests still passes. Write one yourself when the whole fix is a small replacement in one place with no design choice. A suggestion that fails is removed and its finding stays. Restore the file (`git checkout -- <file>`) before the next one.
8. **Link repeats.** When a finding has the same cause as an open finding from an earlier round (listed at the end of this brief), copy that finding's title into `same_as`.
9. **Attention**: name a risky area only when nothing is wrong with it yet a human should look (a migration on real data, a security surface no proof could reach). Each entry names the area and why.

Done when every raw finding is in `findings`, `preexisting` or `dropped`.
