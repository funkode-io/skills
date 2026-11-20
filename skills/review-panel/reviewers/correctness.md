# Correctness

Run the review command you were given over the diff range and report what it finds: bugs, wrong logic, unhandled edge cases, broken callers. Read every changed file and what it calls.

Then name **the one fact the change is safe because of** (an invariant, a caller contract, a test that pins it) and check that fact holds in the code. Put it in `safety_fact` with the file:line that proves it. If no such fact holds, that is a blocking finding.

Each finding: `file`, `line` (a changed line where possible), `problem`, `evidence` (the code that shows it). `blocking` when it breaks behaviour the change claims; `note` otherwise. Set `preexisting` when the bug sits in code the diff did not change.
