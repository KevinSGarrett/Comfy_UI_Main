# SDXL RealVisXL Base Lane Static Certification

- certification_id: CERT-W61-SDXL-REALVISXL-BASE-LANE-STATIC-20260706T064900-0500
- created_at: 2026-07-06T06:48:47-05:00
- artifact: sdxl_realvisxl_base_lane
- result: pass_local_only_runtime_blocked_auth

## Certification

The `sdxl_realvisxl_base_lane` workflow template is authored locally with concrete `workflow.api.json`, `patch_points.json`, `runtime_requirements.json`, and `smoke_test_request.json` files.

Static validation passed with 7 nodes, 9 links, 0 defects, and 0 warnings. The smoke request dry-run built the patched `/prompt` body, kept `execution_allowed=false`, and recorded `generation_executed=false`.

The current QA helper validation now discovers and validates all authored base-generation lanes. It found 2 authored lanes, passed 8 local smoke checks, and reported 0 smoke failures and 0 project-readiness contract failures.

## Evidence

- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_SDXL_REALVISXL_WORKFLOW_STATIC_VALIDATION_20260706T064900-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_SDXL_REALVISXL_WORKFLOW_SMOKE_DRY_RUN_20260706T064900-0500.json`
- `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_SDXL_REALVISXL_WORKFLOW_SMOKE_REQUEST_20260706T064900-0500.json`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_CURRENT_VALIDATION_REALVISXL_20260706T064900-0500.json`

## Runtime Boundary

This certification does not prove EC2 object-info compatibility, RealVisXL checkpoint path resolution, checkpoint hash, model loading, generated output, artifact pullback, or visual QA. Those remain blocked until AWS browser/SSO auth is refreshed and the EC2 runtime gates pass.
