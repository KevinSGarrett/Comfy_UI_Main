# Wave 60 Operations Layer

This directory contains the operational playbooks and starter scripts for GitHub, AWS/EC2, local-to-EC2 sync, EC2-to-local artifact pullback, Civitai API lookup/download, model registry updates, model compatibility, and `.env` secret handling.

## Required read order for Codex Desktop

1. `../AUTONOMOUS_CODEX_DESKTOP_MASTER_MANUAL.md`
2. `../Indexes/MASTER_PROJECT_LOCATION_INDEX.md`
3. `GITHUB_MINIMAL_PERSONAL_PROJECT_PROTOCOL.md`
4. `SECRETS_ENV_HANDLING_PROTOCOL.md`
5. `AWS_EC2_GPU_SERVER_START_STOP_PROTOCOL.md`
6. `LOCAL_TO_EC2_SYNC_PROTOCOL.md`
7. `EC2_TO_LOCAL_ARTIFACT_PULLBACK_PROTOCOL.md`
8. `CIVITAI_API_OPERATING_PROTOCOL.md`
9. `MODEL_METADATA_LOOKUP_PROTOCOL.md`
10. `MODEL_DOWNLOAD_AND_REGISTRY_UPDATE_PROTOCOL.md`
11. `MODEL_STORAGE_AND_COMPATIBILITY_PROTOCOL.md`

## Core rule

Codex must not mark any GitHub, AWS, EC2, Civitai, model download, sync, or registry task complete until the corresponding done gate in the protocol file is satisfied and the tracker is updated.

## Runtime status for this wave

Wave 60 creates protocols and helper files only. It does not start EC2, push to GitHub, download Civitai models, or perform live ComfyUI GPU validation.
