# Wave 32 Planned vs Generated State Model

## Planned state
The planned state comes from the scene director, character ledger, mask ledger, pose plan, video/audio manifests, camera plan, and QA expectations.

## Generated state
The generated state comes from actual outputs and evidence:
- output files
- image/video/audio manifests
- detected character/object state
- QA reports
- region ownership reports
- temporal/audio sync reports

## State diff
The state diff compares each domain and classifies results:
- matched
- partial_match
- mismatch
- missing
- extra
- uncertain
- not_applicable

## Rule
Generated state must not overwrite planned state without a revision record.
