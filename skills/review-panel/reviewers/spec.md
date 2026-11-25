# Spec

The spec is what was asked and what was decided. The linked issue asks for this change; the glossary and the decision records (ADRs) hold for every change. Read in full the ones this brief names, then compare the change with them, line by line:

- **missing**: the issue asks for it and the diff does not do it;
- **extra**: the diff does something the issue did not ask for (scope creep);
- **wrong**: the diff does it differently from what the issue says, goes against a decision record, or uses a term against its glossary meaning (a second name for a thing the glossary names, or a glossary name for a different thing);
- **conflict**: the issue asks for what a decision record rules out. Do not pick a side: end `problem` with the question the owner must answer.

Quote the spec line with its file in `evidence` and point `file`/`line` at the code (or the nearest changed line for a missing item). Missing and wrong items are `blocking` when the issue states them as required or a decision record or the glossary says otherwise; a conflict is `blocking`; extra items are `note` unless they change behaviour a user sees. Something the spec leaves open is not a finding.

The README and other user documentation describe the code; they are not a spec. Do not review the code against them.
