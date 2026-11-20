# Security

Review only what the change touches among: authentication and sessions, authorisation checks, input parsing and deserialisation, secrets and tokens, bot commands and web routes (anything a stranger can reach).

For each finding name the attacker, what they send, and what they gain; quote the line that lets it through in `evidence`. A defence that exists elsewhere in the call path cancels the finding: trace the path before raising it. `blocking` when a stranger gains data, access or control; `note` for defence-in-depth gaps.
