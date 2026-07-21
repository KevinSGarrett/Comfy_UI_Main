# Main Session Integration Handoff — 2026-07-20T22:50-05:00

## Integration Summary

- Active platform: interactive Cursor (integration authority)
- Local authority: `C:\Comfy_UI_Main`
- Branch: `codex/workflow_plan_update_improvements`
- This pass: hash-bound **local vs pod `/workspace/wave64` git divergence** handoff + sync recommendation (evidence-only)
- Tip evidence: `Plan/Instructions/QA/Evidence/Runtime_Readiness/RUNPOD_WAVE64_LOCAL_POD_GIT_DIVERGENCE_HANDOFF_20260720T2250-0500.json`
- Evidence SHA256: `d45a6d501299b8de63abd8437811625c2206278030c54258189a8bf36f5c505f`
- No COMPLETE / Row073 PCM / shared CSV mutation / `reset --hard` wipe

## Hash-bound tips

| Role | Ref | Full SHA |
|------|-----|----------|
| Pod `/workspace/wave64` (reported `main`) | `a3bff6b` | `a3bff6b35d7a54667876d2c2016c5a40542b4e94` |
| Local user-cited tip | `e3b9cbaf` | `e3b9cbaf863786ff2114150a74604959cef0d669` |
| Local measurement tip (pre-land) | `afcd084d` | `afcd084db2a0fcad26abd991ec842461b73c9613` |
| Merge-base | `567117f3` | `567117f3cdd151fd504475eb35dd0ff800bfe9f5` |

## Divergence counts

`git rev-list --left-right --count a3bff6b...<local>` → `pod_main_not_in_local` / `local_not_on_pod`

| Local tip | pod-not-in-local | local-not-on-pod |
|-----------|------------------|------------------|
| `e3b9cbaf` (user-cited) | **99** | **425** (~426) |
| `afcd084d` (measurement) | **99** | **430** |

## Recommendation

- **Keep git commits local** — local remains git authority; do not rebase/reset pod onto local via wipe.
- Pod runtime sync — choose one:
  - **(A)** fetch + checkout `codex/workflow_plan_update_improvements` with care for `Runtime_Data` untracked / models symlink
  - **(B)** bounded rsync of `Plan/` + scripts only
- **Do NOT** `git reset --hard` wipe the pod workspace.

## Boundaries honored

- No COMPLETE / Row073 PCM / CSV / local ComfyUI start / workspace wipe / bulk model re-upload

## Exact next action

1. Keep commits on local `codex/workflow_plan_update_improvements`.
2. For pod Comfy runtime: **(A)** feature-branch checkout (Runtime_Data-safe) or **(B)** Plan/scripts rsync — never hard-reset wipe.
3. Leave Row073 alone.
