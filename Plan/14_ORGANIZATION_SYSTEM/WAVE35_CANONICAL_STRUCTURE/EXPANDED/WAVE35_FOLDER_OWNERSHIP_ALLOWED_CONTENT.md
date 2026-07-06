# Wave 35 Folder Ownership and Allowed Content

Every folder has an owner domain.

| Folder | Owner domain | Allowed content |
|---|---|---|
| 00_ADMIN | project_control | decisions, owners, migration logs |
| 01_REPO | source_control | repo checkout |
| 02_COMFYUI_RUNTIME | runtime_execution | ComfyUI install/runtime |
| 03_MODELS | heavy_assets | checkpoints, UNet, CLIP, VAE, video models |
| 04_LORAS | heavy_assets | LoRA files by engine/category |
| 05_WORKFLOWS | workflow_library | workflow JSONs and workflow docs |
| 06_REFERENCE_ASSETS | reference_assets | references, masks, control maps |
| 07_GENERATED_OUTPUTS | generated_outputs | outputs by type/status |
| 08_QA_EVIDENCE | qa_evidence | proof reports and QA outputs |
| 09_MANIFESTS | manifests | catalogs and runtime manifests |
| 10_LOGS | logs | local, validation, EC2 logs |
| 11_BACKUPS | backups | snapshots and rollback copies |
| 12_EC2_SYNC_STAGING | ec2_sync | minimal upload/pullback staging |
| 13_APP_MODE | app_mode | app controls, presets, exports |
| 14_RELEASES | releases | certified ZIPs and handoff packets |
