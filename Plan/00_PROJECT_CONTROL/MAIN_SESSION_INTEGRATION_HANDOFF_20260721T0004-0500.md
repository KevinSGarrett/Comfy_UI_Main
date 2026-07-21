# Main Session Integration Handoff — 2026-07-21T00:04-05:00

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Branch: `codex/workflow_plan_update_improvements`
- This pass: TRK-W64-019/023 **RunPod binding authority correction** — EC2 Wan recovery **UNAUTHORIZED** vs user RunPod handoff
- Tip evidence: `Plan/Instructions/QA/Evidence/Wave64/TRK-W64-019_023_RUNPOD_BINDING_AUTHORITY_CORRECTION_20260721T0004-0500.json`
- Tip SHA256: `5CBB6E60A5DD2DC47CBB0B3086B2A7A917F2A079E9F28F5E0500EA66E3B73B9E`
- Binding runtime: RunPod `1q4ji0gg1fkhvt` only — `/workspace/wave64`, `/workspace/ComfyUI`, `/workspace/paths.env`
- EC2: **EC2_DEFERRED** — do not start/use for generation or Wan model recovery
- Wan 019/023: **Class F** retained — 0/3 payloads on pod; no clearance until 3/3 hash-bound on pod without EC2
- `row_complete=false`; no COMPLETE; Row074 untouched; CSV deferred

## Exact next action

1. Recover Wan TI2V payloads on pod `1q4ji0gg1fkhvt` via RunPod-authorized paths only (pod-local, S3→pod, or user-directed transfer).
2. Do not start EC2 or use EC2-mediated copy for generation or model recovery.
3. Keep Class F until 3/3 hash-bound on pod; leave Row074 alone; CSV via mutator only; no COMPLETE.
