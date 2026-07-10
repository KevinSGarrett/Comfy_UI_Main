## Decision - Zero Verified Models Can Never Pass Local Generation Readiness - 2026-07-10T16:03:05-05:00

Require selected-lane runtime requirements to exist, parse, and declare at least one model with a nonempty filename/subdirectory and valid SHA256; require every declaration to resolve in the selected ComfyUI or project model tree and match the observed file SHA256 before `local_required_models_present` or local GPU generation candidacy can pass. A runnable local GPU candidate is a cost-control option only and does not replace generated artifact review or EC2 final proof.

## Decision - Root Preflight Must Always Emit Structured Evidence - 2026-07-10T14:28:34-05:00

Treat missing Git metadata, unavailable status, and empty lane arrays as ordinary failing checks, not exceptional termination paths. Git root/HEAD/origin availability is determined from returned values because successful Windows `git rev-parse` calls can leave `$LASTEXITCODE=-1`; worktree cleanliness still requires a successful `git status`. Disposable fixture success does not close the actual global Git checkpoint work order.

## Decision - Supplied Publish Evidence Must Fail With Structured Records - 2026-07-10T13:46:46-05:00

Treat omitted publish evidence, a supplied missing path, invalid JSON, a non-object JSON payload, and parsed linkage mismatch as distinct validator states. Strict omission remains `strict_warning_failure`; supplied missing, malformed, and non-object records use `publish_evidence_missing`, `publish_evidence_json_invalid`, and `publish_evidence_payload_invalid`; parsed contract drift uses `publish_linkage_mismatch`. Do not accept an exception or null payload without a durable failing JSON result as adequate fail-closed evidence.

## Decision - Canonical OpenPose Uses The Tabletop-Hands Source - 2026-07-10T13:18:52-05:00

Use `controlnet_openpose_hands_tabletop_w69_v1.png`, not `controlnet_openpose_w69_v1.png`, as the canonical OpenPose control image. Its source manifest, active input copy, workflow default, runtime requirements, smoke request, package, transfer URI, and pre-EC2 handoff now agree. Do not regress to the older head-and-shoulders map or treat this local canonicalization as target-runtime proof or final hand certification.

## Decision - Freeze Local ControlNet Readiness Until Inputs Or Live Selection Change - 2026-07-10T12:49:30-05:00

Do not rerun package, deploy, publish-dry-run, asset-transfer, or pre-EC2 handoff generation for depth, lineart, openpose, or normal unless a source contract, local asset, bundle, helper, Git authority, or explicit live selection changes. The current matrix is the local handoff authority; further repetition would be bookkeeping, not implementation progress.

## Decision - ControlNet Transfer Bundles Remain Lane-Self-Contained - 2026-07-10T12:38:40-05:00

Each ControlNet lane transfer bundle carries its own six-child contract even though all four share the same checkpoint URI and SHA256. The matrix verifies that shared identity while retaining lane-independent ControlNet and input URIs. This makes later explicit live selection auditable without allowing one lane's proof to imply another lane's runtime completion.

## Decision - Canonical Normal Control Map Is normal_bae - 2026-07-10T12:16:17-05:00

For `sdxl_realvisxl_controlnet_normal_lane`, validate `required_input_assets.control_map_type` exactly as `normal_bae` while matching `control_family` with the broader `normal` token. Do not normalize the asset contract down to `normal`; the four-lane matrix proves the exact current schema across depth, lineart, openpose, and normal.

## Decision - Use Composed ControlNet Package Validation Before Live Selection - 2026-07-10T12:10:17-05:00

Use `Test-ControlNetSelectedLanePackageDeployConsistency.ps1` for depth, lineart, openpose, and normal package/deploy preparation. It must compose the generic validator and pass lane identity, required model, control family, control image, smoke binding, and packaged contract hashes. A local pass does not authorize upload, EC2, generation, promotion, certification, or Item/Tracker completion.

## Decision - mf70_teeth_mouth_area Morphology-Only Repair Is Blocked - 2026-07-10T06:19:25-05:00

Use `Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MF70_TEETH_MOUTH_AREA_ANISOTROPIC_ROUTE_SEARCH_20260710T061925-0500.json` as the current teeth-mouth route-family decision. A 6,471-route anisotropic morphology/shift search did not produce a combined-gold pass. Stop morphology-only tuning for this row; use a non-morphology boundary route, explicit row policy, or another blocked row.

## Decision - mf70_teeth_mouth_area V2 Is Not Combined-Gold Supported - 2026-07-10T06:11:35-05:00

Use `Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MF70_TEETH_MOUTH_AREA_V2_COMBINED_GOLD_EVAL_20260710T061135-0500.json` as the current teeth-mouth v2 decision. The route passes CelebAMask-HQ but fails LaPa, so it is blocked by combined gold and must not be promoted. Earlier target-specific/local generated proof remains useful only as downstream evidence, not as gold route support.

## Decision - mf70_eyebrows Policy Is Fail-Closed Under Current Evidence - 2026-07-10T06:02:00-05:00

Use `Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_EYEBROW_DATASET_RUNTIME_POLICY_DECISION_20260710T060200-0500.json` as the current eyebrow policy decision. `mf70_eyebrows` cannot be promoted through dataset-vs-runtime policy because both CelebAMask-HQ and LaPa block the current eyebrow routes, and no stronger local automatic eyebrow parser is registered. Switch to another blocked row or register a new parser before resuming eyebrow work.

## Decision - No Stronger Local Eyebrow Parser Is Registered - 2026-07-10T05:53:08-05:00

Use `Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_EYEBROW_SEMANTIC_PARSER_OPTIONS_AUDIT_20260710T055308-0500.json` as the current eyebrow parser-options decision. The local registered assets do not currently provide a stronger automatic eyebrow semantic parser than the failed BiSeNet-backed route. Do not continue eyebrow parser/landmark band tuning with these same assets; next work must be an explicit eyebrow policy, a newly registered stronger face parser, or a different blocked row with a new gold-backed route.

## Decision - Eyebrows Are Not Solved By Parser+Landmark Band Tuning - 2026-07-10T05:40:03-05:00

Use `Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_LAPA_PARSER_LANDMARK_BROW_ROUTE_EVAL_20260710T054003-0500.json` as the current brow route decision. Parser+LaPa-landmark combinations do not clear LaPa gold labels: conservative intersections miss too much brow, while broader unions exceed false positives. Continue with stronger semantic parsing, an explicit eyebrow policy split, or another blocked row; do not keep retuning brow landmark bands as-is.

## Decision - LaPa Eye Pass Is Diagnostic Until Runtime 106-Point Source Exists - 2026-07-10T05:31:26-05:00

Use `Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_RUNTIME_106_LANDMARK_SOURCE_AUDIT_20260710T053126-0500.json` as the local runtime landmark-source decision. No LaPa-compatible 106-point runtime route is currently available, so the LaPa supplied-landmark `mf70_eyes_full` pass cannot support target-portrait promotion. Register a 106-point runtime route or use a different segmentation authority before any eye-mask promotion.

## Decision - LaPa Eye Target Is Reachable With Supplied 106-Point Landmarks - 2026-07-10T05:25:14-05:00

Use `Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_LAPA_SUPPLIED_LANDMARK_EYE_BROW_ROUTE_EVAL_20260710T052514-0500.json` as the current eye/brow landmark diagnostic. LaPa supplied landmarks pass `mf70_eyes_full`, so the eye issue is the available runtime landmark/route source, not an impossible gold target. `mf70_eyebrows` remains blocked even with supplied landmarks, so brow work needs semantic parsing or a policy split rather than another landmark hull.

## Decision - Eye/Brow Route Failure Is Not Just Combined-Gate Aggregation - 2026-07-10T05:15:35-05:00

Use `Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_EYE_BROW_ROUTE_DATASET_FAILURE_DIAGNOSTIC_20260710T051535-0500.json` as the current eye/brow route diagnostic. The tested MediaPipe-only and parser+MediaPipe hybrid families do not pass even when split by CelebAMask-HQ versus LaPa. Do not keep tuning this route family as-is; use stronger segmentation, a policy split, or a different blocked row.

## Decision - MediaPipe And Hybrid Eye/Brow Routes Are Still Not Enough - 2026-07-10T05:06:51-05:00

Do not promote or target-proof `mf70_eyes_full` or `mf70_eyebrows` from the tested MediaPipe-only or parser+MediaPipe hybrid route families. Evidence `Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MEDIAPIPE_EYE_BROW_COMBINED_ROUTE_EVAL_20260710T045530-0500.json` and `Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_EYE_BROW_HYBRID_ROUTE_EVAL_20260710T045957-0500.json` shows no candidate clears the combined gold gate. Continue with stronger segmentation, explicit dataset-policy work, or another blocked row rather than repeating these route families.

## Decision - Eye/Brow Label Geometry Is Not Sufficient - 2026-07-10T04:46:26-05:00

Do not continue simple eye/brow geometry tweaks as-is. Evidence `Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_EYE_BROW_LABEL_GEOMETRY_ROUTE_EVAL_20260710T044626-0500.json` shows eyes remain under-covered and eyebrows remain below the combined gold IoU gate. Future eye/brow repair needs a stronger landmark/model-backed aperture and brow route or an explicit dataset-policy split.

## Decision - mf70_hair Needs Stronger Person-Instance Authority - 2026-07-10T04:37:26-05:00

Do not continue anchor-window/component-only `mf70_hair` repairs as-is. Evidence `Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_MF70_HAIR_SUBJECT_INSTANCE_ROUTE_EVAL_20260710T043726-0500.json` shows the best route still fails combined gold gates, primarily due to LaPa false positives from neighboring/background hair. Hair needs stronger person-instance/foreground segmentation or an explicit dataset policy split before target-portrait proof.

## Decision - Stop Simple Facial Postprocess Repairs For Blocked Rows - 2026-07-10T04:27:52-05:00

Use `Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_COMBINED_GOLD_POSTPROCESS_ROUTE_EVAL_20260710T042752-0500.json` as the blocker for simple morphology/component cleanup on the disputed facial rows. Dilation/erosion/open/close/largest-component cleanup is not enough for eyes, eyebrows, hair, lips, teeth-mouth, face-skin, or neck across combined gold evidence. Continue with model-backed, label-aware, subject-instance-aware, or explicit policy-split routes only.

## Decision - Combined Gold Gate Is Required Before Facial Target Proof - 2026-07-10T04:18:40-05:00

Use `Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_FACIAL_COMBINED_GOLD_GATE_DECISION_20260710T041840-0500.json` as the current facial route decision record. Only `mf70_nose` is supported by both current gold gates; all other checked facial rows require repair or policy separation before generated target-portrait proof can mean anything.

## Decision - Wave70 Facial Masks Require Combined Gold-Dataset Evidence - 2026-07-10T04:13:48-05:00

Do not treat the generated target portrait as the primary facial-mask proof. Use CelebAMask-HQ and LaPa gold benchmarks first, then use target-portrait overlays and generated-output QA only as downstream sanity checks. Current LaPa gate evidence `Plan/Instructions/QA/Evidence/Mask_Factory/Wave70/W70_FACIAL_LAPA_GOLD_BENCHMARK_GATE_20260710T041348-0500.json` blocks 7 of 9 LaPa-covered facial regions, so remaining facial repair work must be route/policy driven rather than single-image hand tuning.

## Decision - Wave70 Eyes Full Source-Landmark Repair Candidate V2 - 2026-07-09T21:53:00-05:00

For the user-disputed eye/eyebrow drift, do not reuse the broad oval `mf70_eyes_full` mask. Use the v2 source-landmark repair candidate as the current review target, but keep it candidate-only until strict visual QA and Wave70 geometry/promotion evidence explicitly support promotion. The failed v1 panel is retained only as local evidence of the correction loop.

## Decision - Selected Inpaint QA Helper Dirty-Git Gate Retest - 2026-07-09T21:32:39-05:00

QA helper smoke tests must validate the corrected current-worktree gate behavior. If `Test-ActiveRuntimeQueueFinalCertificationReadiness.ps1` reports a dirty current worktree after a stored clean Git gate, `git_gate_summary.passes_for_ec2_execute` must be false and final blockers must include `current_worktree_dirty_after_stored_git_gate:*`.

## Decision - Selected Inpaint Post-Alignment Scoped Checkpoint Dry-Run - 2026-07-09T21:17:00-05:00

Use a scoped checkpoint boundary for the selected-inpaint post-alignment evidence slice. Do not include unrelated `FLEET_HEALTH_AUDIT_20260709T000000-0500.json` in this slice. The dry-run did not stage, commit, or push; it only proves the scope and secret/blocked-path checks.

## Decision - Selected Inpaint Post-Alignment Final-Cert Closure Refresh - 2026-07-09T21:02:00-05:00

Final-certification readiness must use current local Git status, not only the latest stored dry-run gate. `Test-ActiveRuntimeQueueFinalCertificationReadiness.ps1` was updated to record current `git status --porcelain` and force EC2/final readiness closed when current local evidence makes the worktree dirty. Continue local-only closure work; do not treat this as live runtime proof.

## Decision - Selected Inpaint Final Certification Blocker After Chain Alignment - 2026-07-09T20:59:11-05:00

Do not use pre-alignment final-review closure or stale clean-gate evidence as proof of final readiness. Treat selected-inpaint final certification as blocked until the local final-certification closure is refreshed from the aligned chain and live/runtime QA evidence exists.

## Decision - Selected Inpaint Publish Dry-Run Chain Alignment Current - 2026-07-09T20:49:40-05:00

Treat the selected-inpaint publish dry-run chain as locally aligned but not live-authorized. Preserve the fail-closed boundary and continue only local certification/blocker work until explicit live intent and live-gate proofs exist.

## Final Review Coverage Is Accounted, Do Not Loop Packets - 2026-07-09T17:45:00-05:00

Decision: use `W66_ACTIVE_RUNTIME_QUEUE_FINAL_REVIEW_EVIDENCE_COVERAGE_20260709T174241-0500.json` as the current local accounting record for final-review packet coverage. It has 0 missing review-evidence rows, so do not regenerate final-review blocker packets unless a new lane/work-order/evidence file changes the coverage inputs.

Decision boundary: this is local evidence coverage only. It does not close open final-review work orders, authorize S3 Execute, start EC2, certify target-runtime proof, promote masks, rerun Wave70 hard gates, activate Wave71+, or mutate Jira.

## Checkpoint Evidence Must Use Post-Commit Git Snapshot - 2026-07-09T15:42:24-05:00

Decision: checkpoint evidence emitted after Execute/Push must recompute every Git status-derived counter, preview, and scope field from the post-commit/post-push worktree. Stale pre-commit porcelain counts must not coexist with clean_worktree=true because those records can mis-gate selected runtime orchestration.

Decision boundary: this is a local operations-helper correctness fix only. It does not authorize S3 Execute, EC2 start, ComfyUI generation, mask promotion, Wave70 hard gates, Wave71+ activation, or Jira mutation.

## Selected Inpaint Post-Rebuild Chain Is Local-Ready But Live-Blocked - 2026-07-09T15:35:00-05:00

Decision: use the post-rebuild selected-inpaint package readiness, launch gate, pre-EC2 handoff, live runbook, and execution-readiness snapshot as the current local authority for the selected runtime lane. These artifacts point at rebuilt bundle SHA256 089a7a411f9380c4f737a8d246d1ade29799d59c1fcba95aaf4dde4bcbd68bcb and preserve fail-closed live gates.

Decision boundary: this is not authorization for S3 Execute, EC2 start, EC2 install, ComfyUI generation, final certification, mask promotion, Wave70 hard gates, Wave71+ activation, or Jira mutation. Continue local source-of-truth project work and require explicit live intent before any external/runtime action.

## Local Source Of Truth Overrides Stale EC2 Workspace - 2026-07-09T12:28:07-05:00

Decision: local `C:\Comfy_UI_Main` is the authoritative execution ledger for Items, Tracker, hydration, runtime-lane queue, selected next action, and completed-work status. EC2 `/home/ubuntu/Comfy_UI_Main` is runtime/cache state only and cannot reopen completed work or override local evidence.

Decision boundary: if EC2 and local disagree, classify `EC2_WORKSPACE_STALE_NOT_AUTHORITY`, use local evidence, and continue selected local-first ComfyUI runtime/orchestration work. Do not rerun completed fallback/base/Canny/certification-sample/local-smoke work from stale EC2 queue state.

## S3 Publish Path Is Prepared But Not Upload-Ready - 2026-07-09T09:37:06-05:00

Decision: the selected inpaint deploy bundle may proceed to S3 publish dry-run only after the explicit manifest-scoped checkpoint, clean Git proof, selected deploy-bundle rebuild, package/deploy matrix recheck, and S3 readiness recheck have all passed against a concrete rebuilt manifest and zip.

Decision boundary: do not automatically upload to S3, contact AWS, rebuild, start EC2, or generate. The current artifact is a readiness plan and command ledger, not publish authorization.

## Selected Inpaint Rebuild Command Is Prepared But Not Executed - 2026-07-09T09:28:34-05:00

Decision: the selected inpaint target-runtime path should rebuild its deploy bundle from `runtime_artifacts/g9_20260709T030509/r/sdxl_realvisxl_inpaint_detail_lane_ci_preflight/RUN_PACKAGE_MANIFEST.json` only after the manifest-scoped checkpoint is explicitly executed and clean Git proof passes.

Decision boundary: do not automatically rebuild, publish to S3, start EC2, or generate. The current artifact is a rebuild input plan, not a deploy bundle.

## Post-Checkpoint Runtime Revalidation Must Follow Manifest Checkpoint - 2026-07-09T09:22:50-05:00

Decision: after an explicit manifest-scoped checkpoint is executed, the next runtime path must rerun clean Git proof, package/deploy matrix, selected inpaint deploy-bundle rebuild from clean source, S3/runtime readiness, target-runtime execution plan, and runtime handoff before any live EC2 proof.

Decision boundary: do not automatically stage, commit, push, rebuild deploy bundles, publish to S3, start EC2, or generate. The revalidation plan is a command sequence and blocker ledger, not authorization for live work.

## Use Manifest-Scoped Checkpoint Only With Explicit Intent - 2026-07-09T09:16:48-05:00

Decision: the next checkpoint execute path should use `W66_SCOPED_GIT_CHECKPOINT_MANIFEST_20260709T091648-0500.json` as the audited include/exclude manifest instead of a hand-typed path list.

Decision boundary: do not automatically stage, commit, or push. The manifest is ready for one guarded checkpoint dry-run or execute path only after explicit checkpoint intent. Runtime/deploy/EC2 remains blocked until that checkpoint is clean and revalidated.

## Explicit Checkpoint Scope Support Is Ready, Commit Still Requires Intent - 2026-07-09T08:30:07-05:00

Decision: the guarded checkpoint helper may now handle explicit non-Plan include roots and preserved local exclude roots. This removes the prior workflow-support blocker for `.github`, `PromptProfiles`, `Workflows`, `config`, and `PROJECT_ROOT_MANIFEST.json`.

Decision boundary: do not automatically stage, commit, or push. The next checkpoint step requires explicit checkpoint intent, then a guarded execute path using the validated include/exclude roots. Runtime/deploy/EC2 remains blocked until the checkpoint is clean and revalidated.

## Dirty Git Review Groups Resolved, Guarded Checkpoint Needs Non-Plan Support - 2026-07-09T08:16:28-05:00

Decision: do not run a guarded checkpoint yet. Review/defer groups are resolved as follows: include project Plan ledger work, include runtime-orchestration roots only after checkpoint workflow support exists, preserve runtime artifacts/reference-mask assets/Jira state locally without staging them, and do not stage archive/temp output.

Decision boundary: the next implementation step is checkpoint workflow support for explicit include/exclude roots, followed by one review-resolution rerun before any checkpoint dry-run. Do not rebuild deploy bundles, publish to S3, start EC2, or run target-runtime static proof until a clean checkpoint exists.

## Dirty Git Scope Plan Requires Review Groups Before Checkpoint - 2026-07-09T08:06:33-05:00

Decision: do not run a guarded checkpoint yet. The scope plan identifies 1266 include candidates, but it also identifies 37 review-before-checkpoint paths and 2 defer/exclude candidates. Those groups must be handled first so a clean checkpoint does not accidentally absorb runtime artifacts, reference/mask assets, Jira control-plane state, archives, or temporary CI output.

Decision boundary: after the review/defer groups are explicitly included or excluded, run the guarded Git checkpoint dry-run before any commit. Do not rebuild deploy bundles, publish to S3, start EC2, or run target-runtime static proof until a clean checkpoint exists.

## Dirty Git Needs Intentional Checkpoint Scope, Not Automatic Commit - 2026-07-09T07:55:16-05:00

Decision: the dirty worktree is broad enough that the next step is checkpoint scope review, not automatic staging or commit. The inventory shows 1299 entries and 0 blocked changed paths, with most changes under `Plan`, but it is still a dirty tree and must not be used for EC2/deploy execution.

Decision boundary: do not rebuild deploy bundles, publish to S3, start EC2, or run target-runtime static proof until the checkpoint path is selected, the guarded checkpoint gate passes cleanly, and deploy bundles are rebuilt/revalidated from that clean checkpoint.

## Selected Inpaint Project Readiness Is Current, Do Not Re-Block On Missing Readiness - 2026-07-09T07:43:13-05:00

Decision: selected-lane project-readiness evidence now exists for `sdxl_realvisxl_inpaint_detail_lane` and reports `pass_local_ready_runtime_blocked`. The runtime-unblock handoff now fail-closes on `handoff_git_checkpoint_blocked`, not missing project readiness. Do not keep repeating project-readiness or local recheck ledger generation unless source evidence changes.

Decision boundary: next local-safe progress is dirty Git checkpoint inventory/intentional checkpoint path and clean deploy-bundle rebuild/revalidation planning. No live upload, EC2, generation, runtime marker, Jira lane switch, mask promotion, hard-gate rerun, or Wave71+ activation is authorized.

## Selected Inpaint Local Recheck Ledger Is Accounted, Do Not Loop It - 2026-07-09T07:27:42-05:00

Decision: the six handoff-approved local rechecks have been run and consolidated. Four pass locally; Git remains expected-blocked by dirty worktree; runtime-unblock handoff remains expected-blocked by missing selected-lane project-readiness evidence.

Decision boundary: do not keep regenerating this ledger unless one of the six source recheck artifacts changes. The next local-safe implementation move is selected-lane project-readiness evidence for `sdxl_realvisxl_inpaint_detail_lane`, not another recheck ledger, not Jira, and not live EC2.

## Selected Inpaint Pre-EC2 Handoff Is Accounted, Do Not Repackage It Repeatedly - 2026-07-09T07:14:58-05:00

Decision: the selected inpaint target-runtime lane now has a single local pre-EC2 handoff bundle tying together the latest target-runtime plan, selected package readiness, launch gate, and package/deploy matrix. Do not keep regenerating this bundle unless one of those source artifacts changes or the user explicitly selects a live target-runtime window.

Decision boundary: the bundle lists six local rechecks that may be rerun when needed, but all live upload, S3 publish with Execute, marker write, EC2 static proof, workflow smoke, generation, and final certification actions remain blocked until the explicit live gates pass.

## Final Review Blocker Sweep Is Accounted, Do Not Repeat It - 2026-07-09T07:01:52-05:00

Decision: treat the W66 final-review evidence accounting sweep as complete unless new final-review evidence is added or changed. The coverage matrix proves 9 final-review work orders are accounted for as 2 closure packets and 7 blocker packets, with missing_review_evidence_count=0. Continue to the next concrete non-mask orchestration/runtime task instead of rechecking the same lane blocker loop.

Evidence: Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_ACTIVE_RUNTIME_QUEUE_FINAL_REVIEW_EVIDENCE_COVERAGE_20260709T070139-0500.json

## Normal Lane Final Review Must Stay Blocked - 2026-07-09T06:55:16-05:00

Decision: do not close the `sdxl_realvisxl_controlnet_normal_lane` final-review work order from current local evidence. Local model proof, V3 generation smoke, preferred V3 visual QA, and V3 three-sample robustness are useful iteration/readiness evidence, but the lane promotion rule requires target-runtime object_info/path/hash/input proof, bounded target-runtime generation, pullback, technical QA, strict whole-image visual QA, and final certification review before promotion.

Evidence: Plan/Instructions/QA/Evidence/Done_Certifications/W66_NORMAL_LANE_FINAL_REVIEW_BLOCKER_PACKET_20260709T065242-0500.json

## OpenPose Lane Final Review Must Stay Blocked - 2026-07-09T06:46:44-05:00

Decision: do not close the `sdxl_realvisxl_controlnet_openpose_lane` final-review work order from current local evidence. Local model proof, V4 table-hands generation smoke, V4 visual QA, and V5 multisample table-hands robustness are useful iteration/readiness evidence, but the lane promotion rule requires target-runtime object_info/path/hash/input proof, bounded target-runtime generation, pullback, technical QA, strict visual QA, strict final hand-anatomy QA, and final certification review before promotion.

Evidence: Plan/Instructions/QA/Evidence/Done_Certifications/W66_OPENPOSE_LANE_FINAL_REVIEW_BLOCKER_PACKET_20260709T064431-0500.json

## Lineart Lane Final Review Must Stay Blocked - 2026-07-09T06:37:15-05:00

Decision: do not close the `sdxl_realvisxl_controlnet_lineart_lane` final-review work order from current local evidence. Local model/input proof, v4 plain-backdrop generation smoke, preferred v4 visual QA, and three-sample local robustness are useful iteration/readiness evidence, but the lane promotion rule requires target-runtime object_info/path/hash/input proof, bounded target-runtime generation, pullback, technical QA, strict whole-image visual QA, and final certification review before promotion.

Evidence: Plan/Instructions/QA/Evidence/Done_Certifications/W66_LINEART_LANE_FINAL_REVIEW_BLOCKER_PACKET_20260709T063504-0500.json

## Depth Lane Final Review Must Stay Blocked - 2026-07-09T06:26:17-05:00

Decision: do not close the `sdxl_realvisxl_controlnet_depth_lane` final-review work order from current local evidence. Local model/input proof, v2 generation smoke, preferred v2 visual QA, and three-sample local robustness are useful iteration/readiness evidence, but the lane promotion rule requires target-runtime object_info/path/hash/input proof, bounded target-runtime generation, pullback, technical QA, strict whole-image visual QA, and final certification review before promotion.

Evidence: Plan/Instructions/QA/Evidence/Done_Certifications/W66_DEPTH_LANE_FINAL_REVIEW_BLOCKER_PACKET_20260709T062408-0500.json

## RealESRGAN Lane Final Review Must Stay Blocked - 2026-07-09T06:17:56-05:00

Decision: do not close the `sdxl_realesrgan_upscale_polish_lane` final-review work order from current local evidence. Local model provisioning, one local upscale/polish run, strict visual QA, and p06 pass-planner binding are useful iteration/readiness evidence, but the lane promotion rule requires target-runtime object_info/path/hash proof, bounded target-runtime generation, pullback, technical QA, strict whole-image visual QA, and final certification review before promotion.

Evidence: Plan/Instructions/QA/Evidence/Done_Certifications/W66_REALESRGAN_LANE_FINAL_REVIEW_BLOCKER_PACKET_20260709T061548-0500.json

## Inpaint Lane Final Review Must Stay Blocked - 2026-07-09T06:03:56-05:00

Decision: do not close the `sdxl_realvisxl_inpaint_detail_lane` final-review work order from current local evidence. Local no-mouth v4, local robustness, local object-info, mask preview, and contact-refine context are useful iteration/readiness evidence, but the lane promotion rule requires target-runtime object_info/path/hash/input proof, bounded target-runtime output, pullback, technical QA, and strict whole-image visual QA before final review can close.

Evidence: Plan/Instructions/QA/Evidence/Done_Certifications/W66_INPAINT_LANE_FINAL_REVIEW_BLOCKER_PACKET_20260709T060050-0500.json

## Base Lane Final Review Must Stay Blocked - 2026-07-09T05:55:12-05:00

Decision: do not close the `sdxl_realvisxl_base_lane` final-review work order from current evidence. W63 target-runtime smoke proves generic base runtime viability, but W63 visual QA explicitly excludes final certification, W69 single-hand local QA blocks final decision/promotion, W69 two-character local QA blocks certification, and the runtime queue rule says not to promote final RealVisXL certification from those local samples alone.

Evidence: Plan/Instructions/QA/Evidence/Done_Certifications/W66_BASE_LANE_FINAL_REVIEW_BLOCKER_PACKET_20260709T055223-0500.json

## Canny Lane Final Review Is Locally Closed - 2026-07-09T05:45:43-05:00

Decision: the Canny final-review work order can be closed locally as `done_with_non_blocking_notes` because W68 target-runtime proof, pullback hash verification, technical QA, visual QA, W69 local multiseed robustness, and W72 local micro-control follow-up are present and internally consistent. This is lane-scoped final-review closure, not full-project certification, mask proof or promotion, Jira bookkeeping, live upload, EC2 proof, new generation, or Wave71+ activation.

Evidence: Plan/Instructions/QA/Evidence/Done_Certifications/W66_CANNY_LANE_FINAL_REVIEW_PACKET_20260709T054130-0500.json

## Closure Rollup Now Has Two Closed Work Orders - 2026-07-09T05:45:43-05:00

Decision: the active final-certification closure rollup should be treated as 2 closed / 16 open work orders. Closed work orders are the low-risk local review packet and the Canny final-certification-review packet. Target-runtime execution remains explicitly gated and blocked by dirty Git/deploy-bundle state.

Evidence: Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_CLOSURE_ROLLUP_20260709T054531-0500.json

## Active Queue Package Deploy Matrix Is Local Ready But EC2 Blocked - 2026-07-09T05:34:15-05:00

Decision: all nine active runtime queue lanes can be treated as locally package/deploy ready for orchestration purposes, but none may launch target-runtime from the current deploy bundles. Every bundle records dirty source, so any explicitly selected target-runtime lane must rebuild or revalidate its deploy bundle from a clean Git checkpoint before S3 publish or EC2 static proof. This is local package/deploy matrix evidence, not live upload, EC2 proof, new generation, mask proof or promotion, Jira bookkeeping, or Wave71+ activation.

Evidence: Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_ACTIVE_RUNTIME_QUEUE_PACKAGE_DEPLOY_MATRIX_20260709T053152-0500.json

## Selected Inpaint Launch Gate Keeps Target Runtime Fail-Closed - 2026-07-09T05:27:05-05:00

Decision: because the selected inpaint package is locally ready, future target-runtime work should start from a single launch-gate artifact rather than re-deriving package state. The launch gate may report local_package_ready=true, but target_runtime_launch_allowed must remain false until explicit user selection, clean Git checkpoint, and deploy bundle rebuild/revalidation from a clean checkpoint are proven. This is local launch-gate orchestration, not live upload, EC2 proof, new generation, mask proof or promotion, Jira bookkeeping, or Wave71+ activation.

Evidence: Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_SELECTED_TARGET_RUNTIME_LAUNCH_GATE_20260709T052434-0500.json

## Selected Inpaint Package Readiness Uses Refreshed MaskToImage Object Info - 2026-07-09T05:17:05-05:00

Decision: the stale selected-lane local object-info blocker is resolved by refreshed local proof that includes `MaskToImage` and all other required inpaint/detail runtime nodes. The package readiness packet may now pass local package readiness, but target-runtime execution remains blocked by explicit user selection, dirty Git checkpoint, and deploy bundle rebuild/revalidation from a clean checkpoint. This is local package-readiness and QA harness coverage, not live upload, EC2 proof, new generation, mask proof or promotion, Jira bookkeeping, or Wave71+ activation.

Evidence: Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_SELECTED_TARGET_RUNTIME_LANE_PACKAGE_READINESS_20260709T051227-0500.json

## Selected Inpaint Package Readiness Requires Fresh Object Info - 2026-07-09T05:06:10-05:00

Decision: the selected inpaint target-runtime package cannot be treated as locally package-ready until object-info evidence proves the current runtime-required `MaskToImage` node. Static/package evidence shows the workflow includes `MaskToImage`, but the currently referenced local object-info proof predates or omits that node. Keep EC2 stopped and refresh local object-info evidence before rerunning package readiness. This is local package-readiness and QA harness coverage, not live upload, EC2 proof, new generation, mask proof or promotion, Jira bookkeeping, or Wave71+ activation.

Evidence: Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_SELECTED_TARGET_RUNTIME_LANE_PACKAGE_READINESS_20260709T050404-0500.json

## Target Runtime Execution Plan Must Stay Explicit-Gated - 2026-07-09T04:57:13-05:00

Decision: the next target-runtime execution plan may select `sdxl_realvisxl_inpaint_detail_lane` as the first runtime-queue-order lane with target-runtime proof evidence missing, but it must remain blocked until explicit user lane selection and clean Git/AWS/S3/runtime gates. The plan emits the 13-step gate sequence and preserves `execute_allowed_now=false`. This is local target-runtime planning and QA harness coverage, not live upload, EC2 proof, new generation, mask proof or promotion, Jira bookkeeping, or Wave71+ activation.

Evidence: Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_ACTIVE_RUNTIME_QUEUE_TARGET_RUNTIME_EXECUTION_PLAN_20260709T045509-0500.json

## Final Certification Work Orders Require Closure Rollup - 2026-07-09T04:48:41-05:00

Decision: completed local final-review packets must feed a closure rollup before the next session chooses work from the final-certification manifest. The rollup closes `WO-W66-SDXL_LOW_RISK_FALLBACK_LANE-FINAL-REVIEW-PACKET`, leaves zero local-ready packets open, and preserves the remaining global Git, target-runtime, and final-review blockers. This is local closure-state and QA harness coverage, not live upload, EC2 proof, new generation, mask proof or promotion, Jira bookkeeping, or Wave71+ activation.

Evidence: Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_CLOSURE_ROLLUP_20260709T044638-0500.json

## Low-Risk Lane Review Packet Is Lane-Scoped Closure - 2026-07-09T04:37:50-05:00

Decision: the low-risk lane final-review packet may close `WO-W66-SDXL_LOW_RISK_FALLBACK_LANE-FINAL-REVIEW-PACKET` because it verifies the existing historical proof chain and visual QA locally, but it must not be treated as full project certification. Remaining target-runtime/final-review work orders, the dirty Git checkpoint gate, and explicit live-runtime gates still control broader certification. This is local lane review and QA harness coverage, not live upload, EC2 proof, new generation, mask proof or promotion, Jira bookkeeping, or Wave71+ activation.

Evidence: Plan/Instructions/QA/Evidence/Done_Certifications/W66_LOW_RISK_LANE_FINAL_REVIEW_PACKET_20260709T043340-0500.json

## Final Certification Blockers Use Work Orders - 2026-07-09T04:26:47-05:00

Decision: blocked final-certification readiness should feed an explicit work-order manifest before any live target-runtime work is selected. The current work-order manifest preserves global Git/handoff blockers, separates local final-review packet work from target-runtime proof work, and keeps EC2/generation disabled unless a target-runtime task is explicitly selected and all gates pass. This is local orchestration and QA harness coverage, not a live upload, EC2 proof, generation, mask proof or promotion, Jira bookkeeping, or Wave71+ activation.

Evidence: Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_WORK_ORDER_20260709T042635-0500.json

## Final Certification Requires Explicit Readiness Proof - 2026-07-09T04:20:26-05:00

Decision: the active runtime queue now has a local final-certification readiness aggregator separate from local support certification and target-runtime execution. Current readiness is blocked, with 8 of 9 lanes still blocked by target-runtime/final-review requirements and the Git checkpoint gate not clean for EC2 execution. This is local readiness evidence and QA harness coverage, not a live upload, EC2 proof, generation, mask proof or promotion, Jira bookkeeping, or Wave71+ activation.

Evidence: Plan/Instructions/QA/Evidence/Done_Certifications/W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_READINESS_20260709T042016-0500.json

## Runtime Handoff Requires Git Checkpoint Gate - 2026-07-09T04:11:35-05:00

Decision: runtime unblock handoffs must carry the structured Git checkpoint dry-run gate before any future EC2 execute path can be selected. The handoff may still summarize completed local runtime-smoke evidence, but git_checkpoint_gate.passes_for_ec2_execute must be true immediately before EC2 execution; the current dirty worktree keeps that gate fail-closed. This is local handoff/orchestration and harness coverage, not a commit, push, cleanup, live upload, EC2 proof, generation, mask proof or promotion, Jira bookkeeping, or Wave71+ activation.

Evidence: Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_RUNTIME_UNBLOCK_HANDOFF_WITH_GIT_GATE_20260709T040900-0500.json

## Structured Git Checkpoint Gate Boundary - 2026-07-09T04:04:28-05:00

Decision: Git checkpoint dry runs must produce structured evidence before they can be used as EC2 safety gates. The current evidence proves HEAD equals origin/main but clean_worktree=false, so EC2 execute paths remain blocked until the worktree is intentionally checkpointed clean immediately before a selected target-runtime task. This is local gate evidence and harness coverage, not a commit, push, cleanup, live upload, EC2 proof, generation, mask proof or promotion, Jira bookkeeping, or Wave71+ activation.

Evidence: Plan/Instructions/QA/Evidence/Git_Verification/W66_GITHUB_CHECKPOINT_DRY_RUN_JSON_GATE_20260709T040418-0500.json

## Matrix Quality-Run Planning Current-Evidence Boundary - 2026-07-09T03:56:24-05:00

Decision: the RealVisXL matrix quality-run validator must use current deploy-bundle and runtime-handoff gates, not stale July 6 dry-run evidence. The validated plan is a 3-sample base-lane quality-run plan tied to the current 9-lane active-queue deploy bundle and active queue support evidence; it is not permission to upload, start EC2, generate, certify final quality, promote masks, start Jira bookkeeping, or activate Wave71+.

Evidence: Plan/Instructions/QA/Evidence/Workflow_Runtime/W66_EC2_WORKFLOW_MATRIX_QUALITY_RUN_PLAN_CURRENT_9LANE_GATE_20260709T035604-0500.json

## Runtime Handoff Completed-Queue Sentinel Boundary - 2026-07-09T03:50:50-05:00

Decision: runtime unblock handoffs must distinguish an active selected lane from the completed local queue sentinel. `none_all_current_local_runtime_proofs_complete` is valid for handoff planning only when the selected lane is still in the queue, failed_check_count=0, local-only queue evidence is preserved, and the other target-runtime gates remain passing. This is local handoff/orchestration correction, not a live upload, not EC2 proof, not generation, not mask proof or promotion, not Jira bookkeeping, and not Wave71+ activation.

Evidence: Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_RUNTIME_UNBLOCK_HANDOFF_QUEUE_COMPLETE_AWARE_20260709T035040-0500.json

## Runtime Handoff Requires Active Queue Support Certification - 2026-07-09T03:46:09-05:00

Decision: future runtime unblock handoffs must include and enforce the active runtime queue local support certification before target-runtime proof can be selected. If the certification is missing or failed, New-RuntimeUnblockHandoff.ps1 now records handoff_active_queue_local_support_blocked and directs rerun_active_runtime_queue_local_support_certification. This is local handoff hardening, not a live upload, not EC2 proof, not generation, not mask proof or promotion, not Jira bookkeeping, and not Wave71+ activation.

Evidence: Plan/Instructions/QA/Evidence/Runtime_Readiness/W66_RUNTIME_UNBLOCK_HANDOFF_WITH_QUEUE_SUPPORT_CERT_20260709T034533-0500.json

## Active Runtime Queue Local Support Certification Boundary - 2026-07-09T03:40:24-05:00

Decision: the current 9-lane active runtime queue now has a local support certification distinct from final target-runtime/final-image certification. Historical failed or partial lane evidence remains visible as notes, but it does not override later passing support evidence. Final certification stays blocked until target-runtime proof and final review are explicitly selected and proven. This is local queue-support certification, not a live upload, not EC2 proof, not generation, not mask proof or promotion, not Jira bookkeeping, and not Wave71+ activation.

Evidence: Plan/Instructions/QA/Evidence/Done_Certifications/W66_ACTIVE_RUNTIME_QUEUE_LOCAL_SUPPORT_CERTIFICATION_20260709T033754-0500.json

## QA Helper Preflight Validator Coverage Boundary - 2026-07-09T03:30:38-05:00

Decision: the reusable GitHub Actions preflight package workflow validator is now part of the broader QA helper static harness. Future changes to workflow packaging, router gate behavior, authored lane readiness, or runtime-queue sentinel handling should keep Test-QAHelperStatic.ps1 green before relying on the local package/deploy-bundle path. This is local QA harness validation, not a remote GitHub Actions run, not live S3 upload, not EC2 proof, not generation, not mask proof or promotion, not Jira bookkeeping, and not Wave71+ activation.

Evidence: Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W66_QA_HELPER_GITHUB_ACTIONS_PREFLIGHT_PACKAGE_WORKFLOW_20260709T032720-0500.json

## Reusable Preflight Validator Boundary - 2026-07-09T03:14:13-05:00

Decision: GitHub Actions preflight package workflow drift must be validated with Plan/Instructions/QA/Scripts/Test-GitHubActionsPreflightPackageWorkflow.ps1 before live upload or EC2 execution paths rely on it. Full local package/bundle validation should use the script's short runtime_artifacts/pf_* root to avoid Windows path-depth failures while preserving exact CI run IDs. This is local workflow/package validation, not a remote GitHub Actions run, not live S3 upload, not EC2 proof, not generation, not mask proof or promotion, not Jira bookkeeping, and not Wave71+ activation.

Evidence: Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_GITHUB_ACTIONS_PREFLIGHT_PACKAGE_WORKFLOW_VALIDATOR_20260709T031413-0500.json

## GitHub Actions Full-Matrix Packaging Boundary - 2026-07-09T03:05:09-05:00

Decision: the preflight package workflow matrix must match the active 9-lane runtime queue, not only the original two lanes. Local validation synced Workflows/base_generation from the active queue exports and proved all 9 exact CI run IDs can build run packages and deploy bundles. This is workflow/package orchestration readiness, not a remote GitHub Actions run, not live S3 upload, not EC2 proof, not generation, not mask proof or promotion, not Jira bookkeeping, and not Wave71+ activation.

Evidence: Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_GITHUB_ACTIONS_PREFLIGHT_9LANE_MATRIX_PACKAGING_20260709T030509-0500.json

## GitHub Actions Preflight Queue-Gate Boundary - 2026-07-09T02:58:45-05:00

Decision: the preflight package workflow must prove the current 9-lane authored-lane evidence coverage and runtime-lane queue state before deploy-bundle packaging. The runtime queue gate must consume the exact authored-coverage JSON produced in the same workflow. This is local/CI preflight hardening, not a remote workflow run, not live S3 upload, not EC2 proof, not generation, not mask proof or promotion, not Jira bookkeeping, and not Wave71+ activation.

Evidence: Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_GITHUB_ACTIONS_PREFLIGHT_9LANE_QUEUE_GATES_20260709T025759-0500.json

## Runtime Marker Helper Validation Boundary - 2026-07-09T02:54:00-05:00

Decision: runtime-window marker planning is now part of the operations helper validation suite. This is local validation coverage only; it is not a live EC2 window, not an active marker write, and not permission to upload, start EC2, or generate.

Evidence: Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_OPERATIONS_HELPER_RUNTIME_WINDOW_MARKER_PLAN_20260709T025400-0500.json
## Runtime Window Marker Boundary - 2026-07-09T02:49:03-05:00

Decision: the project now has a local helper and marker template for future EC2 live-window cost-control state. This is not a live-window start and not permission to write ACTIVE_EC2_RUNTIME_WINDOW.json. The active marker remains absent by design until a real approved runtime window starts.

Evidence: Plan/Instructions/QA/Evidence/Operations_Static_Validation/W66_9LANE_RUNTIME_WINDOW_MARKER_PLAN_QA_20260709T024903-0500.json
## 9-Lane Runtime Handoff Boundary - 2026-07-09T02:40:27-05:00

Decision: the current 9-lane bundle is locally ready for a future explicit live-window handoff, but it is not permission to upload, start EC2, or generate. The emergency-stop schedule was refreshed only as a dry run. Continue non-mask local orchestration by default while manual gold masks are still being prepared.

Evidence: $handoff

## 9-Lane Deploy Bundle Runtime Plan Boundary - 2026-07-09T02:35:00-05:00

Decision: the current active queue's deploy-bundle/runtime-plan evidence must use the 9-lane bundle `rvxl_mx_9lane_20260709T0235`, not the earlier 8-lane bundle. This is local-only orchestration readiness and does not authorize live S3 upload, EC2 execution, final certification, body-mask proof, gold-mask proof, Jira execution-ledger work, or Wave71+ activation.



## RealESRGAN Upscale Polish Active Queue Boundary - 2026-07-09T02:25:00-05:00

Decision: `sdxl_realesrgan_upscale_polish_lane` is now part of the active local queue as lane 9 and validates through local runtime plus visual QA evidence. This closes the prior nonqueued authored-lane gap without claiming target-runtime EC2 proof, final upscale/polish certification, body-mask proof, gold-mask proof, live upload, Jira execution-ledger work, or Wave71+ activation.

## Current Active Lanes RealVisXL Readiness Boundary - 2026-07-09T02:13:10-05:00

Decision: current active-lane local readiness evidence is aligned after validator repair. The eight queued base-generation lanes validate locally; the nonqueued RealESRGAN upscale/polish lane is outside this queue scope; the RealVisXL lane has `pass_runtime_smoke_qa_complete` and should not be rerun only to re-prove the same smoke/pullback/QA chain. This is not final project completion, not final quality certification, not body-mask proof, not live upload, not EC2 execution, and not Wave71+ activation.

## Automation Thread Transfer Boundary - 2026-07-09T02:04:29-05:00

Decision: the seven active Comfy_UI_Main cron jobs should remain in place; no duplicate automations are needed. Their automation TOMLs no longer reference the disconnected `019f35e8-7e15-7c72-8ffb-66f6f9b246a0` session and already target the current main ComfyUI thread `019f422f-88b1-7382-872b-21de2089e983`. The paused legacy Wave42 heartbeat remains unrelated.

## Local S3 Readiness And Emergency Stop Dry-Run Boundary - 2026-07-09T02:00:48-05:00

Decision: planned-value S3 runtime transfer readiness and EC2 emergency-stop scheduling are ready only as local dry-run/safety plans. The emergency-stop helper must not be run with `-Execute` unless the user explicitly selects a bounded EC2 runtime window and AWS auth plus Git cleanliness checks pass. This is not live S3 upload, not AWS contact, not EC2 proof, not generation, not mask proof or promotion, not Jira bookkeeping, and not Wave71+ activation.

## Persistent Bundle Quality-Run Plan Validator Boundary - 2026-07-09T01:54:30-05:00

Decision: the matrix quality-run validator now supports both nested validation evidence and root-level persistent dry-run publish evidence, emits no-BOM JSON, and has produced a fresh local-only plan using the persistent bundle URI/hash. This is not a live upload, not AWS contact, not EC2 proof, not generation, not final certification, not body-mask proof, and not Wave71+ activation.

## Persistent Matrix Deploy Bundle Dry-Run Boundary - 2026-07-09T01:49:30-05:00

Decision: the persistent RealVisXL multi-sample matrix deploy bundle is built locally and has a dry-run S3 publish record with exact URI/hash values. This is not a live upload, not AWS contact, not EC2 proof, not generation, not final certification, not body-mask proof, and not Wave71+ activation. A shorter bundle name is the successful path; the longer name hit a local Windows nested path issue.

## S3 Runtime Config Plan Boundary - 2026-07-09T01:45:15-05:00

Decision: local S3 runtime config planning and rendered policy preview validation are ready. This is not a live AWS apply, not a live S3 upload, not emergency-stop scheduling, not EC2 proof, not generation, not final certification, not body-mask proof, and not Wave71+ activation.

## Local Deploy Bundle, Quality Plan, And S3 Readiness Boundary - 2026-07-09T01:42:51-05:00

Decision: the completed repaired package smoke matrix is now discoverable in active base-generation lane manifests, and the local-only deploy bundle, bundle-content QA, matrix quality-run plan, and S3 runtime-transfer readiness checks passed against current state. This is orchestration readiness only: no AWS contact, no EC2 start, no live upload, no generation, no target-runtime proof, no final quality certification, no body-mask proof, and no Wave71+ activation.

## Repaired Package Local Smoke Matrix Completion Boundary - 2026-07-09T01:33:48-05:00

Decision: all 8 repaired base-generation package lanes now have bounded local ComfyUI package smoke execution evidence and visual QA. The completed matrix should be reused instead of rerun by default. This is still not final image quality certification, exact character/reference identity proof, full-body proof, body-mask proof, target-runtime EC2 proof, or Wave71+ activation.

## Inpaint Detail Local Package Smoke Boundary - 2026-07-09T01:31:30-05:00

Decision: `sdxl_realvisxl_inpaint_detail_lane` now has repaired-package local `/prompt` execution proof, generated-output viability QA, and localized inpaint mask-preview capture. This completes bounded local package smoke execution for all 8 repaired base-generation matrix lanes. The QA notes remain strict: local smoke viability is not final quality certification, not exact character identity proof, not full-body proof, not body-mask proof, not target-runtime EC2 proof, and not Wave71+ activation.

## OpenPose Local Package Smoke Boundary - 2026-07-09T01:28:23-05:00

Decision: `sdxl_realvisxl_controlnet_openpose_lane` now has repaired-package local `/prompt` execution proof, generated-output viability QA, and diagnostic OpenPose-map capture. The QA notes are intentionally strict: the generated image is coherent but male-presenting and close-up, so intended character identity, full-body composition, final quality, body-mask proof, target-runtime EC2 proof, and Wave71+ activation are not proven.

## Normal Local Package Smoke Boundary - 2026-07-09T01:24:32-05:00

Decision: `sdxl_realvisxl_controlnet_normal_lane` now has repaired-package local `/prompt` execution proof, generated-output viability QA, and diagnostic normal-map capture. The QA notes are intentionally strict: the generated image is a coherent close-up portrait, but full-body composition, exact identity/reference matching, final quality, body-mask proof, target-runtime EC2 proof, and Wave71+ activation are not proven.

## Jira Control-Plane Board Boundary - 2026-07-09T00:54:24-05:00

Decision: CU Jira is a control-plane board for the ComfyUI project, not the authoritative 24/7 autonomous execution ledger. Preserve the imported Feature/Initiative and 18 Epics; delete imported Story, Task, and Sub-task rows from the Wave8 mechanical pack. The local authoritative execution detail stays in `Plan\Items`, `Plan\Tracker`, QA evidence, tracker evidence, and `runtime_artifacts`.

Importer session `019f452c-76e8-7312-9fe0-2ade82f19651` must not continue the full 228,339-row Jira import. Scheduled agents targeting ComfyUI session `019f422f-88b1-7382-872b-21de2089e983` must read `C:\Comfy_UI_Main\Plan\Instructions\JIRA_CONTROL_PLANE_AND_AI_EXECUTION_LEDGER_POLICY.md` before Jira work and must not bulk-create Jira Stories, Tasks, or Sub-tasks from local Items/Tracker rows.

## Lineart Local Package Smoke Boundary - 2026-07-09T01:18:50-05:00

Decision: `sdxl_realvisxl_controlnet_lineart_lane` now has repaired-package local `/prompt` execution proof, generated-output viability QA, and diagnostic lineart-map capture. The QA notes are intentionally strict: exact identity/reference matching is not proven, so this evidence is not final quality certification, not character identity proof, not target-runtime EC2 proof, not mask proof, and not Wave71+ activation.

## Depth Local Package Smoke Boundary - 2026-07-09T01:14:30-05:00

Decision: `sdxl_realvisxl_controlnet_depth_lane` now has repaired-package local `/prompt` execution proof, generated-output viability QA, and diagnostic depth-map capture. The QA notes are intentionally strict: the generated image is underexposed and exact identity/reference matching is not proven, so this evidence is not final quality certification, not character identity proof, not target-runtime EC2 proof, not mask proof, and not Wave71+ activation.

## Canny Local Package Smoke Boundary - 2026-07-09T01:10:30-05:00

Decision: `sdxl_realvisxl_controlnet_canny_lane` now has repaired-package local `/prompt` execution proof, generated-output viability QA, and diagnostic control-map capture. The QA notes are intentionally strict: generated subject identity/reference matching failed or was not proven, so this evidence is not final quality certification, not character identity proof, not target-runtime EC2 proof, not mask proof, and not Wave71+ activation.

## RealVisXL Base Local Package Smoke Boundary - 2026-07-09T01:06:40-05:00

Decision: `sdxl_realvisxl_base_lane` now has repaired-package local `/prompt` execution proof and generated-output viability QA. This proves the local RealVisXL base package execution path only. It does not certify ControlNet, inpaint, final quality, identity/reference match, body/hand anatomy, masks, target-runtime EC2, or Wave71+ activation.

## Low-Risk Local Package Smoke Boundary - 2026-07-09T01:03:20-05:00

Decision: `sdxl_low_risk_fallback_lane` now has repaired-package local `/prompt` execution proof and generated-output viability QA. This proves the local package execution path and SDXL low-risk fallback lane only. It does not certify RealVisXL, ControlNet, inpaint, final quality, identity/reference match, body/hand anatomy, masks, target-runtime EC2, or Wave71+ activation.

## Base Generation Repaired Package Readiness Boundary - 2026-07-09T00:56:03-05:00

Decision: the active Canny v3 control input is `controlnet_canny_cleaned_eye_safe_v3_rightedge_band_masked.png` with SHA256 `4b40cdd7386d9287a37d64efafdeb7078a8a9d4160e23e00b5ddc87106a1f870`; runtime requirements and generated packages must not carry the older v1 SHA `d2f09161928d6efa1c724aafd6798ab597f8cfa0e12dcb4db61203c6b4e74bd0` for that v3 filename. Repaired packages under `runtime_artifacts/run_package_matrices/base_generation_smoke_prompts_20260709T005518-0500` have model/input asset readiness and object-info readiness, but this is still not prompt execution, model-load proof, generated-output QA, EC2 proof, final certification, mask proof, or Wave71+ activation.

## Base Generation Object Info Boundary - 2026-07-09T00:46:13-05:00

Decision: local `/object_info` validation proves node-class visibility for the packaged prompts only. It does not prove model file availability, input image availability, prompt submission, model loading, image generation, visual QA, final certification, mask proof, EC2 readiness, or permission to run generation without the normal runtime gates.

## Base Generation Run Package Matrix Boundary - 2026-07-09T00:42:50-05:00

Decision: `runtime_artifacts/run_package_matrices/base_generation_smoke_prompts_20260709T004250-0500` is a dry-run package matrix for later readiness/execution gates. It proves package assembly and hash tracking only; it is not prompt submission, model-load proof, runtime proof, visual QA, final certification, mask proof, or permission to start EC2/AWS.

## Base Generation Prompt Materialization Boundary - 2026-07-09T00:39:24-05:00

Decision: materialized `prompt_request.json` payloads under `runtime_artifacts/base_generation_smoke_prompt_materialization/20260709T003924-0500` are dry-run artifacts for packaging/readiness validation. They must not be treated as runtime proof, model-load proof, visual QA, final certification, or permission to execute generation without the normal runtime gates.

## Base Generation Smoke Contract Boundary - 2026-07-09T00:36:29-05:00

Decision: active base-generation smoke requests and patch-point files are valid local launch contracts only. `execution_allowed: false` remains required until runtime gates are intentionally satisfied; this evidence does not start ComfyUI, contact EC2/AWS, run generation, promote masks, or certify final image quality.

## Base Generation Lane Sync Boundary - 2026-07-09T00:32:43-05:00

Decision: runtime-facing `Workflows/base_generation/*/runtime_requirements.json` files for active lanes must stay hash-aligned with their Plan template counterparts unless a deliberate runtime-lane override is recorded with evidence. The inactive `sdxl_realesrgan_upscale_polish_lane` folder remains available but is not activated by the active-lane sync repair.

No EC2, AWS, generation, ComfyUI contact, hard-gate rerun, mask truth, candidate-mask promotion, or Wave71+ activation occurred.

## Wave64 Registry ID Boundary - 2026-07-09T00:28:35-05:00

Decision: registry uniqueness checks enforce actual row identifiers, not foreign-key fields such as source/target node IDs, repeated Comfy registry package IDs, or taxonomy value lists. This is a local structural validation only and does not claim runtime freshness.


## Jira Imported Item Proof-Reuse Decision - 2026-07-09T01:23:58-05:00

Decision: imported Jira rows are control-plane visibility only and cannot recreate, reopen, or rerun already-proven ComfyUI work. Local review found `7,772` mapped Jira import rows (`1` Initiative, `18` Epics, `7,751` Stories, `1` Task, `1` Sub-task), with cleanup already confirming `3,086` deleted imported rows and bulk cleanup still running. `jira_full_import_supervisor.py` aborts, `jira_api_importer.py import-issues` is blocked by default, and cron jobs already route Jira actions through `Plan/Instructions/JIRA_CONTROL_PLANE_AND_AI_EXECUTION_LEDGER_POLICY.md`, which now explicitly requires proof reuse and forbids Jira backlog/status rows from triggering duplicate Canny/AWS/local smoke, Wave64/Wave65 hygiene, route-alignment, or local Items/Tracker mirror work.

## AWS Auth And Runtime Proof Reuse Decision - 2026-07-09T01:18:29-05:00

Decision: live AWS auth is current for account `029530099913` in `us-east-1`, so stale expired-auth blocker text is superseded for authentication status. This does not authorize default EC2 reruns. `sdxl_realvisxl_controlnet_canny_lane` baseline Canny proof is complete and reusable: W68 EC2 Canny v4 target-runtime smoke has static proof, bounded generation, S3 sync, pullback/hash verification, technical QA, and visual QA, and the 20260709 local Canny package smoke passed with generated image plus diagnostic control map. Do not rerun baseline Canny local/AWS proof unless workflow/request/input/model/artifact integrity changed or the user intentionally selects final certification/changed-variant proof. Use `Plan/Instructions/QA/RUNTIME_PROOF_REUSE_AND_NO_RERUN_PROTOCOL.md`.

## Return To Concrete ComfyUI Runtime Work Decision - 2026-07-09T00:27:04-05:00

Decision: the Wave64 hygiene/bookkeeping run stops after `TRK-W64-053` unless a specific control row directly unblocks implementation. The main session should not default to `TRK-W64-054`, Wave65 coverage/index refresh, generic manifest cleanup, hydration proof churn, or route-alignment loops. The next active work is one bounded local-first ComfyUI workflow/runtime/orchestration task using `Workflows/base_generation/ACTIVE_LANES.json`, `Plan/07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json`, and active `Workflows/base_generation` lane folders. Produce one concrete artifact or exact blocker; do not consume candidate masks as truth, promote masks, rerun Wave70 hard gates, activate Wave71+, or start EC2/AWS unless explicitly selected and fully gated.

## Wave64 Example Fixture Expectations Boundary - 2026-07-09T00:23:49-05:00

Decision: `Plan/09_EXAMPLES/EXAMPLE_FIXTURE_EXPECTATIONS_MANIFEST.json` is the explicit local QA expectation binding for example/fixture rows. This boundary validates example contracts only; it does not promote masks, consume candidate masks as truth, claim runtime readiness, or activate Wave71+.


## Wave64 Script Parser Boundary Decision - 2026-07-09T00:16:25-05:00

Decision: script-validation rows may use parser-only local smoke checks without executing helper bodies. Live helper execution remains gated by each helper's own runtime, AWS, EC2, ComfyUI, secret, and cost-control preconditions.


## Wave64 Schema Descriptor Decision - 2026-07-09T00:13:22-05:00

Decision: `Plan/08_SCHEMAS` contains both JSON Schema documents and legacy `schema_name` plus `required_fields` descriptors. Schema validation must accept both established local forms while still failing closed on JSON parse errors, CSV parse/header errors, invalid JSON Schemas, duplicate schema filenames, or malformed legacy descriptors.


## Wave64 Coverage Stop Decision - 2026-07-09T00:08:16-05:00

Decision: after repairing the single missing Ultra source key and passing the post-repair verifier, stop coverage refreshes. Continue to concrete non-coverage rows unless a Plan file is added/renamed or the user explicitly requests another coverage pass.


## Wave64 Blocker Precedence Decision - 2026-07-09T00:01:53-05:00

Decision: use the latest active blocker register in `BLOCKERS.md` as the current source of truth for blocker scope. Historical blocker and known-issue entries remain useful context, but they cannot reopen or override newer structured evidence without a new explicit validation record.


## Wave64 No-Loop Boundary Decision - 2026-07-08T23:59:42-05:00

Decision: do not repeat the session-transfer, hydration, route-alignment, coverage-refresh, EC2-auth, hard-gate, or mask-promotion checks unless an input changes or the user explicitly asks. Continue only to concrete tracker rows that advance implementation, orchestration, runtime readiness, evidence governance, or exact blocker recording.


## Wave64 Session Transfer Boundary Decision - 2026-07-08T23:57:24-05:00

Decision: the live active session state is governed by the top hydration blocks pointing to `019f422f-88b1-7382-872b-21de2089e983`, `TRK-W64-047` / `ITEM-W64-047`, and next `TRK-W64-048` / `ITEM-W64-048`. Lower mentions of dead thread `019f35e8-7e15-7c72-8ffb-66f6f9b246a0` are historical ledger context only and must not be treated as active scheduled-work or next-action targets.


## Gold Mask Dependency Boundary Decision - 2026-07-08T22:21:23-05:00

Decision: manual gold-standard mask creation is a scoped dependency gate, not a global project freeze. Mask-dependent promotion, geometry authority, body/hand/contact validation, final mask QA requiring trusted masks, certification-ready claims, and Wave71+ activation must fail closed with `Blocked_Gold_Mask_Dependency_Missing` until exact manual masks pass intake and strict gates. Non-mask workflow, orchestration, evidence, automation, dataset organization, validation scaffolding, tracker hygiene, and asset work may continue without consuming candidate masks as truth.

## Wave70 Gold Trace Registration Decision - 2026-07-08T07:17:13-05:00

Registered the user's existing annotated references as durable calibration/evaluation evidence only. This does not promote masks or replace missing model-derived geometry authority.

# Recent Decisions

- 2026-07-07T20:37:00-05:00: Added Wave70 protected-boundary registry enforcement after user asked whether a bad mask, such as `mf70_nose` crossing into mouth, could corrupt later masks. Decision: previous generated editable masks are not authoritative protected boundaries by default. Every Wave70 mask must validate protected neighbors against canonical source-derived boundaries and a protected-overlap matrix; bad masks must fail/revise instead of becoming boundary truth for later masks. Added `Plan/Instructions/QA/WAVE70_PROTECTED_BOUNDARY_REGISTRY_PROTOCOL.md` and updated mask alignment protocol, promotion gates, taxonomy, matrix manifest template, tracker rows, and item rows with `canonical_protected_boundary_registry_pass`, `protected_overlap_matrix_pass`, `boundary_registry_manifest_present`, and `protected_boundary_noninheritance_pass`.

- 2026-07-07T20:06:00-05:00: Added Wave70 reference-image matrix enforcement after user questioned why masks were being created and judged against the same active portrait. Decision: one portrait is allowed only as `single_anchor_smoke` evidence for plumbing, source-specific overlay review, source visibility, and low-denoise generated-output stability. Generalized, universal, or certification-ready Wave70 mask claims now require `reference_image_matrix_pass`, `high_resolution_detail_review_pass`, `cross_subject_generalization_pass`, and `source_visibility_matrix_pass`. Added `Plan/Instructions/QA/WAVE70_REFERENCE_IMAGE_MATRIX_QA_PROTOCOL.md` and `Plan/07_IMPLEMENTATION/mask_factory/ULTIMATE_MASK_REFERENCE_IMAGE_MATRIX.md`; updated promotion gates, taxonomy, tracker, and item rows. Existing single-portrait pass rows `mf70_under_eye`, `mf70_eyebrows`, `mf70_mouth_lips`, and `mf70_teeth` were reclassified as `Single_Anchor_Mask_Alignment_Pass_Matrix_Required_Target_Runtime_Pending`.

- 2026-07-07T19:25:00-05:00: Superseded the earlier Wave70 mask-alignment audit after user pointed out that the nose and original mask examples had not been strictly reviewed enough. The new strict overlay-first audit downgrades prior pass-with-notes rows where the overlay is a shortcut polygon, partial target, or protected-neighbor overlap. Decision: `mf70_nose`, `mf70_pupils_iris_sclera`, and `mf70_skin_tone_continuity` are mask-alignment failures; `mf70_forehead_skin` and `mf70_eyelashes` are no longer passes; generated-output stability remains separate evidence only.

- 2026-07-07T19:05:00-05:00: Tightened Wave70 mask QA after user review showed several generated-output-safe masks were not semantically aligned to their claimed anatomical target. Added `Plan/Instructions/QA/WAVE70_MASK_ALIGNMENT_QA_PROTOCOL.md`, retro-audited the questioned Wave70 rows, updated all 141 Wave70 tracker/item rows to require `semantic_mask_alignment_pass`, `protected_neighbor_check_pass`, and `generated_output_safe_pass`, and changed `mf70_eyebrows` from generated-output-only status to `Mask_Alignment_Pass_Generated_Output_Safe_Target_Runtime_Pending`. Decision: generated-output stability remains valid runtime evidence, but it no longer counts as mask completion. Rows with alignment fail/needs-revision/unreviewed status must be revised or re-reviewed before certification. No cron/scheduled task change was needed because no project Wave70 mask QA cron job was found.

- 2026-07-07T14:40:00-05:00: Added generated-output proof for Wave70 `mf70_face_identity_critical`. A low-denoise inpaint profile used the Wave70 mask and active Canny v3 portrait source, generated one local output plus mask preview, and passed whole-image visual QA with notes. Decision: generated-output proof is now present and the mask evidence is updated; final certification remains blocked only by target-runtime proof.

- 2026-07-07T14:25:00-05:00: Added local Wave70 Ultimate Mask Factory support for `mf70_face_identity_critical` (`TRK-W70-0002` / `ITEM-W70-0002`). A deterministic mask and preview overlay were generated from the active MOD-17 Canny v3 portrait, copied into `ComfyUI/input`, validated through the existing mask contract validator, scored at `96.25`, and routed to the inpaint detail lane mask input. Decision: local artifact/routing support passes, but the item remains incomplete until generated-output proof, strict whole-artifact QA after use, and target-runtime proof exist.

- 2026-07-07T14:15:00-05:00: Refreshed and locally certified the Wave14 Canny/inpaint Pass Planner readiness package against the active MOD-17 Canny v3 lane surface. The request now points at `canny_w69_rightedge_masked_v3_seed711570105` and the v3 active control image, the compiled plan validates with 7 passes, 21 checked evidence paths, zero errors, and zero warnings, and the new local certification gate reports `pass_local_pass_planner_readiness_final_blocked_target_runtime`. Boundary: local dry-run-first readiness only; final promotion still requires target-runtime proof.

- 2026-07-07T13:50:00-05:00: Promoted the v3 right-edge-band-masked Canny control image into the active MOD-17 local lane surface: exported workflow defaults, Plan template defaults, runtime requirements, reference-slot routing request, and ControlNet local support certification request. Static validation, reference-slot routing, and five-lane local support certification all pass. Final ControlNet lane certification remains blocked by target-runtime proof. Boundary: local support refresh only, not final certification.

- 2026-07-07T13:35:00-05:00: Created and tested a v3 right-edge-band-masked Canny control input after the prior `0.38/0.55` rerun exposed a right-edge band artifact. A first 22px v2 mask was rejected before runtime because inspection showed the Canny line remained; the v3 96px mask removed the line. The bounded local retest kept the better `0.42/0.60` Canny settings, generated a portrait plus diagnostic map, and passed strict visual QA with notes. Decision: v3 is the preferred local MOD-17 Canny control input for this candidate; final MOD-17 certification still requires target-runtime proof and broader gates.

- 2026-07-07T13:15:00-05:00: Ran one bounded local MOD-17 Canny edge-naturalness rerun from a new QA-driven profile lowering Canny strength to `0.38` and end_percent to `0.55`. The local run generated a 768x768 portrait and 1024x1024 diagnostic control map, then stopped ComfyUI with port `8188` closed. Strict visual QA found face/eyes/hair/clothing stayed coherent, but a visible right-edge vertical band/panel artifact returned. Decision: do not promote this profile; keep the prior `0.42/0.60` seam-suppression sample as the better local candidate, and clean/crop the far-right control-map edge before any further Canny strength retry.

- 2026-07-07T13:05:00-05:00: Ran one bounded local Wave25 lower-upper-arm contact reposition attempt using a broader mask and seed210705. The run generated one local image and preserved identities, contact ownership, hand visibility, and no visible mask edge, but the comparison crop shows the hand still reads as shoulder/top-upper-sleeve contact. Certification rerun passed local support and correctly blocked final certification for subtle-to-moderate shadow, shoulder/top-upper-sleeve placement, missing target-runtime proof, and missing final review. Decision: stop squeezing this same image with similar masks; move to another named local gap unless a materially different contact-generation strategy is selected.

- 2026-07-07T12:55:00-05:00: Added and ran a conservative local support certification gate for MOD-17 through MOD-21 ControlNet lanes. Canny, Depth, Lineart, OpenPose, and Normal all passed local support checks against static evidence, tracker evidence, strict visual QA, generated artifact existence, and reference-slot routing. Final lane certification remains correctly blocked for all five lanes by missing target-runtime evidence. Boundary: local support certification only, not final promotion.

- 2026-07-07T12:40:00-05:00: Implemented and validated the local reference-slot routing contract beyond face reference. The new request binds five non-face slots (`edge_reference`, `depth_reference`, `lineart_reference`, `pose_reference`, `normal_reference`) to real Canny, Depth, Lineart, OpenPose, and Normal ControlNet lanes, and the new validator checked workflow patch points, `LoadImage` control-image routing, existing evidence, and input hashes/dimensions. Result: `pass_local_reference_slot_routing_beyond_face` with 5 slots verified and zero defects. Boundary: local routing proof only, not target-runtime proof or final visual certification.

- 2026-07-07T12:50:00-05:00: Ran one bounded local contact-shadow/pressure refinement against the Wave25 hand/contact blocker. Seed `210704` slightly improved lower-finger/sleeve pressure and contact shadow while preserving identities and contact ownership, but the certification gate still blocks final certification because shadow is only `subtle_to_moderate`, placement remains shoulder/top-upper-sleeve, target-runtime proof is missing, and final certification review is missing. Boundary: useful local iteration, not final certification.

- 2026-07-07T12:35:00-05:00: Added and ran a stricter local hand/contact visual certification gate for the Wave25 two-character contact. The gate passed local support but correctly blocked final certification because contact shadow remains subtle, contact placement is shoulder/top-upper-sleeve rather than exact target upper-arm, target-runtime proof is missing, and final certification review is missing. This prevents over-certifying the current local output while preserving the real local progress.

- 2026-07-07T12:25:00-05:00: Added and ran a local Wave13 contact-mask QA helper for the Wave25 two-character hand-to-body mask. The mask passed with named participants, non-empty contact, 475 edge pixels, 2.0351% coverage, overlap with both named participant regions, and outside-participant bleed at 18.5239% under the configured 20% ceiling. Boundary: local mask QA only, not final visual certification or target-runtime proof.

- 2026-07-07T12:15:00-05:00: Ran a two-seed local robustness pair for the Wave25 mask-routed contact refine path. Seeds `210702` and `210703` used the same source, mask, prompt, model, sampler, and denoise as seed `210701`. Both generated cleanly through local ComfyUI and passed strict visual QA with notes: identities, clothing, background, body separation, woman-to-man contact ownership, and contact-zone finger anatomy stayed stable; contact shadow remains subtle and final/target-runtime certification is still separate.

- 2026-07-07T12:05:00-05:00: Routed the preferred Wave25 two-character contact output through one local low-denoise inpaint refinement using a pixel-aligned 1024x1024 contact mask. The local run generated `codex_wave25_two_character_contact_refine_seed210701_00001_.png`, SHA256 `991ede7b0df2f820d7fbd834a888c1b085958ebf30781840728f190a32e2968c`; visual QA is pass-with-notes because the whole image stayed stable and the contact crop shows slightly cleaner fingers/edge contact, but contact shadow remains subtle and this is not robustness, target-runtime proof, or final certification.

- 2026-07-07T11:50:00-05:00: Turned the Wave25 two-character preflight into local RealVisXL pixels. First sample seed `7152026251` produced two distinct bodys but failed source/target contact ownership. Made one QA-driven prompt change and reran seed `7152026252`; the rerun is the preferred local candidate with the woman on the left visibly resting an open hand on the man's shoulder/upper-arm area, distinct bodies, coherent faces/clothing, and pass-with-notes visual QA. Boundary: first local pixel evidence only; mask-routed refine, robustness, target-runtime proof, and final Wave25 certification remain separate.

- 2026-07-07T11:35:00-05:00: Superseded the Wave25 single-instance local preflight blocker with a bounded two-character hand-to-body contract chain. Wave24 layout validation now passes with 2 character instances, 2 depth-order entries, and 2 region maps; Wave22 contact graph validation passes with 1 independently scoreable contact edge; Wave25 interaction validation passes with 2 character instances, 1 event, 1 contact mask, 1 contact graph edge, and 3 merge-prevention checks. Scores are `1.0` for Wave24, Wave22, and Wave25. Boundary: local contract/mask/depth/contact preflight only, not generated-image or target-runtime certification.

- 2026-07-06T22:00:00-05:00: Resolved the ControlNet Canny local model/input blocker by downloading `diffusers/controlnet-canny-sdxl-1.0-small` fp16 safetensors from Hugging Face into ignored `models/controlnet`, recording SHA256 `fde4888a5f0a5648118991cc50e0ac4d60a2356dbaddf5e0649dd69c1119a2f9`, exposing project `controlnet` models in `config/comfyui_extra_model_paths.yaml`, generating the required white-edge-on-black control input, proving local `/object_info` sees the checkpoint/model/input, running bounded local generation through the run-package helper, and completing technical plus whole-image visual QA. Decision: treat local Canny iteration as unblocked; keep EC2 target-runtime proof as the remaining promotion boundary.

- 2026-07-06T21:26:30-05:00: Selected `MOD-17-CONTROLNET-CANNY-LANE` as the next local-first lane/module because Wave05 marks it `extract_from_current_flow`, Wave11 marks the Canny branch `wired_ready_to_verify`, and the RealVisXL SDXL base path is already locally and target-runtime proven. Extracted it as `sdxl_realvisxl_controlnet_canny_lane`, added it to Plan and exported `Workflows`, queued it as order 3, added model registry/runtime queue records, built `sdxl_realvisxl_controlnet_canny_lane_static_package_v1`, passed static validation, built the dry-run `/prompt` body, proved local object_info contains ControlNet node classes, refreshed authored-lane coverage, and reran queue validation to pass. This is not runtime-proven; the ControlNet model and control image asset remain the next blocker.

- Wave 62 was built as the final continuity and certification layer for Waves 58-62.
- Existing hydration starter files were preserved and updated instead of discarded.
- Completion rules require QA evidence and done certification before any item is marked complete.
- Runtime validations are intentionally recorded as pending when they cannot be executed during packaging.
- 2026-07-06T00:36:08-05:00: Selected Wave 59 live local directory/index validation (`TRK-W59-002`, `TRK-W59-003`) as the first active task because it is local-only, evidence-producing, and required after extraction before broader GitHub/AWS/Civitai/ComfyUI runtime work.
- 2026-07-06T00:42:00-05:00: Selected secret-safe local Git verification (`TRK-W59-004`, `TRK-W60-001`) after completing Wave 59 live index validation, because repository identity and `.env` protection must be understood before any commit, push, EC2 sync, or remote work.
- 2026-07-06T00:46:32-05:00: Selected Wave 60 operations local static validation (`TRK-W60-010`, items `W60-010` and `W60-011`) after Git verification was blocked, because script/schema/template checks are local-only and prepare future AWS/GitHub/Civitai use without contacting external services.
- 2026-07-06T00:51:11-05:00: Selected Wave 61 QA helper local validation (`TRK-W61-011`) because it is local-only, uses safe sample outputs, and improves future evidence handling before runtime artifact QA.
- 2026-07-06T00:54:25-05:00: Selected Wave 62 hydration helper local validation because session continuity helpers can be validated locally, while cumulative zip validation must remain pending if no zip exists under `C:\Comfy_UI_Main`.
- 2026-07-06T00:57:38-05:00: Selected Git recovery preflight as the next action because `BLOCKER-W59-GIT-001` blocks durable commits, GitHub sync, and future EC2 pull/sync workflows. No Git state mutation should occur until recovery evidence is recorded.
- 2026-07-06T01:01:09-05:00: User clarified that the missing `.git` blocker should be resolved by creating Git metadata in `C:\Comfy_UI_Main`. Selected guarded Git initialization plus canonical remote setup; do not commit, push, pull, or merge until status/fetch/secret-guard evidence is recorded.
- 2026-07-06T01:10:16-05:00: Verified the Git recovery evidence/tracker commit on `origin/main` at `f735d838c2ac75e928b4e069ac6ba8574347882a`; selected Wave 62 cumulative zip validation as the next local-first task.
- 2026-07-06T01:15:48-05:00: Built the final Wave 58-62 cumulative zip from tracked project files, added Git LFS coverage for zip artifacts, passed the official cumulative pack validator, and selected secret-safe runtime readiness preflight as the next task.
- 2026-07-06T01:23:01-05:00: Completed secret-safe readiness preflight. GitHub API, AWS account, EC2 identity, EBS volume, and Civitai metadata checks passed; local ComfyUI runtime is absent, so selected a bounded EC2 runtime discovery run with stop verification.
- 2026-07-06T01:46:30-05:00: Completed bounded EC2 runtime discovery. SSM and NVIDIA A10G were available and ComfyUI exists at `/home/ubuntu/ComfyUI`; no `Comfy_UI_Main` checkout was found, so selected bounded EC2 project sync as the next task.
- 2026-07-06T01:59:07-05:00: Completed bounded EC2 project sync. `/home/ubuntu/Comfy_UI_Main` now matches pushed local HEAD with Git LFS pulled and `.env` absent; selected bounded EC2 ComfyUI/model/workflow inventory next.
- 2026-07-06T02:10:57-05:00: Completed bounded EC2 runtime inventory. ComfyUI, GPU, custom nodes, model folders, and seven workflow runtime requirement templates are present; selected lowest-risk workflow lane matching before execution.
- 2026-07-06T02:40:25-05:00: Selected `sdxl_low_risk_fallback_lane` as the first bounded execution candidate because it uses the simplest standard SDXL checkpoint graph and avoids Flux or specialty-lane loader complexity for the first smoke run.
- 2026-07-06T02:40:25-05:00: Authored the SDXL low-risk `workflow.api.json`, concrete patch map, runtime requirements, and smoke request locally. Runtime promotion remains pending because the AWS CLI default login token expired before EC2 object-info, path, hash, output, and QA proof could be collected.
- 2026-07-06T02:48:46-05:00: Added reusable static validation and EC2 static-proof helpers. The selected SDXL workflow passed local graph, patch point, required-node, checkpoint-reference, and smoke-request validation; EC2 runtime proof remains pending on AWS login refresh.
- 2026-07-06T02:55:36-05:00: Added a bounded ComfyUI smoke helper and generated the exact patched `/prompt` request body for the selected SDXL lane. Execution remains blocked until EC2 static proof exists and ComfyUI API is running.
- 2026-07-06T03:00:37-05:00: Added an image artifact QA helper that creates the QA record/checklist after pullback and keeps final visual review pending until a real generated image exists.
- 2026-07-06T03:10:07-05:00: Added a secret-safe AWS auth gate helper after `aws login --remote` required browser authorization in this non-interactive shell. EC2 start and generation remain disallowed until account `029530099913` is verified and the auth gate reports `safe_to_start_ec2=true`.
- 2026-07-06T03:17:58-05:00: Added an EC2 pullback record helper because the first generated-image runtime path needs local file counts, hashes, manifest comparison, and QA routing before any pulled-back artifact can be treated as review-ready.
- 2026-07-06T03:23:45-05:00: Added a selected-lane runtime readiness gate so future EC2 work has a single local proof of lane files, helper scripts, prerequisite evidence, auth status, and static-proof/generation eligibility before any GPU-costing action.
- 2026-07-06T03:35:20-05:00: Added a bounded EC2 workflow smoke-run coordinator so the first generated-image execution has one gated path for auth/readiness/static proof, remote ComfyUI prompt execution, artifact manifest creation, optional S3 pullback, and stop verification. Dry-run evidence confirms no EC2 start or generation is allowed while AWS auth and static proof are missing.
- 2026-07-06T03:45:16-05:00: Tightened EC2 static-proof gating so `Invoke-EC2LaneStaticProof.ps1 -Execute` writes a blocked record before AWS identity checks or EC2 start when auth/readiness gates are false. Readiness and smoke-run coordinator discovery now ignore dry-run and blocked-execute records as real static proof.
- 2026-07-06T03:51:48-05:00: Added current operations helper static validation because the original Wave 60 operations validation predated the newer auth gate, pullback, readiness, static-proof, and smoke-run coordinator helpers. The validator is local-only and skips AWS/Civitai/GitHub/EC2 actions.
- 2026-07-06T03:59:00-05:00: Rechecked the stale `BLOCKER-W59-GIT-001` report instead of creating a second repository. `C:\Comfy_UI_Main` already has `.git`, canonical `origin`, ignored/untracked `.env`, required GitHub/Civitai secret variable names, and local `main` matching `origin/main`; future commands should stay anchored to `C:\Comfy_UI_Main` rather than the non-Plan workspace root.
- 2026-07-06T04:02:05-05:00: Sanitized `Test-OperationsHelperStatic.ps1` evidence output so local validation temp paths are recorded as `[VALIDATION_TEMP_ROOT]` instead of user-specific temp paths, then regenerated current operations helper validation evidence with all 14 scripts, 5 JSON files, and 6 local smoke checks passing.
- 2026-07-06T04:05:05-05:00: Hardened `Invoke-GitHubCheckpoint.ps1` so future checkpoint commits scan staged content for configured GitHub, AWS, and Civitai credential patterns and print only redacted file/line/rule findings. Added a non-mutating checkpoint-helper dry-run to current operations helper validation; latest validation passes with 7 local smoke checks.
- 2026-07-06T04:09:32-05:00: Added `Test-QAHelperStatic.ps1` because the original Wave 61 QA helper validation predated later QA helpers. Current QA helper validation now covers 5 QA scripts, 4 JSON schemas/templates, 4 markdown templates, image QA dry-run and technical sample checks, and selected-lane workflow static validation smoke without claiming runtime visual QA.
- 2026-07-06T04:12:40-05:00: Added `Test-HydrationHelperStatic.ps1` because the original Wave 62 hydration helper validation recorded `pending_no_zip_found` before the cumulative zip was created. Current validation now parses 3 hydration scripts, validates/imports 3 templates, smoke-generates session state, and validates the actual cumulative Wave 58-62 zip.
- 2026-07-06T04:15:26-05:00: Regenerated generated local indexes after adding current operations, QA, and hydration validation helpers/evidence. The generated plan/instructions indexes now include the newest helper and evidence files, and validation confirms CSV/JSON row-count parity and no `.env` or credential pattern matches.
- 2026-07-06T04:22:57-05:00: Added `Test-AwsProfileAuthMatrix.ps1` to make AWS auth diagnosis repeatable without starting EC2. Current evidence shows the active default profile is expired and all 15 configured AWS CLI profiles are unusable for expected account `029530099913`, so the blocker is AWS browser/SSO authentication rather than missing GitHub or Civitai tokens in `.env`.
- 2026-07-06T04:24:40-05:00: Regenerated generated local indexes after adding AWS profile auth matrix helper/evidence. Generated plan/instructions indexes now include the profile helper, matrix evidence, operations validation evidence, and related certifications; validation confirms row-count parity and no auth URL or credential pattern matches.
- 2026-07-06T04:29:38-05:00: Updated `Test-LaneRuntimeReadiness.ps1` to include AWS profile matrix diagnostics in selected-lane readiness evidence while keeping EC2 start gated by the auth gate. Latest readiness explicitly records `expired_session`, 15 configured profiles, 0 expected-account matches, and no EC2/generation permission.
- 2026-07-06T04:31:30-05:00: Regenerated generated local indexes after adding profile-aware readiness evidence. Generated plan/instructions indexes now include the updated readiness helper, readiness evidence/certification, operations validation evidence/certification, and validation confirms row-count parity plus no AWS auth URL or credential pattern matches.
- 2026-07-06T04:35:39-05:00: Added `Test-ItemsTrackerPackageStatic.ps1` to make current Items/Tracker package health part of the QA evidence system. Current validation passes for 54695 tracker rows and 54647 item rows, with 5059/5059 source keys covered in both packages and zero bad human flags, citations, or line ranges.
- 2026-07-06T04:40:21-05:00: Regenerated generated local indexes after Items/Tracker validation evidence and certified row-count parity: plan 2481, instructions 255, items 45, tracker 26. Discovery confirms the new Items/Tracker helper, evidence, certifications, and QA helper validation evidence are indexed, with no AWS auth URL or credential-pattern matches.
- 2026-07-06T04:46:06-05:00: Reran current AWS auth/profile gates after the latest GitHub checkpoint. Default AWS auth remains `expired_session`; all 15 configured profiles were checked and zero authenticate to expected account `029530099913`, so EC2 start and generation remain disallowed.
- 2026-07-06T04:46:38-05:00: Reran selected-lane readiness against the fresh auth/profile recheck. The SDXL low-risk lane remains locally ready, but EC2 static proof and generation remain blocked until AWS browser/SSO auth is refreshed.
- 2026-07-06T04:49:11-05:00: Regenerated generated local indexes after the auth/profile/readiness recheck and certified row-count parity: plan 2488, instructions 262, items 45, tracker 26. Discovery confirms the new auth/readiness evidence and certifications are indexed, with no AWS auth URL or credential-pattern matches.
- 2026-07-06T04:55:58-05:00: Hardened `New-EC2PullbackRecord.ps1` so `REMOTE_ARTIFACT_MANIFEST.json` is excluded from local artifact counts/hashes during manifest verification. This prevents a valid future EC2 artifact pullback from falsely failing because the manifest file itself is present beside generated artifacts.
- 2026-07-06T05:03:52-05:00: Hardened `Test-AwsAuthGate.ps1` to write top-level `result`, `failure_category`, `account_match`, and `remote_login_status` fields. This makes AWS blocker evidence easier for readiness summaries, certifications, and later recovery logic to consume without digging through nested STS records.
- 2026-07-06T05:13:48-05:00: Hardened `Test-LaneRuntimeReadiness.ps1` to write its own top-level `result` and `failure_category` and to carry auth-gate `result`, `failure_category`, `account_match`, and `remote_login_status` into readiness evidence. This prevents selected-lane runtime status from being ambiguous when AWS auth is blocked even though local pre-EC2 checks pass.
- 2026-07-06T05:17:43-05:00: Regenerated generated indexes after lane readiness contract hardening and retained a first failed index-validation record where the ad hoc probe counted JSON arrays as one wrapper object. The corrected retest passes and keeps the index-refresh trail auditable.
- 2026-07-06T05:24:27-05:00: Hardened the EC2 static-proof and workflow-smoke coordinators to emit top-level `result` and `failure_category` fields and to copy auth/readiness summaries into their gate records. This makes blocked `-Execute` evidence auditable without starting EC2 and keeps future runtime recovery focused on the exact gate that changed.
- 2026-07-06T05:31:00-05:00: Added EC2 coordinator evidence contract validation to the operations helper validator so the latest blocked coordinator records are not merely JSON-parsed; they must prove the gate result/failure fields, blocked reasons, `ec2_started=false`, and no workflow generation while blocked.
- 2026-07-06T05:42:01-05:00: Added a local-only project readiness snapshot helper because AWS browser/SSO auth still blocks runtime work, while a consolidated evidence record can prove selected-lane local readiness, current helper validation, generated index parity, secret-scan cleanliness, and the exact EC2/generation gates without starting EC2.
- 2026-07-06T05:44:50-05:00: Regenerated generated local indexes after the project readiness snapshot helper/evidence/certification so future sessions can discover the consolidated readiness record directly through the Plan and Instructions indexes.
- 2026-07-06T05:54:10-05:00: Removed literal scanner pattern strings and token-like scan labels from `Test-ProjectReadinessSnapshot.ps1` after local secret scans flagged the helper source itself. The helper now builds those scanner patterns dynamically, uses neutral labels, and the scan-safe snapshot retest passes with 0 secret/private-path hits.
- 2026-07-06T05:59:11-05:00: Refreshed the `BLOCKER-W59-GIT-001` current-state recheck instead of creating a second repository. `C:\Comfy_UI_Main` has `.git`, canonical `origin`, ignored/untracked `.env`, required GitHub/Civitai variable names without values printed, current `HEAD` matching `origin/main`, and a no-prompt push dry-run reporting `Everything up-to-date`.
- 2026-07-06T06:05:00-05:00: Hardened `Test-QAHelperStatic.ps1` so project-readiness snapshot smoke validation now requires explicit contract checks for recognized result, `local_ready=true`, scan result `pass`, scan hit count 0, runtime gates present, EC2/generation gate consistency, and blocked-execute coordinator safety while AWS auth remains expired.
- 2026-07-06T06:07:10-05:00: Regenerated generated indexes after QA helper project-readiness contract hardening and certified row-count parity plus discoverability for the new helper evidence, project readiness snapshot, contract certification, and index refresh evidence.
- 2026-07-06T06:12:37-05:00: Added `New-RuntimeUnblockHandoff.ps1` because the first post-auth runtime path needed one local-only handoff packet with exact commands and geometry gates. The handoff records `handoff_ready_runtime_blocked_auth`, `aws_contacted=false`, `ec2_started=false`, and `generation_executed=false`, and operations validation now smoke-checks that contract.
- 2026-07-06T06:14:30-05:00: Regenerated generated indexes after runtime handoff evidence/certification and certified row-count parity plus discoverability for the new helper, JSON/Markdown handoff, operations validation, readiness snapshot, and index evidence.
- 2026-07-06T06:19:38-05:00: Hardened `Test-ProjectReadinessSnapshot.ps1` and `Test-QAHelperStatic.ps1` so the consolidated project readiness snapshot must include the runtime unblock handoff and the QA helper must prove it is local-only, no external contacts occurred, EC2 was not started, generation was not run, the eight-step command handoff exists, and the Markdown handoff was written.
- 2026-07-06T06:20:43-05:00: Regenerated generated indexes after runtime handoff readiness contract hardening. This confirms the Git blocker is resolved and discoverable while the remaining runtime blocker is AWS auth, not missing GitHub/Civitai keys in `.env`.
- 2026-07-06T06:31:45-05:00: Added a local Git checkpoint gate to the EC2 static-proof and workflow-smoke coordinators. Future `-Execute` runs now require local `HEAD` to equal `origin/main` with a clean worktree before any EC2 start path, and the remote payload verifies the EC2 checkout reaches the expected pushed commit after `git pull --ff-only origin main`.
- 2026-07-06T06:31:45-05:00: Refreshed the runtime unblock handoff with a `git_checkpoint_recheck` command step and safety invariant so the post-auth handoff now distinguishes AWS auth, local Git checkpoint cleanliness, lane readiness, EC2 static proof, generation, pullback, and image QA gates.
- 2026-07-06T06:38:42-05:00: Added post-checkpoint Git recheck evidence after pushing the EC2 Git checkpoint gate commit. Current local `main` and `origin/main` both resolve to `535c3320f443b05e1ab6dc236004fc36e0bfa611`, the worktree is clean, `.env` is ignored/untracked, and the remaining runtime blocker is AWS auth rather than GitHub or Civitai token presence.
- 2026-07-06T06:49:27-05:00: Authored `sdxl_realvisxl_base_lane` as the second concrete local SDXL lane because RealVisXL is the planned SDXL hyperrealism/refine family. It is static-valid and request-buildable, but remains blocked from promotion until EC2 verifies object_info, checkpoint path/hash/load, output generation, pullback, and image QA.
- 2026-07-06T06:58:21-05:00: Hardened lane runtime readiness after adding the second authored lane. Readiness/static-proof/smoke-run evidence is now selected and gate-checked by `LaneId`; QA helper validation runs lane-runtime readiness smokes for both authored base-generation lanes; RealVisXL coordinator dry-runs prove no EC2 start or generation while AWS auth is blocked.
- 2026-07-06T07:12:30-05:00: Hardened the project readiness snapshot and runtime unblock handoff to select lane-matched evidence by `LaneId`. The current low-risk lane handoff now includes explicit `-LaneId sdxl_low_risk_fallback_lane` commands, and QA helper contract checks prove the snapshot, lane readiness, and runtime handoff agree on the first EC2 proof lane.
- 2026-07-06T07:19:43-05:00: Added authored-lane evidence coverage validation because the project now has two concrete authored SDXL lanes and needs a repeatable local pre-EC2 coverage check. The new QA helper smoke proves both `sdxl_low_risk_fallback_lane` and `sdxl_realvisxl_base_lane` have lane-matched static validation, smoke dry-run/request, and lane readiness evidence before any AWS/EC2 runtime attempt.
- 2026-07-06T07:35:23-05:00: Added a local runtime lane queue contract because the project now has two concrete authored base-generation lanes and needs a testable execution order before AWS auth resumes. The queue fixes `sdxl_low_risk_fallback_lane` as the first EC2 proof/generation lane and keeps `sdxl_realvisxl_base_lane` queued second until the low-risk lane has object-info, checkpoint path/hash, output, pullback, and image QA evidence.
- 2026-07-06T07:52:41-05:00: Integrated runtime lane queue evidence into project readiness and runtime unblock handoff because queue order should be a gate, not just a separate report. The readiness snapshot now disallows EC2 static proof unless the selected lane is the first queued runtime lane, and the handoff now includes a queue recheck command before any EC2 execute path.
- 2026-07-06T08:15:38-05:00: Added `tools\New-WorkflowRunPackage.ps1` and generated the first root-level local run package for `sdxl_low_risk_fallback_lane` so the exported workflow has a concrete patched `/prompt` body, copied lane files, static validation, smoke dry-run, and package manifest ready for post-auth EC2 static proof and bounded execution.
- 2026-07-06T09:07:34-05:00: Added profile-aware run package support and generated `hyperreal_editorial_portrait_v1` for `sdxl_low_risk_fallback_lane`; the package applies the prompt profile to the packaged lane copy, builds the concrete hyperreal portrait `/prompt` body, passes local static/smoke validation, and remains blocked from generation until AWS auth and EC2 static proof pass.
- 2026-07-06T09:17:11-05:00: Added `-RunPackageManifestFile` to `Invoke-EC2WorkflowSmokeRun.ps1` because the first real hyperreal execution should consume the verified run package request, not rebuild an anonymous smoke request; the dry-run evidence proves the package is hash/profile/lane validated and still blocks before EC2 start while AWS auth is expired.
- 2026-07-06T09:24:29-05:00: Made `New-RuntimeUnblockHandoff.ps1` package-aware because the generated post-auth handoff should tell the operator/coordinator to use the verified hyperreal package; operations validation now smoke-checks that the bounded workflow command includes `-RunPackageManifestFile` whenever a package is supplied.
- 2026-07-06T09:34:15-05:00: Created the primary model registry folder, seeded checkpoint records for the first two active SDXL runtime lanes, captured RealVisXL V5.0 Civitai metadata through the project `.env` credentials without printing secrets, fixed the Civitai lookup helper URL encoder for this PowerShell runtime, and added `Test-WorkflowModelRegistryCoverage.ps1` so active lane model/queue coverage is locally provable before EC2 starts.
- 2026-07-06T09:45:00-05:00: Integrated model registry coverage into selected-lane runtime readiness, project readiness, and runtime unblock handoff because checkpoint registry/queue coverage should be a first-class EC2 preflight gate. The current handoff now includes `model_registry_coverage_recheck`, command step count `11`, and a safety invariant forbidding EC2 start unless coverage passes.
- 2026-07-06T10:15:00-05:00: Rechecked root Git/scaffold state from `C:\Comfy_UI_Main` after pushing commit `2a1449601bc2d022fa5034fd2b5940f3ef3a474e`; root preflight passed with `.git` present, `HEAD == origin/main`, ignored `.env`, root file structure present, active exported lanes static-valid, and model registry coverage passing. Continue treating `BLOCKER-W59-GIT-001` as resolved; AWS auth expiry is the remaining runtime blocker.
- 2026-07-06T10:30:00-05:00: Refreshed root preflight again after evidence commit `8bd059bdec2b2c8bd95a158930d2a26fa9d77b0a` reached `origin/main`, so the latest root proof now matches the current pushed checkpoint. This remains local-only and does not unblock EC2 until AWS auth passes.
- 2026-07-06T12:56:00-05:00: Activated Wave 63 EC2 cost controls and aligned hydration state with the newest RealVisXL evidence. The low-risk lane proof is complete; RealVisXL object-info/core-node proof passed but the checkpoint is missing on EC2. Future work must resolve the model through a non-Git path, verify SHA256, use local/CI deploy-bundle preparation while EC2 is stopped, default EC2 helpers to `-SkipGitLfsPull`, and set `-MaxEc2RuntimeMinutes`.
- 2026-07-06T13:13:00-05:00: Advanced the runtime queue contract after the completed low-risk proof. `runtime_lane_queue.json` now keeps `sdxl_low_risk_fallback_lane` as the completed first proof lane and makes `sdxl_realvisxl_base_lane` the current runtime lane; project readiness and runtime handoff selectors now use current-lane evidence instead of hardcoded order-1 evidence.
- 2026-07-06T14:11:04-05:00: Marked the RealVisXL single runtime smoke proof complete after model install, SHA256 verification, EC2 static proof, workflow smoke generation, local pullback hash verification, technical image QA, and visual QA all passed. Project readiness now emits `pass_runtime_smoke_qa_complete`, runtime handoff emits `handoff_runtime_smoke_qa_complete`, and QA contracts allow completed previous lanes to remain queued without being the current runtime lane. Do not rerun this proof unless the lane, prompt, model, runtime, or QA objective changed.
- 2026-07-06T12:49:30-05:00: Classified the RealVisXL second-lane runtime blocker as a missing EC2 checkpoint, not a Git or `.env` problem. EC2 `/object_info` passed and final state was verified `stopped`, but `realvisxlV50_v50Bakedvae.safetensors` was absent from `/home/ubuntu/ComfyUI/models/checkpoints/`. Static-proof and readiness helpers now block generation on missing required models or hashes, and Wave63 cost-control tooling is locally validated.
- 2026-07-06T13:45:00-05:00: Accepted the S3-first cost-control architecture for RealVisXL runtime work. GitHub Actions/local tools should prepare deploy bundles while EC2 is stopped, upload bundles and model binaries to S3/model-cache prefixes, use least-privilege AWS policy templates from `configs/aws`, install RealVisXL on EC2 with `Install-EC2ModelFromS3.ps1`, run EC2 helpers with `-DeployBundleS3Uri` and `-DeployBundleSha256`, and protect live windows with EventBridge Scheduler emergency stops plus optional instance-side watchdogs.
- 2026-07-06T13:48:36-05:00: Superseded the RealVisXL missing-checkpoint blocker. Newer evidence shows model install, SHA256 verification, EC2 static proof after install, and workflow smoke generation completed. This was later superseded again by the 2026-07-06T14:11:04 terminal-state decision: pullback and image QA are complete, and S3 permissions/configuration are now a future cost-saving improvement rather than a blocker for this smoke proof.
- 2026-07-06T14:01:00-05:00: Superseded the RealVisXL pullback/QA blocker. SSM-backed SCP over Session Manager succeeded after tightening `comfyui-lora-key.pem` ACLs, EC2 final state was verified `stopped`, pullback hashes were verified, and RealVisXL technical plus visual image QA passed with runtime-smoke notes. S3 remains the preferred future cost-control path, not a blocker for this completed smoke.
- 2026-07-06T14:59:31-05:00: Aligned model registry state with completed runtime-smoke evidence. The active low-risk and RealVisXL model records and runtime-validation queue rows now use completed smoke-proof statuses with evidence paths; `Test-WorkflowModelRegistryCoverage.ps1` is state-aware so future pending lanes still require queued state while smoke-proven lanes must keep evidence-backed completed state.
- 2026-07-06T15:03:12-05:00: Validated Wave64 strict AI-operational coverage. Wave64 adds current Items and Tracker rows for whole-artifact visual/audio review, localized regression, runtime proof, QA evidence, and release controls; reports pass with 66 item rows, 66 tracker rows, and 28 required domains covered. This is a coverage/control layer and does not mark the full project complete.
- 2026-07-06T15:18:00-05:00: Implemented the Wave64 image-engine router gate for `TRK-W64-009` / `ITEM-W64-009`. Route selection now derives from active lanes, runtime queue, runtime requirements, and model registry evidence; the RealVisXL SDXL route passes with checkpoint hash/path/object_info/runtime/QA proof, while an incompatible Flux LoRA request on SDXL blocks without silent fallback, EC2 start, generation, or external service contact.
- 2026-07-06T15:36:12-05:00: Extended the Wave64 image-engine router gate into workflow run package creation. `tools\New-WorkflowRunPackage.ps1` now accepts `-RouteRequestFile`, writes `router_decision.json`, records `route_gate` in `RUN_PACKAGE_MANIFEST.json`, and blocks package creation when the router-selected lane does not match the requested package lane. Dedicated W66 validation and QA helper validation both passed locally with no AWS/GitHub API/Civitai/ComfyUI contact, EC2 start, or generation.
- 2026-07-06T15:50:49-05:00: Prepared broader RealVisXL image-quality certification locally by adding a three-sample package matrix. The new profiles cover close-up skin/eyes, hands/fabric/contact realism, and environmental low-light coherence. `tools\New-WorkflowRunPackageMatrix.ps1` produced three router-gated packages and a matrix manifest, and `Test-WorkflowRunPackageMatrix.ps1` plus QA helper validation passed locally. This prepares the future EC2 quality run but does not certify final image quality until generation, pullback, hash verification, and whole-image visual QA are complete for every sample.
- 2026-07-06T17:00:52-05:00: Added the local-only RealVisXL matrix deploy-bundle path. `tools\New-EC2DeployBundleMatrix.ps1` packages the matrix manifest, matrix source JSON, prompt profiles, shared project context, and all three sample run packages into one ZIP; `Test-EC2DeployBundleMatrix.ps1` and QA helper validation passed locally with no AWS/GitHub API/Civitai/ComfyUI contact, EC2 start, or generation. Wave65 now covers 2,837 current Plan files with 662 closure rows and zero missing.
- 2026-07-06T17:12:55-05:00: Hardened the RealVisXL matrix S3 bridge. `Publish-DeployBundleToS3.ps1` now preserves the supplied manifest filename, so matrix bundles publish `DEPLOY_BUNDLE_MATRIX_MANIFEST.json`; EC2 static-proof and workflow-smoke helpers now read either standard or matrix deploy-bundle manifests after extraction. Direct matrix validation, QA helper validation, and operations helper validation all passed locally with no AWS contact, EC2 start, or generation. Wave65 now covers 2,840 current Plan files with 665 closure rows and zero missing.
- 2026-07-06T17:31:38-05:00: Added the RealVisXL matrix quality-run execution planner. `New-EC2WorkflowMatrixQualityRunPlan.ps1` validates all three matrix package manifests and emits bounded per-sample `Invoke-EC2WorkflowSmokeRun.ps1` commands with `-RunPackageManifestFile`, matrix S3 bundle URI/SHA arguments, `-SkipGitLfsPull`, `-MaxEc2RuntimeMinutes`, pullback commands, and whole-image QA commands. Direct planner validation, QA helper validation, and operations helper validation passed locally with no AWS contact, EC2 start, or generation. Wave65 now covers 2,845 current Plan files with 670 closure rows and zero missing.
- 2026-07-06T17:45:42-05:00: Added the S3 runtime config plan layer because current readiness is blocked by missing bucket/base URI and IAM role values, not by GitHub or Civitai tokens. `New-S3RuntimeConfigPlan.ps1` creates redacted env lines, renders five policy previews for supplied bucket/role values, and emits the next readiness/publish/emergency-stop/matrix-plan commands without contacting AWS or starting EC2. Direct validation, operations helper validation, and QA helper validation passed locally. Wave65 now covers 2,851 current Plan files with 676 closure rows and zero missing.
- 2026-07-06T17:58:08-05:00: Initialized the real S3/IAM runtime infrastructure from `C:\Comfy_UI_Main` instead of treating `.env` tokens as the issue. `Initialize-S3RuntimeInfrastructure.ps1 -Execute -UpdateEnv` created/configured bucket `comfy-ui-main-runtime-029530099913-us-east-1`, attached EC2 runtime S3 access, created the GitHub OIDC deploy role and scheduler stop role, updated only non-secret local `.env` values, and kept EC2 `stopped` with no generation. `Test-S3RuntimeTransferReadiness.ps1` now reports `ready_local_only`; next step is S3 publishing of the RealVisXL matrix deploy bundle.
- 2026-07-06T18:00:00-05:00: Refreshed Wave65 after S3 runtime infrastructure additions. Current coverage is 2,855 Plan files, 680 closure rows, and 0 missing; this tracks source coverage and does not certify final media quality.
- 2026-07-06T18:12:52-05:00: Published the RealVisXL three-sample matrix deploy bundle to S3 and verified the uploaded ZIP by download SHA256. Uploaded bundle URI is `s3://comfy-ui-main-runtime-029530099913-us-east-1/deploy-bundles/rvxl_mx_s3_20260706T181144-0500/rvxl_mx_s3_20260706T181144-0500.zip`; SHA256 is `d3d81bbe2b6cb678304ab06ddf9cb707da31721cb01ca9c26df729414396cc84`. Regenerated the matrix quality-run plan with that real URI/SHA. EC2 stayed `stopped` and no generation ran; next step is fresh auth/Git/readiness/static gates before any bounded three-sample EC2 execution.
- 2026-07-06T18:14:00-05:00: Refreshed Wave65 after S3 matrix publish evidence. Current coverage is 2,859 Plan files, 684 closure rows, and 0 missing.
- 2026-07-06T18:23:20-05:00: Prepared the S3-backed matrix quality EC2 window with fresh auth, queue, model-registry, and RealVisXL readiness gates, and created a verified one-time EventBridge Scheduler emergency stop. Fixed `New-EC2EmergencyStopSchedule.ps1` after the first helper attempt exposed Windows CLI quoting and long schedule-name issues; the fixed helper now uses short names and `Mode=OFF`. EC2 remained stopped and no generation ran. Commit this gate checkpoint before the actual S3-backed static proof so the EC2 helper's clean-Git gate can pass.
- 2026-07-06T18:24:00-05:00: Refreshed Wave65 after the matrix pre-EC2 gates and emergency-stop helper fix. Current coverage is 2,865 Plan files, 690 closure rows, and 0 missing.
- 2026-07-06T18:36:13-05:00: Ran the S3-backed RealVisXL matrix static-proof attempt and confirmed the geometry gate works: EC2 started, SSM ran, EC2 stopped, and no generation ran, but the remote helper rejected the uploaded bundle because its source head `27111d0c606336e5c67c529228e11703974b02e7` did not match current `origin/main` `ce4487f5cfbd72448e5bec1d3191d076ec4d97af`. Next action is to rebuild and publish a fresh bundle from the current pushed head, then retry static proof.
- 2026-07-06T18:37:00-05:00: Refreshed Wave65 after stale-bundle static-proof evidence. Current coverage is 2,866 Plan files, 691 closure rows, and 0 missing.
- 2026-07-06T19:07:00-05:00: Recovered from the stale-bundle block by building/publishing fresh bundle `rvxl_mx_s3b_20260706T184054-0500` from clean head `59d34ea1d1e057f628b160c4629fb1e5736bb4cf`, download-verifying SHA256 `e1044e447abb548db5e834ba26c8376ba0a80ad463fadd5b969346edf30a3605`, rerunning EC2 static proof successfully, and executing RealVisXL matrix sample 1. The generated close-up skin/eye PNG pulled back through S3, hashes verified, technical QA passed, visual QA passed with notes, and EC2 final state is `stopped`. Samples 2 and 3 remain pending behind a new clean-head checkpoint/rebundle gate.
- 2026-07-06T19:08:00-05:00: Refreshed Wave65 after RealVisXL matrix sample 1 evidence. Current coverage is 2,883 Plan files, 708 closure rows, and 0 missing.
- 2026-07-06T19:10:00-05:00: Hardened Wave65 citation extraction for binary/media and control-heavy log files after the pulled-back sample image caused raw PNG/log control data to enter generated CSV excerpts. The generator now writes safe binary/media summaries, Wave65 still passes, and `git diff --check` is clean.
- 2026-07-06T19:38:10-05:00: Generated and QA-reviewed RealVisXL matrix sample 2 using fresh bundle `rvxl_mx_s3c_20260706T191636-0500` from clean head `d262a2a`. Static proof passed, sample 2 generated a seated hands/fabric portrait, S3 pullback hashes verified, technical QA passed, and visual QA passed with minor interlocked-finger/contact compression notes. Sample 3 remains pending behind a clean checkpoint/rebundle gate.
- 2026-07-06T19:40:00-05:00: Refreshed Wave65 after RealVisXL matrix sample 2 evidence. Current coverage is 2,901 Plan files, 726 closure rows, and 0 missing.
- 2026-07-06T20:10:00-05:00: Completed and certified RealVisXL matrix sample 3 using fresh bundle `rvxl_mx_s3d_20260706T194502-0500` from clean head `5d988e6`. Static proof passed, sample 3 generated a low-light environmental portrait, S3 pullback hashes verified, technical QA passed, visual QA passed with minor lamp-edge/skin-polish notes, and final certification `W66_REALVISXL_MATRIX_FINAL_QA_CERTIFICATION_20260706T201000-0500.json` records all three matrix samples as certified with notes. EC2 final state is `stopped`.
- 2026-07-06T20:13:00-05:00: Refreshed Wave65 after RealVisXL matrix sample 3 and final certification evidence. Current coverage is 2,920 Plan files, 745 closure rows, and 0 missing.
- 2026-07-06T20:26:00-05:00: Advanced the local-first runtime path after matrix certification. Added `tools\Initialize-LocalComfyUICheckout.ps1`, ignored external `ComfyUI/` runtime folders, cloned the local ComfyUI checkout to `C:\Comfy_UI_Main\ComfyUI` at head `7747c342d4143f35e7c8031dddf3ee4455f10a2e`, proved `main.py --help` works, and hardened `tools\Test-LocalComfyUIDevPreflight.ps1` to record Torch CUDA and required local model presence. Current local preflight is `pass_local_dev_candidate`, but local GPU generation remains pending CUDA-enabled Torch and local RealVisXL checkpoint placement; EC2 remains required for final target proof.
- 2026-07-06T20:29:00-05:00: Refreshed Wave65 after local ComfyUI checkout bootstrap, CLI smoke, hardened local preflight, and start-plan evidence. Current coverage is 2,926 Plan files, 751 closure rows, and 0 missing.
- 2026-07-06T20:48:00-05:00: Completed local ComfyUI readiness prerequisites for a bounded local RealVisXL smoke. `Initialize-LocalComfyUIPythonEnv.ps1` created an ignored venv with `torch 2.11.0+cu128`, CUDA 12.8, and RTX 5060 detection; RealVisXL version `789646` downloaded from Civitai to ignored `models\checkpoints\realvisxlV50_v50Bakedvae.safetensors` and SHA256 matched `6a35a7855770ae9820a3c931d4964c3817b6d9e3c6f9c4dabb5b3a94e5643b80`; hardened local preflight now reports `pass_local_gpu_generation_candidate`; local `/object_info` smoke reports 791 nodes and all required workflow nodes present. No EC2 was started.
- 2026-07-06T20:49:00-05:00: Refreshed Wave65 after local CUDA/model/object-info readiness evidence and model registry updates. Current coverage is 2,932 Plan files, 757 closure rows, and 0 missing.
- 2026-07-06T20:58:00-05:00: Proved the local RealVisXL path with an actual bounded local ComfyUI generation. The new local smoke profile and extra-model-paths config let the ignored local ComfyUI checkout load the verified project RealVisXL checkpoint, generate one 512x512 PNG, pull it into project evidence, pass technical image QA, and pass whole-image visual QA with local-smoke notes. This is a local iteration proof only; EC2 target-runtime proof and final portfolio certification remain separate gates.
- 2026-07-06T21:02:00-05:00: Refreshed Wave65 after local RealVisXL smoke generation and QA evidence. Current coverage is 2,939 Plan files, 764 closure rows, and 0 missing.
- 2026-07-06T21:12:00-05:00: Converted the ad hoc local smoke execution path into `tools\Invoke-LocalComfyUIRunPackageSmoke.ps1`. Dry-run validates package/lane/hash/root without contacting ComfyUI; execute starts the local checkout, posts the packaged prompt, copies outputs into project pullback evidence, and stops the process. The helper was execute-proven on the bounded RealVisXL package and the generated PNG passed technical plus whole-image visual QA.
- 2026-07-06T21:13:00-05:00: Refreshed Wave65 after adding the reusable local helper and helper QA evidence. Current coverage is 2,946 Plan files, 771 closure rows, and 0 missing.
- 2026-07-07T01:35:00-05:00: Aligned the current runtime queue with the locally proven ControlNet Canny lane instead of leaving Canny behind stale pending-provisioning text. `runtime_lane_queue.json` and exported `ACTIVE_LANES.json` now point to `sdxl_realvisxl_controlnet_canny_lane`, attach local pre-EC2 proof evidence, and keep target-runtime proof blocked until AWS auth permits EC2 static proof.
- 2026-07-07T01:40:00-05:00: Made the Canny runtime unblock handoff lane-aware for auth/profile evidence by preferring the auth gate and profile matrix selected by lane readiness. This prevents old global W60/W61 auth records from being mistaken for the current Canny blocker.
- 2026-07-07T01:45:00-05:00: Synced QA helper project-readiness contracts with the explicit `handoff_ready_runtime_blocked_auth` result and fixed the image-engine router to read UTF-8-BOM JSON/JSONL files. QA helper validation now passes for the Canny current queue/handoff/model-registry/project-readiness state with no EC2 start or generation.
- 2026-07-07T02:29:00-05:00: Completed the bounded Canny v4 target-runtime smoke after the cleaned input install fix. Static proof passed from a clean pushed deploy bundle, the first generation attempt exposed missing `controlnet_canny_cleaned_eye_safe_v1.png` on EC2, the cleaned input was installed and hash-verified, and the rerun generated one pulled-back PNG with verified hash `7951e6a37e8e05bbf22604ac03eac38831875ed283206af8f6a99d874ad3e523`. Technical QA passed and whole-image visual QA passed with runtime-smoke notes; `runtime_lane_queue.json` now marks `sdxl_realvisxl_controlnet_canny_lane` as `runtime_smoke_proven`, while broader multi-sample certification remains pending.
- 2026-07-07T02:29:00-05:00: Refreshed Wave65 after Canny target-runtime evidence and queue alignment. Current coverage is 3,107 Plan files, 932 closure rows, and 0 missing.
## Decision - Clean Git Removes Only Git Blockers, Not Live Gates - 2026-07-09T17:08:00-05:00

The selected-inpaint runtime chain now treats the clean/synced Git checkpoint gate as satisfied when evidence reports `passes_for_ec2_execute=true`. This removes stale dirty-Git blocker strings from target plan, pre-EC2 handoff, runbook, execution snapshot, and final launch gate, but does not authorize S3 Execute, EC2 start, ComfyUI prompts, generation, final certification, mask promotion, Wave70 hard gates, Wave71+, or Jira mutation.
## Decision - Supersede Stale RealESRGAN Package Before Any Upload - 2026-07-10T11:46:52-05:00

Do not publish or execute from `runtime_artifacts/run_packages/upscale_polish_w69_canny_seed711570105/RUN_PACKAGE_MANIFEST.json`; it is retained only as historical regression evidence and fails `stale_clean_git_metadata`. Use the current package `upscale_polish_w69_canny_seed711570105_current_3e4207a` and clean bundle `realesrgan_current_3e4207a`, validated by `W66_REALESRGAN_CURRENT_RUN_PACKAGE_DEPLOY_BUNDLE_CONSISTENCY_20260710T114200-0500.json`.
