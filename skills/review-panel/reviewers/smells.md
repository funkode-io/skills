# Smells

Code that compiles and passes its tests can still be a workaround, and a workaround is the template the next change copies. A smell means something is missing: for each one, name the function, type, resource or boundary whose absence made the workaround necessary.

Read every changed file in full, examples, demos and tests included: they are what later code is modelled on. You need no knowledge of the project's own decisions; another reviewer checks those.

Smells to look for:

- **The catalogue** at <https://refactoring.guru/refactoring/smells>. It is written for classes and methods: read "class" as a type or module and "method" as a function.
  - *Bloaters*, code grown too large to work with:
    - long method: a function long enough to do several things (more than about ten lines is worth a question);
    - large class: a type or module with many fields, functions or lines;
    - primitive obsession: a bare string or number where a small type belongs (money, a range, an id, a code), or constants that encode information;
    - long parameter list: more than three or four parameters;
    - data clumps: the same group of values passed around together in several places, which should be one type.
  - *Object-orientation abusers*, the language's modelling tools applied wrongly or partly:
    - switch statements: a large `match`/`switch` or chain of `if`s on a kind, repeated where the kinds could carry the behaviour;
    - temporary field: a field that holds a value only in some circumstances and is empty the rest of the time;
    - refused bequest: an implementation that uses only part of what it inherits or must implement, leaving the rest unused or failing;
    - alternative classes with different interfaces: two types that do the same job under different function names.
  - *Change preventers*, one change forces many others:
    - divergent change: one type or module edited for many unrelated reasons;
    - shotgun surgery: one change needs many small edits across many types or files;
    - parallel inheritance hierarchies: adding a case in one place always means adding a matching case in another.
  - *Dispensables*, code whose absence would make the rest clearer:
    - comments: a function full of comments that explain what it does;
    - duplicate code: two fragments that are almost the same;
    - lazy class: a type or module that does too little to pay for its upkeep;
    - data class: a type with only fields and accessors, whose behaviour lives in other code that reaches into it;
    - dead code: a variable, parameter, field, function or type nothing uses any more;
    - speculative generality: a type, function, field or parameter added for a future need and used by nothing.
  - *Couplers*, parts that know too much about each other, or only pass work along:
    - feature envy: a function that uses another type's data more than its own;
    - inappropriate intimacy: one type using another's internal fields and functions;
    - message chains: a chain of calls such as `a.b().c().d()`, so the caller depends on the whole path;
    - middle man: a type that only delegates to another;
    - incomplete library class: helper code scattered about to make up for what a library lacks, with no single place that extends it.
- **A comment doing a name's job**: a function, type or test named for less, or for something else, than what it does, with a comment that makes up the difference. A reader must be able to follow the code from its declarations alone. The fix is a better name or an extracted function, never a better comment. Only a reason no name can carry, such as a constraint from outside the code, is left to a comment.
- **One fact in two places** (single source of truth): a value, name, address, key or rule written out by hand in two places that must change together, where one could be derived from the other; the same state kept twice; one part working out what another part already knows instead of being told.
- **One thing serving two uses**: a function or type whose behaviour is chosen by a flag, a type parameter or an optional field that says which use this is. Two things are hiding in one.
- **A rule kept by a comment or a convention** ("do not call this before", "must match", "not for callers to override") where a type, a signature or visibility could make breaking it impossible.
- **A mechanism built by hand** that the language, the standard library, the framework or the protocol already provides.
- **Admitted debt nobody owns**: "for now", "temporary", "TODO", "known gap" beside code that does the wrong thing, with nothing tracked that names the fix.
- **Test smells**: a literal repeated through the tests where a named value or a parameter would say what the test depends on; a helper that hides which data the test relies on; one test that checks several behaviours; branches or loops in a test that repeat the production logic; a test whose name says something other than what it asserts.

Each finding: `file`, `line` (a changed line), `problem` (the smell and what is missing), `evidence` (the changed code). Give a `suggestion` only when the fix is a small replacement; when it is a design decision, end `problem` with the question the owner must answer.

`blocking` for two smells: a comment doing a name's job, and admitted debt nobody owns. Every other smell is a `note`. Not findings: formatting and naming taste, and a smell in code the change did not touch, unless the change copies it (then say what it copied).
