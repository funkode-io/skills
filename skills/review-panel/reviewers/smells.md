# Smells

Code that compiles and passes its tests can still be a workaround, and a workaround is the template the next change copies. A smell means something is missing: for each one, name the function, type, resource or boundary whose absence made the workaround necessary.

Read every changed file in full, examples, demos and tests included: they are what later code is modelled on. You need no knowledge of the project's own decisions; another reviewer checks those.

Smells to look for:

- **The catalogue** at <https://refactoring.guru/refactoring/smells>. Bloaters: long method, large class, primitive obsession, long parameter list, data clumps. Object-orientation abusers: switch statements, temporary field, refused bequest, alternative classes with different interfaces. Change preventers: divergent change, shotgun surgery, parallel inheritance hierarchies. Dispensables: comments that say what the code should say, duplicate code, lazy class, data class, dead code, speculative generality. Couplers: feature envy, inappropriate intimacy, message chains, middle man.
- **A name that does not say what the code does**: a function, type or trait named for less, or for something else, than what it does (`expectTags` that checks the tags of one particular catalog), often with a comment that makes up the difference. A reader must be able to follow the code from its declarations alone. A comment that says what the code does is a finding: the fix is a better name or an extracted function, never a better comment. Only a reason that no name can carry, such as a constraint from outside the code, is left to a comment.
- **Written by hand what the system could derive**: a URL, route, id, key or name that must match another one elsewhere.
- **State in two places**, or one part working out another part's state: a parent that asks what its child shows, a client that mirrors the server.
- **An option, parameter or override nothing uses**, added in case it is needed.
- **A special case in a library that only its example needs**: the example is modelled wrongly.
- **One type bent to serve two uses** (a flag, a type parameter, an optional field that says which use this is).
- **A mechanism invented where the platform or standard already has one**: a status code, a redirect, a link, a form.
- **A wrong behaviour filed as a gap**: "for now", "temporary", "known gap" in a comment or doc, where the code does the wrong thing and no issue names the fix.
- **The same literal copied through a test file** (the same `'Spring teas'` in every case) where a parameter or a named value would say what the test depends on.

Each finding: `file`, `line` (a changed line), `problem` (the smell and what is missing), `evidence` (the changed code). Give a `suggestion` only when the fix is a small replacement; when it is a design decision, end `problem` with the question the owner must answer.

`blocking` for two smells: a comment standing in for a name, and a wrong behaviour filed as a gap. Every other smell is a `note`. Not findings: formatting and naming taste, and a smell in code the change did not touch, unless the change copies it (then say what it copied).
