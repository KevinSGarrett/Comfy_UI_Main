# Wave 06 Implementation Manual

## Implementation sequence
1. Add engine registry schema.
2. Add engine registry entries.
3. Add checkpoint recommendation matrix.
4. Add router rules.
5. Add pass-to-engine map.
6. Add compatibility validator.
7. Add route decision CLI.
8. Add current main flow engine inventory.
9. Update `.env.example` with Flux2 and engine-router variables.
10. Validate locally.
11. Do not run EC2 until route proof tasks are explicit.

## Required repository additions
```text
Implementation/
  engine_router/
    engine_registry.json
    engine_router_rules.json
    pass_to_engine_map.json
    checkpoint_recommendation_matrix.json
  scripts/
    route_engine_candidate.py
    validate_wave06_engine_registry.py
    validate_model_engine_compatibility.py
    inspect_workflow_engines.py
  schemas/
    engine_registry.schema.json
    engine_route_request.schema.json
    engine_route_decision.schema.json
```

## Required `.env` additions
```text
# Engine Router
ENGINE_ROUTER_ENABLED=true
ENGINE_REGISTRY_PATH=Implementation/engine_router/engine_registry.json
ENGINE_ROUTER_RULES_PATH=Implementation/engine_router/engine_router_rules.json
PASS_TO_ENGINE_MAP_PATH=Implementation/engine_router/pass_to_engine_map.json

# Flux2
FLUX2_ENABLED=false
FLUX2_LOCAL_ROOT=C:\Comfy_UI_Main\models\flux2
FLUX2_S3_PREFIX=s3://YOUR_MODEL_BUCKET/models/flux2/
FLUX2_EC2_ROOT=/opt/ComfyUI/models/flux2
FLUX2_DEV_MODEL_FILENAME=
FLUX2_KLEIN_MODEL_FILENAME=
FLUX2_TEXT_ENCODER_FILENAME=
FLUX2_VAE_FILENAME=
FLUX2_MIN_COMFYUI_VERSION=
FLUX2_PROMOTION_STATUS=blocked_until_runtime_proof

# Optional API routes
BFL_API_ENABLED=false
BFL_API_KEY=
BFL_API_MAX_COST_PER_RUN_USD=
QWEN_IMAGE_ENABLED=false
SD35_ENABLED=false
```

## Router function
The router must receive a structured request and return a structured decision. It must not make free-form guesses.

Input:
```json
{
  "pass_type": "skin_fabric_microdetail",
  "output_type": "image",
  "requested_engine": null,
  "requires_lora_family": "sdxl",
  "cost_tier": "local_first",
  "promotion_required": true
}
```

Output:
```json
{
  "selected_engine": "sdxl_realvisxl",
  "selected_family": "sdxl",
  "reason": "Pass requires SDXL LoRA family and local detail/inpaint support.",
  "blocked": [],
  "required_proof": ["model_load", "output_file", "qa_manifest"]
}
```

## Failure behavior
The router must return a blocked decision, not silently substitute another family.

Example:
```json
{
  "selected_engine": null,
  "blocked": ["sdxl_lora_requested_but_only_flux_engine_available"],
  "action": "hydrate_or_install_sdxl_assets_or_change_pass_plan"
}
```
