# Model Registry Index

Updated: 2026-07-06T14:58:05-05:00

Primary registry:

`Plan/Registries/Models/model_registry.jsonl`

Runtime validation queue:

`Plan/Registries/Models/model_runtime_validation_queue.csv`

## Active Base-Generation Checkpoints

| Lane | Model | File | Status | Runtime Queue |
|---|---|---|---|---|
| `sdxl_low_risk_fallback_lane` | Stable Diffusion XL Base 1.0 | `sd_xl_base_1.0.safetensors` | `runtime_validated` / `pass_with_notes_for_runtime_smoke` | `MRQ-20260706-001` = `runtime_smoke_complete` |
| `sdxl_realvisxl_base_lane` | RealVisXL V5.0 / V5.0 (BakedVAE) | `realvisxlV50_v50Bakedvae.safetensors` | `runtime_validated` / `pass_with_notes_for_runtime_smoke` | `MRQ-20260706-002` = `runtime_smoke_complete` |

## Boundaries

- Model binaries are not committed to the repo.
- Local registry coverage is not a new runtime run; completed statuses above point to existing EC2 path/hash proof, ComfyUI object-info proof, generation output, pullback, and image QA evidence.
- Single-image runtime smoke is not final portfolio certification.
- S3 runtime transfer remains blocked until bucket prefix and role values are configured.
- RealVisXL metadata was fetched through the Civitai API helper and cached at `Plan/Registries/Models/metadata/civitai/realvisxl_query_20260706T093109-0500.json`.
