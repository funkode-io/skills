# Smells

Code that compiles and passes its tests can still be a workaround, and a workaround is the template the next change copies. A smell means something is missing: for each one, name the function, type, resource or boundary whose absence made the workaround necessary.

Read every changed file in full, examples, demos and tests included: they are what later code is modelled on. You need no knowledge of the project's own decisions; another reviewer checks those.

Smells to look for:

- **The catalogue** at <https://refactoring.guru/refactoring/smells>. Bloaters: long method, large class, primitive obsession, long parameter list, data clumps. Object-orientation abusers: switch statements, temporary field, refused bequest, alternative classes with different interfaces. Change preventers: divergent change, shotgun surgery, parallel inheritance hierarchies. Dispensables: comments that say what the code should say, duplicate code, lazy class, data class, dead code, speculative generality. Couplers: feature envy, inappropriate intimacy, incomplete library class, message chains, middle man.
- **A comment doing a name's job**: a function, type or test named for less, or for something else, than what it does, with a comment that makes up the difference. A reader must be able to follow the code from its declarations alone. The fix is a better name or an extracted function, never a better comment. Only a reason no name can carry, such as a constraint from outside the code, is left to a comment.
- **One fact in two places** (single source of truth): a value, name, address, key or rule written out by hand in two places that must change together, where one could be derived from the other; the same state kept twice; one part working out what another part already knows instead of being told.
- **One thing serving two uses**: a function or type whose behaviour is chosen by a flag, a type parameter or an optional field that says which use this is. Two things are hiding in one.
- **A rule kept by a comment or a convention** ("do not call this before", "must match", "not for callers to override") where a type, a signature or visibility could make breaking it impossible.
- **A mechanism built by hand** that the language, the standard library, the framework or the protocol already provides.
- **Admitted debt nobody owns**: "for now", "temporary", "TODO", "known gap" beside code that does the wrong thing, with nothing tracked that names the fix.
- **Test smells**: a literal repeated through the tests where a named value or a parameter would say what the test depends on; a helper that hides which data the test relies on; one test that checks several behaviours; branches or loops in a test that repeat the production logic; a test whose name says something other than what it asserts.

Each finding: `file`, `line` (a changed line), `problem` (the smell and what is missing), `evidence` (the changed code). Give a `suggestion` only when the fix is a small replacement; when it is a design decision, end `problem` with the question the owner must answer.

`blocking` for two smells: a comment doing a name's job, and admitted debt nobody owns. Every other smell is a `note`. Not findings: formatting and naming taste, and a smell in code the change did not touch, unless the change copies it (then say what it copied).
