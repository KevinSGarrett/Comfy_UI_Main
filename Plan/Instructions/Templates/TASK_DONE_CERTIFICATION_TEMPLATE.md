# Task Done Certification

Strict autonomous completion uses a machine-readable JSON record created by
`Plan/Instructions/QA/Scripts/New-DoneCertification.ps1`. Markdown output is
legacy presentation-only evidence and cannot authorize a strict pass.

The strict record contains:

- certification, task, tracker, and artifact identities
- title, manifest-verified artifact scope paths, and implementation summary
- tests performed and QA summary
- evidence paths and known issues
- final decision, certifier, and timestamp
- all nine completion gates as explicit booleans
- exact QA record, test run record, and evidence manifest paths

Allowed final decisions are `done`, `done_with_non_blocking_notes`,
`pending_runtime_validation`, `failed`, and `blocked`. Only `done` and
`done_with_non_blocking_notes` can authorize a strict pass, and only after the
bound evaluator independently verifies every required gate and file binding.
