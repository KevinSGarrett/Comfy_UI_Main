# Done Certification: ComfyUI Workflow Smoke Helper Dry Run

- Certification ID: CERT-W61-COMFY-WORKFLOW-SMOKE-HELPER-DRY-RUN-20260706T025536-0500
- Task / Tracker ID: TRK-W61-006
- Title: SDXL low-risk ComfyUI smoke helper dry-run validation
- Artifact Scope: `Plan/Instructions/Operations/Scripts/Invoke-ComfyWorkflowSmoke.ps1`; `Plan/07_IMPLEMENTATION/workflow_templates/base_generation/sdxl_low_risk_fallback_lane/*`
- Implementation Summary: Added a bounded ComfyUI API smoke helper that builds the `/prompt` request body from the selected lane workflow, patch map, and smoke request. The helper is dry-run by default and blocks execution until static proof exists or the smoke request explicitly allows execution.
- Tests Performed: PowerShell parser validation; dry-run request generation; JSON parse validation for generated evidence and request body.
- QA Summary: Dry-run passed and generated a patched request body covering prompt, negative prompt, seed, sampler settings, latent resolution, checkpoint, and save prefix. No generation was executed.
- Evidence Paths: `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_COMFY_WORKFLOW_SMOKE_DRY_RUN_20260706T025536-0500.json`; `Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_COMFY_WORKFLOW_SMOKE_REQUEST_20260706T025536-0500.json`
- Known Issues: `BLOCKER-AWS-AUTH-EXPIRED-001`; local ComfyUI runtime remains absent.
- Final Decision: pending_runtime_validation
- Certifier: Codex Desktop autonomous release manager
- Timestamp: 2026-07-06T02:55:36-05:00
