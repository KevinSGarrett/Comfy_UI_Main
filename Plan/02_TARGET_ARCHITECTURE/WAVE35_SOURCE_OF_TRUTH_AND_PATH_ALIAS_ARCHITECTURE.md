# Wave 35 Source-of-Truth and Path Alias Architecture

The system uses path aliases to prevent local directory chaos.

## Required aliases
- SYSTEM_ROOT
- REPO_ROOT
- COMFYUI_ROOT
- MODELS_ROOT
- LORAS_ROOT
- WORKFLOWS_ROOT
- REFERENCE_ASSETS_ROOT
- OUTPUTS_ROOT
- QA_EVIDENCE_ROOT
- MANIFESTS_ROOT
- EC2_SYNC_ROOT
- APP_MODE_ROOT
- RELEASES_ROOT

## Source-of-truth rule
A file can have runtime copies, but only one canonical owner.
