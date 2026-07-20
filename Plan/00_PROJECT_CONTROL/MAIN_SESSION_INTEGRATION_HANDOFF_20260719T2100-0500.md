# Main Session Integration Handoff - 2026-07-19T21:00-05:00

## Integration Summary

- Active integration platform: top-level interactive Cursor subagent under continuous autonomous shift plan / proof-tier pivot.
- Branch: `codex/workflow_plan_update_improvements`
- Policy pivot obeyed: climbed independent local ComfyUI MF70 left-eye runtime + direct whole-frame visual QA for TRK-W64-017; historical left-eye seed210809 pass retained; prior W69 inpaint-nomouth/eyeonly/contact-shadow and MF70 face-region VISUAL_QA_PASS_BOUNDED climbs retained; EC2 deferred; Docker/CVAT unused and not treated as ComfyUI proof.
- Writable scope kept DISJOINT from Row069/070/071 sound/BS.1770 / decode_wave64_canonical_audio sibling surfaces.
- Prior fluid masked-inpaint reject, canny eyeonly full-gen reject, eyes_full_v3b reject, and contact-shadow seed210704 reject retained truthfully.
- No COMPLETE / promotion claim.

## Commits Pushed This Pass

1. `df5a0f9d` Prove Row017 MF70 left-eye local visual climb.
2. `b9224ebd` Stamp Row017 left-eye handoff with primary commit id.
3. `1b0e43ab` Finalize Row017 left-eye handoff tip commit ids.

Pushed tip verified on origin: `1b0e43ab`

## Row-Scoped Increment Executed

- Target row: `TRK-W64-017` (`ITEM-W64-017`) global whole-image visual review for localized changes.
- Target proof tiers: `RUNTIME_PASS_BOUNDED` then `VISUAL_QA_PASS_BOUNDED`.
- Highest proof tier achieved: `VISUAL_QA_PASS_BOUNDED`
- Outcome:
  - Posted W70 MF70 left-eye localized workflow to **existing** ComfyUI `http://127.0.0.1:8188` (no helper start/stop).
  - Re-uploaded Canny v3 identity source + prepared left-eye mask via `/upload/image`; source sha `ea99facf19b7...`; mask sha `2b81866c1d68...`.
  - Seed `4829176503`; realvisxlV50_v50Bakedvae; denoise 0.05; FeatherMask 24px; cfg 3.4; steps 18.
  - Prompt ID: `9810d04a-8197-4f14-a886-b1986f06b6fe`.
  - Output sha256 `a323b31f8aaa4de706c5dfb81a43cd52ef2d5d6ecd7ea2e45b576170fd33b23c`.
  - Diff bbox on subject-left eye `[391, 293, 469, 350]`; mouth/blazer/background/hair/subject-right-eye mean abs `0.0`; 3126 changed pixels.
  - Iris mean RGB stable dark-brown (src ~[79,57,47] vs out ~[80,58,47]).
  - Direct visual QA: **canonical pass** (identity/hair/wardrobe/background/lighting preserved; subtle left eyelid/lash/iris microtexture refinement; subject-right eye unchanged).
  - Historical MF70 left-eye seed210809 pass retained.
  - Prior W69 inpaint-nomouth climb (`13481175` / tip `72188bff`) retained.
  - `row_complete`: `false` (historical normalization backlog remains).
- Direct evidence:
  - `Plan/Instructions/QA/Evidence/Wave64/ROW017_LOCAL_RUNTIME_HISTORICAL_CANONICALIZATION_CLIMB_20260719T205000-0500.json`
  - `Plan/Instructions/QA/Evidence/Wave64/TRK-W64-017_LOCAL_RUNTIME_HISTORICAL_CANONICALIZATION_CLIMB_20260719T205000-0500.json`
  - `Plan/Instructions/QA/Evidence/Image_Artifact_QA/ROW017_LOCAL_MF70_LEFT_EYE_VISUAL_QA_20260719T205000-0500.json`
  - `Plan/Instructions/QA/Evidence/Image_Artifact_QA/Row017_Canonical_Global_Reviews/ROW017_LOCAL_MF70_LEFT_EYE_20260719T205000-0500_GLOBAL_REVIEW.json`
  - `Plan/Instructions/QA/Evidence/Workflow_Runtime/W64_LOCAL_COMFYUI_ROW017_MF70_LEFT_EYE_EXECUTE_20260719T205000-0500.json`
  - `Plan/Instructions/Operations/Pulled_Back_Artifacts/local_comfyui_row017_mf70_left_eye_20260719T205000-0500/`

## Validators Run

- `python Plan/07_IMPLEMENTATION/scripts/validate_global_whole_image_visual_review.py --input <fresh left-eye global review>` -> **PASS**
- `python -m unittest Plan.Instructions.QA.Scripts.test_global_whole_image_visual_review -v` -> **9 passed**
- ComfyUI: live local runtime used (`system_stats` / `/free` / `/upload/image` / `/prompt` / `/history` / `/view`)
- Docker/CVAT: unused (not-needed)
- EC2: `EC2_DEFERRED`

## Dirty Ownership Boundary (Preserved)

- Exact-path staging only for Row017 MF70 left-eye local runtime/visual evidence + tracker/item Notes + this handoff.
- Pre-existing unrelated dirty/untracked paths preserved, including Row069/070/071 sibling surfaces and modified audio decode scripts.
- No `git add -A`, broad reset, restore, or cleanup.

## Blockers

- None for this bounded local climb.
- Row017 remains not COMPLETE pending remaining historical localized canonicalization + future localized candidates that clear whole-frame rejection gates.
- Historical canny eyeonly full-gen reject, contact-shadow seed210704 reject, fluid masked-inpaint reject, and eyes_full_v3b reject remain (not overturned).
- EC2 remains deferred by session policy.

## Claims Not Established

- `COMPLETE` / `row_complete=true`
- Promotion authority for the left-eye candidate
- Overturn of historical canny eyeonly full-gen reject
- Overturn of eyes_full_v3b reject
- Overturn of prior fluid masked-inpaint reject
- Overturn of contact-shadow seed210704 reject

## Exact Next Action

1. Continue Row017 historical localized canonicalization with another independent local visual/audio proof lane away from Row069-071.
2. Prefer remaining MF70 right-eye or expression-region local ComfyUI + whole-frame visual QA using existing prepared masks/workflows.
3. Do not treat Docker/CVAT uptime as ComfyUI proof; keep EC2 deferred.
