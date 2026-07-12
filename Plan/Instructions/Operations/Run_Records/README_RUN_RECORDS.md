# Operations Run Records

Codex Desktop writes local operation records here after GitHub, AWS, EC2, Civitai, sync, artifact pullback, and model registry actions.

Required behavior:

- One JSON record per meaningful operation.
- No secret values.
- Include command summaries, paths, hashes, evidence, and pass/fail state.
- Link tracker row IDs where possible.

## Required normalized contract

New run records must include enough data to normalize these fields without inference:

- `run_id`
- `timestamp` or explicit start/end timestamps
- `task_id`, `tracker_id`, or `evidence_id`
- `command_id` when an external command service was used
- `command_status` or an explicit final operation status
- `final_state`
- `run_record_file`
- `log_path`, or `log_absent_reason` when no separate log exists
- artifact/evidence pointers and errors

Historical records remain append-only evidence. Auditors may normalize known legacy
schemas, but must not rewrite a failed result or invent missing log metadata.

## Retention policy

- Run-record JSON files and their canonical QA indexes are permanent tracked project evidence; automated cleanup must not delete them.
- A referenced local transient log must be retained for at least 30 days. It may be removed later only when its hash, final status, and durable evidence pointer remain in the run record or canonical index.
- Remote or short-lived logs must be pulled back before expiry when required for QA. When no separate log exists, `log_absent_reason` is mandatory.
- Failed, partial, blocked, and superseded records are retained. A later success links to rather than replaces earlier evidence.
- Retention never authorizes storing credentials, tokens, signed URLs, or secret values.

The Wave64 Row062 auditor treats missing log metadata, missing status/final state,
missing task/evidence linkage, invalid JSON, or an absent index entry as fail-closed.
