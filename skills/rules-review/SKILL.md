---
name: rules-review
description: Review stored rules and memory (CLAUDE.md, AGENTS.md, preference, playbook and memory files) and propose deletions and rewrites. Use when the owner asks to review, prune or clean up rules or memory, or periodically to keep them lean.
---

# Rules review

Rules hold only the owner's decisions, directions and intents. Ask four questions of every rule, one rule at a time:

1. **Can I get this from code, the internet or an API?** Yes: propose deleting it.
2. **Do I already know this** (general knowledge such as clean architecture or REST principles, or what loaded instruction files already say)? Yes: propose deleting it. Keep the owner's stance on it ("strong advocate of REST, hence HTMX"), not the knowledge.
3. **Can it say the same in fewer words?** Yes: propose the shorter text.
4. **Is it a lasting idea, or a specific case or step-by-step guide?** If it's a case or steps, propose rewriting it as the idea behind it.

Never delete an owner safety decision; you may only shorten it.

## Output

Propose only. Change nothing until the owner approves. For each file, give a table: rule (first few words) | Q1-Q4 answers | proposal (keep, delete, or the new text). Then list what to delete and what to rewrite, and wait.
