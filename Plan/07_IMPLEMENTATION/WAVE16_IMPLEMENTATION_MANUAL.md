# Wave 16 — Implementation Manual

## Objective

Implement the image refine and engine bridge layer after Wave 15 base generation.

## Implementation steps

1. Generate or select an approved base image.
2. Record base image hash and QA status.
3. Choose refine sequence from `wave16_base_to_refine_sequence_map.json`.
4. Select bridge contract from `wave16_refine_engine_bridge_matrix.json`.
5. Validate denoise against `wave16_low_denoise_policy.json`.
6. Patch workflow JSON/API template.
7. Run dry-run validation.
8. Execute in ComfyUI only after validation.
9. Collect history/output evidence.
10. Score base preservation and drift.
11. Rerun/fallback/stop.
12. Promote only passing outputs.

## Local-first rule

Wave 16 does not require EC2 by default.

EC2 is used only after local static validation passes and a GPU runtime proof is explicitly needed.

## Main Flow relationship

The current Main Flow has static low-denoise examples for SDXL inpaint/detail and cross-engine SDXL refine. These are templates to extract and prove, not automatically promoted production lanes.

## Required implementation artifacts

- image refine bridge plan;
- engine bridge contract;
- low-denoise patch manifest;
- output evidence manifest;
- preservation QA report;
- rerun/fallback report;
- promotion decision.
