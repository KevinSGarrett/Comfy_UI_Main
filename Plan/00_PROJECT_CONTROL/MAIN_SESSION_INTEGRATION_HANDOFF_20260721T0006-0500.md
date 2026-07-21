# Main Session Integration Handoff — 2026-07-21T00:06-05:00

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- This pass: **WAVE64 RunPod hard runtime binding** — NEVER start/use EC2 for Wave64/Comfy/GPU/model recovery
- Tip evidence: `Plan/Instructions/QA/Evidence/Runtime_Readiness/WAVE64_RUNPOD_HARD_RUNTIME_BINDING_20260721T0006-0500.json`
- Tip SHA256: `11C696D5182CB0BAE8C0A163DE23964F14ACA4EDF09D0F6FC132968DC7DD67EB`
- **Hard binding:** Sole runtime = RunPod `1q4ji0gg1fkhvt` — `/workspace/wave64`, `/workspace/ComfyUI`, `source /workspace/paths.env`
- EC2: **FORBIDDEN** for Wave64/Comfy/GPU generation and model recovery (remains stopped; no live authority)
- Wan 019/023: **Class F** retained — 0/3 payloads on pod; prior binding citations retained
- `row_complete=false`; no COMPLETE; Row074 untouched; CSV deferred

## Exact next action

1. Route all Wave64/Comfy/GPU generation and model recovery through RunPod `1q4ji0gg1fkhvt` only (`source /workspace/paths.env`).
2. Do **not** start or use EC2 for Wave64, ComfyUI, GPU, or model recovery.
3. Leave Row074 alone; CSV via mutator only; no COMPLETE.
