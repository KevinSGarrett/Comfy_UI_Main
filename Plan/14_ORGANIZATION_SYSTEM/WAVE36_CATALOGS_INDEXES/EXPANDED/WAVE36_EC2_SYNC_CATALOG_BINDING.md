# Wave 36 EC2 Sync Catalog Binding

EC2 sync should use catalogs to decide what to upload.

## Required sync catalog fields

- sync_job_id
- required_workflows
- required_models
- required_loras
- required_reference_assets
- required_scripts
- expected_outputs
- pullback_artifacts
- proof_required
- stop_conditions

## Rule

Never sync the entire local system by default. Sync only cataloged required artifacts.
