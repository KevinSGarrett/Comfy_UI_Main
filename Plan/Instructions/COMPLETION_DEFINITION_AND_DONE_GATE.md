<!--
Wave 58 — Autonomous Instruction Manual + AI Project Manager Brain
Target path after extraction: C:\Comfy_UI_Main\Plan\Instructions
This file is designed for Codex Desktop autonomous operation.
-->

# COMPLETION_DEFINITION_AND_DONE_GATE

## 1. Purpose

This file defines what “done” means. Codex Desktop must never mark a project item, tracker row, workflow, model, prompt, script, generated artifact, or wave as complete unless the required evidence exists.

Completion is a certification gate, not an opinion.

## 2. Completion levels

Codex must use proof levels instead of vague completion language.

```text
LEVEL 0 — NOT_STARTED
No meaningful work has begun.

LEVEL 1 — SELECTED
Task has been selected and pursuing goal is written.

LEVEL 2 — IMPLEMENTED_NOT_VERIFIED
Files/code/workflow/docs were created or edited, but validation is missing or incomplete.

LEVEL 3 — STATIC_VALIDATION_PASSED
Files parse, schemas validate, references resolve, and local non-runtime checks pass.

LEVEL 4 — RUNTIME_VALIDATION_PASSED
Workflow/script/system executed and produced expected output.

LEVEL 5 — QA_PASSED
Required visual/audio/video/manual-style autonomous QA checks passed.

LEVEL 6 — READY_FOR_CERTIFICATION
All expected evidence exists and tracker/report updates are prepared.

LEVEL 7 — COMPLETE_CERTIFIED
Implementation, validation, QA, tracker update, evidence, report, and manifest are all complete.
```

Only Level 7 equals complete.

### 2.1 Lane completion vocabulary

Use `bounded_scope_complete` for a proven sample, seed, prompt, pose, resolution, or configuration. Do not shorten it to "lane complete." Package creation, queue progression, static readiness, S3 staging, and dry-run success are not runtime completion. A production image, video, or audio lane is certified only when its declared multisample scope has genuine runtime artifacts, applicable technical QA, and direct modality review.

Portfolio delivery truth and lane classifications are governed by:

```text
Plan/Instructions/COMFYUI_DELIVERY_RECOVERY_AND_PORTFOLIO_CONTROL.md
Plan/10_REGISTRIES/comfyui_delivery_portfolio_registry.json
```

## 3. Universal done gate

A task can be marked `COMPLETE_CERTIFIED` only when all applicable questions are answered yes:

```text
Implementation:
Was the requested thing actually created or updated?

Scope:
Was the work limited to the selected task or logged as scope change?

Static validation:
Did all files parse/validate?

Reference validation:
Do paths, links, model references, node references, and registry references resolve?

Runtime validation:
If execution is required, did it run and produce expected output?

Visual QA:
If image output is involved, was autonomous image review completed and passed?

Video QA:
If video/GIF output is involved, was autonomous temporal review completed and passed?

Audio QA:
If audio output is involved, was autonomous audio review completed and passed?

Failure handling:
Were failures, retries, and known issues recorded?

Tracker:
Was the tracker updated or was a tracker update artifact generated?

Items:
Were itemized-list impacts recorded or mapped?

Evidence:
Are proof files/logs/reports linked?

Release:
Were delivery report, validation report, and manifest updated?

Rehydration:
Was next-session state updated?

Portfolio:
Is the result reflected accurately in the delivery portfolio without overstating bounded proof?
```

If any applicable answer is no, the item is not complete.

### 3.1 Core autonomous versus independent-anchor mask dependency gate

Gold-standard mask work follows:

```text
Plan/Instructions/QA/GOLD_STANDARD_MASK_DEPENDENCY_GATE_PROTOCOL.md
```

For `core_autonomous_runtime`, missing manual/human-anchor masks are not a
blocker. Core mask authority may be satisfied by an active, unexpired,
unrevoked, exact-output certificate issued by `maskfactory_autonomous` when its
release, capability, access mode, execution stack, source/output hashes, owner,
transform, QA, scope, signature, and revocation evidence pass.

Missing human anchors block only `independent_real_accuracy` or a row whose
acceptance contract explicitly requires an independent human-labelled claim.
Use `Blocked_Independent_Anchor_Dependency_Missing` for that exact optional
scope. Legacy `Blocked_Gold_Mask_Dependency_Missing` statuses migrate to the new
blocker only for optional independent-anchor claims; otherwise re-evaluate the
row against the autonomous core authority path.

Candidate, draft, or unbound masks remain non-authoritative. They cannot support
false core certification or independent-accuracy claims. Unrelated work and
eligible exact-certificate core mask, geometry, bridge, and downstream work may
continue while optional independent anchors are absent.

### 3.2 Core autonomous versus independent perceptual calibration gate

For `core_autonomous_runtime`, image, video, audio, AV, model-ranking, and
LLM/VLM qualification reviews use versioned deterministic validators, exact
metrics, qualified calibrated autonomous critics, abstention/disagreement rules,
and a signed policy decision. These runtime-proof and whole-artifact QA
requirements remain mandatory; the rule removes only an implicit human-work
dependency.

Blind human visual comparison, listening panels, and human/operator adjudication
belong to the optional `independent_perceptual_calibration` profile unless the
user explicitly requests and separately authorizes an override. Missing optional
human perceptual evidence cannot block, revoke, downgrade, or redefine core
completion. A user override is never implicit and cannot waive a never-waivable
core integrity, ownership, safety, provenance, or hard-QA failure.

Rows157, 167, 172, 190, 192, 204, 209, and 211 use this interpretation. Their
runtime-proof requirements remain true; their review methods are autonomous for
core and human review is optional calibration evidence only. Rows261-320 use the
same autonomous-policy-first release rule.

## 4. Documentation-only done gate

For documentation/instruction waves such as Wave 58, runtime proof is usually not required. The done gate is:

```text
Required files exist.
Required sections exist.
Paths are correct.
Instructions are actionable.
No secrets are included.
No runtime success is claimed.
Manifest exists.
Delivery report exists.
Validation report exists.
File index exists.
Hydration starter exists.
Package zip validates.
```

## 5. Code/script done gate

For scripts or code:

```text
File exists in expected location.
Syntax parses.
Dependencies are declared.
No hardcoded secrets.
Expected inputs/outputs are documented.
Unit/smoke test exists where useful.
Script runs or dry-runs successfully.
Failure modes are handled.
Logs are written.
Tracker/evidence updated.
```

## 6. ComfyUI workflow done gate

For ComfyUI workflows:

```text
Workflow JSON exists.
JSON parses.
Node classes are known or documented as required dependencies.
Links are valid.
Required models exist or are registered as pending.
Input contract exists.
Output contract exists.
QA contract exists.
Paths are correct.
Static workflow validation passes.
Runtime execution passes when required.
Generated output exists.
QA review passes.
Evidence saved.
```

## 7. Model/LoRA/checkpoint done gate

For models:

```text
Model metadata exists.
Source is recorded.
Version is recorded.
Base model compatibility is recorded.
Trigger words are recorded when available.
Local path is recorded.
File exists.
File hash is recorded when available.
Model type is classified.
Workflow lane is assigned.
Compatibility test is passed or pending with reason.
Visual/audio/video impact is reviewed when used.
```

## 8. Image artifact done gate

For generated images:

```text
Prompt and settings recorded.
Seed recorded when available.
Model/LoRA stack recorded.
Workflow/output path recorded.
Image exists and opens.
Resolution/aspect ratio correct.
Prompt compliance reviewed.
Anatomy reviewed.
Hands/feet reviewed when visible.
Face/eyes/skin reviewed when visible.
Contact/collision/deformation reviewed when applicable.
Lighting/background reviewed.
Artifacts reviewed.
QA score meets threshold.
Failures logged with before/after if fixed.
```

## 9. Video/GIF artifact done gate

For generated videos/GIFs:

```text
Prompt/settings recorded.
Frame count/FPS/duration recorded.
Model/workflow recorded.
Output exists and opens.
Sampled frames reviewed.
Temporal consistency reviewed.
Flicker reviewed.
Identity drift reviewed.
Motion/contact reviewed.
Loop seam reviewed if looped.
Audio sync reviewed if audio exists.
QA score meets threshold.
```

## 10. Audio artifact done gate

For generated audio:

```text
Input text/prompt recorded.
Voice/model/settings recorded.
Output exists and opens.
Duration/sample rate recorded.
Clipping checked.
Noise/distortion checked.
Pacing/tone checked.
Pronunciation checked when speech exists.
Loudness consistency checked.
Video sync checked if applicable.
QA score meets threshold.
```

## 11. Tracker update requirements

Every completed task must include tracker evidence:

```text
Status
Timestamp
Files changed
Validation result
QA result if applicable
Evidence paths
Known issues
Next action
Certification result
```

If tracker files are unavailable, Codex must create a tracker update artifact that can be applied later and must not claim the tracker itself was updated.

## 12. Certification language

Allowed:

```text
Complete certified: static validation passed; no runtime required for this documentation wave.
Implemented but not verified: files created but validation not yet run.
Runtime validated: workflow executed and output exists.
QA passed: visual review score exceeded threshold.
Blocked external resource: AWS auth unavailable; local work continued.
```

Not allowed:

```text
Probably done.
Looks good.
Should work.
Finished I think.
Complete because files were created.
Runtime passed without output evidence.
QA passed without review evidence.
```

## 13. Wave 58 done gate

Wave 58 is complete only when these files exist:

```text
AUTONOMOUS_CODEX_DESKTOP_MASTER_MANUAL.md
AI_PROJECT_MANAGER_DYNAMIC_OPERATING_MODEL.md
NO_LOOP_NO_DRIFT_PROGRESS_CONTROL.md
PURSUING_GOAL_TEXT_UPDATE_PROTOCOL.md
AUTONOMOUS_DECISION_TREE_AND_RECOVERY_PROTOCOL.md
COMPLETION_DEFINITION_AND_DONE_GATE.md
DAILY_SESSION_REHYDRATION_PROTOCOL.md
```

And these evidence files exist:

```text
Manifests/wave58_package_manifest.json
Reports/WAVE58_DELIVERY_REPORT.md
Reports/WAVE58_VALIDATION_REPORT.json
Reports/WAVE58_FILE_INDEX.md
Hydration_Rehydration/CURRENT_SESSION_STATE.md
Hydration_Rehydration/CURRENT_PURSUING_GOAL.md
Hydration_Rehydration/NEXT_ACTION.md
```

Wave 58 may be marked complete as documentation/static-package complete only. It must not claim ComfyUI runtime, AWS runtime, generated image QA, generated video QA, or generated audio QA.
