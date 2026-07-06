# SDXL / RealVisXL Base Lane

This directory contains the authored local-static workflow contract for the `sdxl_realvisxl_base_lane` base generation workflow template.

## Current files

- `workflow.api.json`
- `patch_points.json`
- `runtime_requirements.json`
- `smoke_test_request.json`

## Runtime proof still required

- `object_info_proof.json`
- checkpoint path and sha256 proof for `realvisxlV50_v50Bakedvae.safetensors`
- first generated output evidence
- pullback manifest and image QA evidence

## Design boundary

This lane uses a simple SDXL `CheckpointLoaderSimple -> CLIPTextEncode -> EmptyLatentImage -> KSampler -> VAEDecode -> SaveImage` graph. No LoRA stack is enabled until a compatible SDXL/RealVisXL stack is selected from the registry and proven through runtime QA.

## Promotion rule

This template is not promoted until object_info, model-loading, output, and QA evidence pass.
