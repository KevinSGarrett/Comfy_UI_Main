# Main Session Integration Handoff — 2026-07-20T22:44-05:00

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- This pass: RunPod `1q4ji0gg1fkhvt` mechanical smoke **PASS** (evidence-only)
- Tip evidence: `Plan/Instructions/QA/Evidence/Runtime_Readiness/RUNPOD_1q4ji0gg1fkhvt_MECHANICAL_SMOKE_PASS_20260720T2244-0500.json`
- Tip SHA256: `0144FF7DAD52058E021F29CD4FDF69DAA02506CEBEF29BF44D5C7D98747D033D`
- ComfyUI v0.28.0 UP on pod loopback; models symlink → `/workspace/ComfyUI/models`; RTX 6000 Ada; **no restart**
- No local Comfy / Row073 PCM / CSV / COMPLETE / HOLD 090+

## Exact next action

1. Use RunPod as runtime authority for ComfyUI API and GPU work.
2. Leave Row073 alone; CSV via mutator only.
