# SDXL low-risk fallback template

This directory contains the first concrete executable draft for the `sdxl_low_risk_fallback_lane` base generation workflow template.

## Files

- `workflow.api.json`
- `patch_points.json`
- `runtime_requirements.json`
- `smoke_test_request.json`
- `object_info_proof.json` (pending EC2 object-info capture)
- `first_output_evidence.json` (pending bounded EC2 execution)

## Promotion rule

This template is not promoted until object_info, model-loading, output, and QA evidence pass.
