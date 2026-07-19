# Main Session Migration Handoff - 2026-07-19

This handoff freezes the outgoing Main session at 2026-07-19T07:03Z. A fresh, non-forked Main session should resume from this repository state. The outgoing session must perform no further project work, monitoring, or worker-intent creation after committing this file.

## Repository State

- Project root: `C:\Comfy_UI_Main`
- Current branch: `codex/workflow_plan_update_improvements`
- Project-work HEAD immediately before this handoff-only commit: `07f27188b237653c51efccab598a4ccd559673c4`
- The repository HEAD after migration is the commit containing this file; its exact ID is reported in the outgoing session terminal message.
- Current branch has no configured upstream.
- Pushed Row093 branch: `origin/codex/wave64-row093-clip-preparation-audit-20260719` at `883e7afe74505220ea6e1e6246a22a4049574caa`
- Pushed Row094 branch: `origin/codex/wave64-row094-layered-foley-audit-20260719` at `9ec94f98edd552ee944533206a6430107f9f4cba`
- Pushed Row095 branch: `origin/codex/wave64-row095-spatial-audio-audit-20260719` at `07f27188b237653c51efccab598a4ccd559673c4`
- Snapshot refs resolve to the same commits:
  - `refs/codex/snapshots/wave64-row093-clip-preparation-audit-20260719`
  - `refs/codex/snapshots/wave64-row094-layered-foley-audit-20260719`
  - `refs/codex/snapshots/wave64-row095-spatial-audio-audit-20260719`

## Dirty Worktree Ownership

The pre-handoff worktree contains 396 unrelated modified or untracked entries. They predate this handoff and are intentionally preserved. Do not broad-stage, clean, reset, restore, or rewrite them.

- Autonomous sound package ownership includes untracked schemas, builders, registries, and evidence under `Plan/08_SCHEMAS`, `Plan/07_IMPLEMENTATION`, `Plan/10_REGISTRIES`, and `Plan/Instructions`.
- FLUX.2 paths, portfolio-reconciliation paths, worker-control source/snapshots/worktrees, model inventories, workflow assets, and visual-QA artifacts have separate existing ownership.
- Four pre-existing untracked files under `Plan/00_PROJECT_CONTROL` are unrelated and must remain untouched:
  - `WAVE64_AUTONOMOUS_MODEL_INTELLIGENCE_AND_SELECTION_MASTER_PLAN.md`
  - `WAVE64_AUTONOMOUS_VIDEO_TO_AUDIO_AND_SOUND_GENERATION_MASTER_PLAN.md`
  - `WAVE64_HYPERREAL_VIDEO_AUDIO_APP_THIRD_PASS_MASTER_PLAN.md`
  - `WAVE64_ULTIMATE_MODULAR_CHARACTER_TO_MULTIMODAL_WORKFLOW_MASTER_PLAN.md`
- This migration commit may contain only this handoff file.

## Tracker Continuation

- Latest completed row: `TRK-W64-095` spatial audio renderer current-delta audit.
- Row095 evidence: `Plan/Instructions/QA/Evidence/Wave64/TRK-W64-095_SPATIAL_AUDIO_RENDERER_CURRENT_DELTA_20260719.json`
- Row095 evidence SHA-256: `77bfab212871f3e8fd4fe76adb41f3ae8e0cc0b28c81f52e9e2e60ad9214e46e`
- Row095 result: 13 PASS / 15 FAIL; technical reuse is supported, while seven schema fail-open findings remain.
- Next actionable row: `TRK-W64-096` room impulse response, early reflection, RT60, and convolution renderer.
- Row096 has read-only investigation only; its required evidence file does not exist and no Row096 project file was written.
- The already-started Row096 focused suite completed: `55 passed in 110.69s`; stdout SHA-256 `60f3a3b9b41b206618ac1145adbdf19ba739cae0141d8dc9e4863688ea072f57`, stderr empty SHA-256 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.
- Row096 should determine whether the existing strict evaluator/producer merely evaluates rendered media or also satisfies the required RIR selection/synthesis and dry-source convolution contract. Do not infer completion from the green focused suite.

## Signed Worker Requests

These are the only request records observed as `QUEUED` during the migration readback. Do not replay, duplicate, edit, wake, or bypass them; resolve them through their signed records in the replacement session.

### Cursor implementation

- Request ID: `p000_20260719T061707117Z_row091_wave30_manifest_truth_hardening_v2_32019b57`
- Intent ID: `intent_20260719T061703902Z_row091_wave30_manifest_truth_hardening_v2_cb1611c7`
- Request path: `C:\Users\kevin\.codex\ai_worker_dispatcher\queue\Cursor\p000_20260719T061707117Z_row091_wave30_manifest_truth_hardening_v2_32019b57.json`
- Request SHA-256: `0f77067c2a62f3525f4a05f6a6aedfaf0590162f7cbf8f722bfb734e308de64d`
- Scope packet: `C:\Comfy_UI_Main\runtime_artifacts\agent_handoffs\scope_packets\20260719T011707-0500_row091_wave30_manifest_truth_hardening_v2.json`
- Scope SHA-256: `39a135589edc6fa7d00a0d42eef27db3bfe87bf52605c5fb08259a49c2a259e6`
- Allowed paths:
  - `Plan/07_IMPLEMENTATION/scripts/compile_wave30_audio_event_manifest.py`
  - `Plan/Instructions/QA/Scripts/test_wave30_audio_pipeline_strict.py`
- Dependency: `p000_20260719T061706055Z_row091_wave30_manifest_truth_hardening_v2_sonnet_preflight_c370584f`

### Claude semantic review

- Request ID: `p001_20260719T061708386Z_row091_wave30_manifest_truth_hardening_v2_sonnet_review_206f6055`
- Intent ID: `intent_20260719T061703902Z_row091_wave30_manifest_truth_hardening_v2_cb1611c7`
- Request path: `C:\Users\kevin\.codex\ai_worker_dispatcher\queue\Claude\p001_20260719T061708386Z_row091_wave30_manifest_truth_hardening_v2_sonnet_review_206f6055.json`
- Request SHA-256: `5d7c37e853fcc897653da5ee0e3f9ce7b21e3d02e447e7da42fb354d7c6442ae`
- Scope packet: `C:\Comfy_UI_Main\runtime_artifacts\agent_handoffs\scope_packets\20260719T011708-0500_row091_wave30_manifest_truth_hardening_v2_sonnet_review.json`
- Scope SHA-256: `9e6db1dfc5971919beb27dbff14e4cab3770278e4a063ecc6aaa9eac5f9e2656`
- Allowed paths: none; review is read-only.
- Dependency: `p000_20260719T061707117Z_row091_wave30_manifest_truth_hardening_v2_32019b57`

The earlier Row093 intent `intent_20260719T063709548Z_row093_canonical_clip_preparation_contract_v1_daf31700` failed before request/provider use because `RiskClass high` was incompatible with `balanced_default`. It has no request ID and must not be replayed unchanged.

## Runtime And Service State

Observed read-only at 2026-07-19T07:03Z:

- `WslService`: Running / Automatic.
- `com.docker.service`: Stopped / Manual. Docker was not started or probed by this handoff.
- All five `ComfyUIMain AI Worker` scheduled tasks are `Disabled` with `enabled=false`.
- All four `MaskFactory` maintenance tasks are `Disabled` with `enabled=false`.
- Relevant non-self dispatcher, wrapper, and Cursor-agent process count: zero.
- No provider, wrapper, WSL command, Docker job, EC2 call, scheduled-task wake, or model/runtime operation was initiated while producing this handoff.

## Holds And Boundaries

- Persistent worker scheduling remains disabled. Do not enable or start any worker or maintenance task by implication.
- Row091 queued request paths are frozen pending governed processing and adoption; do not implement their allowed paths locally in parallel.
- Row093 canonical-clip worker scope remains unrequested after admission failure; do not reuse the failed intent bytes.
- Row096 is locally actionable for Codex-owned PM/QA/integration work, but implementation work must respect current worker ownership and intake policy.
- Preserve all worker-control refs, retained worktrees, signed queue/control records, scope packets, CAS evidence, and recovery artifacts.
- Preserve all FLUX.2, portfolio-reconciliation, autonomous-sound, model, workflow, visual-QA, and tracker dirty paths under their existing ownership.

## No Delete / No Replay

1. Do not delete, clean, reset, restore, stash, or broad-stage any pre-existing dirty path or retained worktree.
2. Do not delete or rewrite signed intents, requests, controls, scope packets, adoption records, snapshots, CAS objects, or terminal evidence.
3. Do not replay terminalized or failed intent/request bytes, including the failed Row093 intent.
4. Do not duplicate or locally implement the two queued Row091 scopes while their signed records remain unresolved.
5. Do not call Cursor or Claude wrappers directly and do not enable scheduled worker lanes.
6. Resume from Row096 in a fresh non-forked Main session after verifying this handoff commit and the then-current dirty ownership boundary.
