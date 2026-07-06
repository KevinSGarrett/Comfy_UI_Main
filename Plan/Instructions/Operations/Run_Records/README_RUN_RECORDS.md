# Operations Run Records

Codex Desktop writes local operation records here after GitHub, AWS, EC2, Civitai, sync, artifact pullback, and model registry actions.

Required behavior:

- One JSON record per meaningful operation.
- No secret values.
- Include command summaries, paths, hashes, evidence, and pass/fail state.
- Link tracker row IDs where possible.
