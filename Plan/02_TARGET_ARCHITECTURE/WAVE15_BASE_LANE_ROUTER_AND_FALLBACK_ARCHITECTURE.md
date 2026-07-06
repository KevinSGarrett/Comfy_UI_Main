# Wave 15 — Base Lane Router and Fallback Architecture

The base lane router decides which image engine should produce the first image and which lane should run next if the first lane fails.

## Router inputs

- Scene Director structured plan
- Character Bible/identity reference requirements
- Environment/room/material requirements
- Camera/framing plan
- Pose/control-map plan
- Mask Factory requirements
- Engine registry and model family compatibility matrix
- Available workflow templates
- Local/EC2 object_info results
- Runtime budget and fallback policy

## Router outputs

- `selected_lane_id`
- `fallback_lane_ids`
- `blocked_reasons`
- `workflow_template_id`
- `patch_target_set`
- `required_models`
- `required_loras`
- `qa_gates`
- `promotion_allowed: false` until evidence exists

## Fallback order

Default fallback sequence:

```text
Flux2 Dev → Flux1 Dev → SDXL/RealVisXL → Z-Image → Flux Schnell smoke → SDXL low-risk fallback → Pony specialty → SD1.5 legacy
```

This is not a blind sequence. The router skips lanes whose required assets, model family, prompt style, or workflow template do not match the scene.

## Hard stops

The router must stop rather than guess when:

- A LoRA/checkpoint family mismatch would occur.
- Required identity/reference assets are missing.
- Required masks/control maps are missing.
- All configured base lanes fail.
- Max retries have already been used.
