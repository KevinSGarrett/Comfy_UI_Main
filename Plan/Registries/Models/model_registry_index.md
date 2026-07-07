# Model Registry Index

Updated: 2026-07-06T20:45:00-05:00

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
- RealVisXL is now present both on EC2 and locally: the local ignored file `models/checkpoints/realvisxlV50_v50Bakedvae.safetensors` was downloaded from Civitai version `789646` and SHA256-verified in `Plan/Instructions/QA/Evidence/Model_Registry/W66_LOCAL_REALVISXL_MODEL_DOWNLOAD_20260706T204500-0500.json`.
- Local ComfyUI is CUDA-ready for low-cost development iteration: `Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_LOCAL_COMFYUI_DEV_PREFLIGHT_FULL_READY_20260706T204500-0500.json` reports CUDA Torch, required model presence, and selected-lane static validation; `Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_LOCAL_COMFYUI_OBJECT_INFO_SMOKE_20260706T204800-0500.json` reports required local ComfyUI nodes present.
- Local ComfyUI generation is now proven for RealVisXL iteration: `Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_LOCAL_COMFYUI_REALVISXL_SMOKE_EXECUTE_20260706T205501-0500.json` reports one bounded local PNG generated and stopped cleanly; visual QA `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_LOCAL_REALVISXL_SMOKE_IMAGE_QA_VISUAL_20260706T205650-0500.json` passed with local-smoke notes.
- Single-image runtime smoke is no longer the broadest RealVisXL proof; the bounded three-sample matrix certification is recorded in `Plan/Instructions/QA/Evidence/Image_Artifact_QA/W66_REALVISXL_MATRIX_FINAL_QA_CERTIFICATION_20260706T201000-0500.json`.
- S3 runtime transfer infrastructure is configured and the matrix deploy/pullback path has been exercised; keep using fresh clean-head bundles and emergency stops for future EC2 target proof.
- RealVisXL metadata was fetched through the Civitai API helper and cached at `Plan/Registries/Models/metadata/civitai/realvisxl_query_20260706T093109-0500.json`.
