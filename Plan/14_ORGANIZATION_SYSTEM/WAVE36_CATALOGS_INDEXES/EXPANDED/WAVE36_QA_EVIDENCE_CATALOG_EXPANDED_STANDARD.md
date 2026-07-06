# Wave 36 QA Evidence Catalog Expanded Standard

The QA evidence catalog is the audit layer.

## Required fields

- evidence_id
- run_id
- wave
- workflow_id
- artifact_id
- output_path
- evidence_type
- QA gate
- pass_fail_status
- score
- proof_file
- manifest_id
- promotion_decision
- rerun_link
- timestamp

## Evidence types

```text
image_decode
manifest_presence
preview_QA
state_diff_QA
runtime_output_proof
video_temporal_QA
audio_sync_QA
app_mode_QA
ec2_proof
release_certification
```

## Rule

Promotion decisions must point to QA evidence records.
