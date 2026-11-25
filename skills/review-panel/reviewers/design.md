# Design

Code that compiles and passes its tests can still bend a principle the project stands on. That is debt, and it is also the template the next change copies. Find where this change does it.

1. **Read the principles first**: the ADRs (`docs/adr/`), `GLOSSARY.md` or `CONTEXT.md`, what the README says the project is for and never does, `AGENTS.md` and `CLAUDE.md`, and the standards they name (REST, HTTP semantics, domain-driven design, a design system).
2. **Read every changed file in full**, examples, demos and tests included: they are what later code is modelled on.
3. **Hunt smells.** A smell is a workaround, and a workaround means something is missing. For each one ask: which principle does this bend, and which resource, type or boundary is missing that made the workaround necessary?

Smells to look for:

- **The catalogue** at <https://refactoring.guru/refactoring/smells>. Bloaters: long method, large class, primitive obsession, long parameter list, data clumps. Object-orientation abusers: switch statements, temporary field, refused bequest, alternative classes with different interfaces. Change preventers: divergent change, shotgun surgery, parallel inheritance hierarchies. Dispensables: comments that say what the code should say, duplicate code, lazy class, data class, dead code, speculative generality. Couplers: feature envy, inappropriate intimacy, message chains, middle man.
- **A name that does not say what the code does**: a function, type or trait named for less, or for something else, than what it does (`expectTags` that checks the tags of one particular catalog), often with a comment that makes up the difference. A reader must be able to follow the code from its declarations alone. A comment that says what the code does is a finding: the fix is a better name or an extracted function, never a better comment. Only a reason that no name can carry, such as a constraint from outside the code, is left to a comment.
- **Written by hand what the system could derive**: a URL, route, id, key or name that must match another one elsewhere.
- **State in two places**, or one part working out another part's state: a parent that asks what its child shows, a client that mirrors the server.
- **An option, parameter or override nothing uses**, added in case it is needed.
- **A special case in a library that only its example needs**: the example is modelled wrongly.
- **One type bent to serve two uses** (a flag, a type parameter, an optional field that says which use this is).
- **A mechanism invented where the platform or standard already has one**: a status code, a redirect, a link, a form.
- **"For now", "temporary", "known gap"** in a comment or doc with no issue that names the fix.

Each finding: `file`, `line` (a changed line), `problem` (the smell, the principle it bends, and what is missing), `evidence` (the changed code, and the principle quoted with its file when the repository states one). Give a `suggestion` only when the fix is a small replacement; when it is a design decision, end `problem` with the question the owner must answer.

`blocking` when the change breaks a principle the repository states; `note` for a smell no stated principle covers. Not findings: formatting and naming taste, and a smell in code the change did not touch, unless the change copies it (then say what it copied).
