# Correctness

Find the bugs this change introduces. Read every changed file in full and what the changed code calls and is called by. For each changed function ask: which input, state or caller breaks it? Look for wrong logic, unhandled edge cases (empty, none, zero, duplicate, out of order), broken callers, error paths that swallow or mislabel a failure, and tests that pass without pinning the behaviour. Then read what the README and other user documentation say about the changed behaviour: a sentence or example the change makes false is a finding.

Then name **the one fact the change is safe because of** (an invariant, a caller contract, a test that pins it) and check that fact holds in the code. Put it in `safety_fact` with the file:line that proves it. If no such fact holds, that is a blocking finding.

Each finding: `file`, `line` (a changed line where possible), `problem`, `evidence` (the code that shows it and the input that breaks it). `blocking` when it breaks behaviour the change claims; `note` otherwise. Set `preexisting` when the bug sits in code the diff did not change.
