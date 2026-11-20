# Spec

The linked issue is the spec. Compare the change with it, line by line:

- **missing**: the issue asks for it and the diff does not do it;
- **extra**: the diff does something the issue did not ask for (scope creep);
- **wrong**: the diff does it, differently from what the issue says.

Quote the spec line in `evidence` and point `file`/`line` at the code (or the nearest changed line for a missing item). Missing and wrong items are `blocking` when the issue states them as required; extra items are `note` unless they change behaviour a user sees. Something the issue leaves open is not a finding.
