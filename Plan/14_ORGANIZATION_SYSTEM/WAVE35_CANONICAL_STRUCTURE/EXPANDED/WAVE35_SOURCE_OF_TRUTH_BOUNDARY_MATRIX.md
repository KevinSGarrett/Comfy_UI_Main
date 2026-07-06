# Wave 35 Source-of-Truth Boundary Matrix

| Artifact | Source of truth | Runtime copy allowed | Generated copy allowed | Catalog required |
|---|---|---:|---:|---:|
| Architecture docs | Repo/docs or project pack docs | No | No | Yes |
| Schemas | Repo/schemas | Yes, as copied validation dependency | No | Yes |
| Registries | Repo/registries | Yes | No | Yes |
| ComfyUI canonical workflows | Repo/workflows + local 05_WORKFLOWS | Yes | No | Yes |
| Active ComfyUI runtime workflows | ComfyUI/user/workflows | Yes | No | Yes |
| Models/checkpoints | Local 03_MODELS / ComfyUI/models | Yes | No | Yes |
| LoRAs | Local 04_LORAS / ComfyUI/models/loras | Yes | No | Yes |
| Reference assets | Local 06_REFERENCE_ASSETS / ComfyUI/input | Yes | No | Yes |
| Generated outputs | Local 07_GENERATED_OUTPUTS / ComfyUI/output | Yes | Yes | Yes |
| QA evidence | Local 08_QA_EVIDENCE / release pack | Yes | Yes | Yes |
| EC2 sync payloads | Local 12_EC2_SYNC_STAGING | Yes | Yes | Yes |
| Releases | Local 14_RELEASES / release ZIP | No | Yes | Yes |
