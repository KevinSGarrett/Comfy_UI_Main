# Main Session Integration Handoff - 2026-07-19T19:35-05:00

## Integration Summary

- Active integration platform: top-level interactive Cursor subagent under continuous autonomous shift plan / proof-tier pivot.
- Branch: `codex/workflow_plan_update_improvements`
- Policy pivot obeyed: climbed independent local ComfyUI MF70 teeth/mouth-area runtime + direct whole-frame visual QA for TRK-W64-017; historical teeth_mouth_area_v2 seed210826 pass retained; prior forehead/jawline/cheeks/nose/eyebrows/eyelids/mouth_lips VISUAL_QA_PASS_BOUNDED retained; EC2 deferred; Docker/CVAT unused and not treated as ComfyUI proof.
- Writable scope kept DISJOINT from Row069/070/071 sound/BS.1770 / decode_wave64_canonical_audio sibling surfaces.
- Prior fluid masked-inpaint reject, eyes_full_v3b reject, pupils/skin_tone/eyelids/eyebrows/nose/cheeks/jawline/forehead/mouth_lips passes retained truthfully.
- Wave70 mf70_teeth_mouth_area mask-alignment/promotion remains blocked (not overturned; no mask promotion claim).

## Commits Pushed This Pass

1. `PENDING_PRIMARY` Prove Row017 MF70 teeth/mouth-area local visual climb.
2. Tip-stamp commits follow after primary push verify.

Pushed tip verified on origin: `PENDING_TIP`

## Row-Scoped Increment Executed

- Target row: `TRK-W64-017` (`ITEM-W64-017`) global whole-image visual review for localized changes.
- Target proof tiers: `RUNTIME_PASS_BOUNDED` then `VISUAL_QA_PASS_BOUNDED`.
- Highest proof tier achieved: `VISUAL_QA_PASS_BOUNDED`
- Outcome:
  - Posted MF70 teeth/mouth-area localized workflow to **existing** ComfyUI `http://127.0.0.1:8188` (no helper start/stop).
  - Uploaded source + unpromoted teeth_mouth_area v2 mask via `/upload/image`; mask sha `ac9e1a0782f0...` (promotion blocked separately).
  - Seed `4829173651`; realvisxlV50_v50Bakedvae; denoise 0.02; FeatherMask 8px; cfg 3.0; steps 14.
  - Prompt ID: `a9cd9d1f-0ff0-4e43-911d-3f4f82982a05`.
  - Output sha256 `49392114380265c8d176d78cc38dee6a9e072abebb97fcbc05a0ba6bf484e131`.
  - Diff bbox on teeth/mouth `[321, 455, 374, 467]`; blazer mean abs `0.0`; background mean abs `0.0`; 501 changed pixels.
  - Direct visual QA: **canonical pass** (identity/gaze/iris/brows/lids/lashes/nose/cheeks/jawline/forehead/hair/blazer/background/lighting preserved; subtle teeth-edge/mouth-band continuity delta; no open-mouth/smile/lip reshape/plastic skin).
  - Historical MF70 teeth_mouth_area_v2 seed210826 canonical pass retained.
  - Prior fresh forehead climb (`e12cf00b` / tip `e5e99392`) retained.
  - `row_complete`: `false` (historical normalization backlog remains).
- Direct evidence:
  - `Plan/Instructions/QA/Evidence/Wave64/ROW017_LOCAL_RUNTIME_HISTORICAL_CANONICALIZATION_CLIMB_20260719T193000-0500.json`
  - `Plan/Instructions/QA/Evidence/Wave64/TRK-W64-017_LOCAL_RUNTIME_HISTORICAL_CANONICALIZATION_CLIMB_20260719T193000-0500.json`
  - `Plan/Instructions/QA/Evidence/Image_Artifact_QA/ROW017_LOCAL_MF70_TEETH_MOUTH_AREA_VISUAL_QA_20260719T193000-0500.json`
  - `Plan/Instructions/QA/Evidence/Image_Artifact_QA/Row017_Canonical_Global_Reviews/ROW017_LOCAL_MF70_TEETH_MOUTH_AREA_20260719T193000-0500_GLOBAL_REVIEW.json`
  - `Plan/Instructions/QA/Evidence/Workflow_Runtime/W64_LOCAL_COMFYUI_ROW017_MF70_TEETH_MOUTH_AREA_EXECUTE_20260719T193000-0500.json`
  - `Plan/Instructions/Operations/Pulled_Back_Artifacts/local_comfyui_row017_mf70_teeth_mouth_area_20260719T193000-0500/`

## Validators Run

- `python Plan/07_IMPLEMENTATION/scripts/validate_global_whole_image_visual_review.py --input <fresh teeth/mouth + historical teeth_mouth_area_v2 canonical reviews>` -> expected **PASS** each
- `python -m unittest Plan.Instructions.QA.Scripts.test_global_whole_image_visual_review -v` -> expected **9 passed**
- ComfyUI: live local runtime used (`system_stats` / `/free` / `/upload/image` / `/prompt` / `/history` / `/view`)
- Docker/CVAT: unused (not-needed)
- EC2: `EC2_DEFERRED`

## Dirty Ownership Boundary (Preserved)

- Exact-path staging only for Row017 teeth/mouth-area local runtime/visual evidence + tracker/item Notes + this handoff.
- Pre-existing unrelated dirty/untracked paths preserved, including Row069/070/071 sibling surfaces and modified audio decode scripts.
- No `git add -A`, broad reset, restore, or cleanup.

## Blockers

- None for this bounded local climb.
- Row017 remains not COMPLETE pending remaining historical localized canonicalization + future localized candidates that clear whole-frame rejection gates.
- Wave70 mf70_teeth_mouth_area mask-alignment/promotion remains blocked (separate from this Row017 climb).
- EC2 remains deferred by session policy.

## Claims Not Established

- `COMPLETE` / `row_complete=true`
- Promotion authority for the teeth/mouth-area candidate
- Wave70 mask promotion / fail-closed policy clearance
- Overturn of prior fluid masked-inpaint reject
- Overturn of eyes_full_v3b reject

## Exact Next Action

1. Continue Row017 historical localized canonicalization with a fresh W69 contact-shadow or eyeonly local ComfyUI runtime climb + whole-frame visual QA, away from Row069-071.
2. Or climb another tracker-authorized independent local visual/audio proof lane with existing artifacts/workflows.
3. Do not treat Docker/CVAT uptime as ComfyUI proof; keep EC2 deferred.
