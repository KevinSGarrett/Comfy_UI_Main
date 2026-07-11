# RealESRGAN Source Selection And Export Gate Protocol

Status: active

## Purpose

This gate prevents a technically valid RealESRGAN 4x output from replacing a more realistic source solely because dimensions, runtime, and downsample-preservation checks pass.

## Required Inputs

- The source and upscale files must exist and match the registered SHA-256 values.
- Runtime evidence must prove generation, request-hash binding, helper shutdown, and a closed ComfyUI port.
- The output must be exactly 4x the source dimensions.
- Downsample comparison must meet the policy thresholds for SSIM, PSNR, MAE, and mean color shift.
- A completed visual review bound to the same source and output hashes is mandatory. Binding must use explicit schema fields: singleton evidence uses `source_image.sha256` and `generated_image.sha256`; multisource evidence uses one exact `sample_id` with `source.sha256` and `output.sha256`. Hash text appearing elsewhere does not satisfy the gate.

## Decision Rules

1. Missing, ambiguous, unbound, or invalid evidence returns `hold_fail_closed_missing_or_invalid_evidence`.
2. A technical failure returns `reject_upscale_technical_failure`.
3. A blocking visual regression or explicit retain-source disposition returns `retain_source_reject_upscale_as_preferred`.
4. A visually acceptable upscale needed only for resolution delivery returns `conditional_resolution_export_retain_source_master`.
5. Only an explicit visual preference with no blocking regression returns `prefer_upscale_export`.
6. Local selection never implies target-runtime or final production export approval.

Scalar metrics are preservation checks, not perceptual authority. Waxy skin, false detail, oversharpened fabric, identity changes, anatomy changes, and composition defects require explicit visual judgment. The source master is never deleted by this gate.

## Canonical Artifacts

- Policy: `Plan/10_REGISTRIES/realesrgan_export_selection_policy.json`
- Candidate registry: `Plan/10_REGISTRIES/realesrgan_export_candidate_registry.json`
- Evaluator: `Plan/07_IMPLEMENTATION/scripts/evaluate_realesrgan_export_selection.py`

The current candidate matrix covers the corrected Canny portrait, Normal full-body portrait, and two-character contact output already proven locally. It does not authorize new generation, AWS/EC2 work, mask claims, Wave70 hard-gate replay, or Wave71+ activation.
