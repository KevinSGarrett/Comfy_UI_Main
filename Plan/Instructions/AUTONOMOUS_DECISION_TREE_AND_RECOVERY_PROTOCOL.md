<!--
Wave 58 — Autonomous Instruction Manual + AI Project Manager Brain
Target path after extraction: C:\Comfy_UI_Main\Plan\Instructions
This file is designed for Codex Desktop autonomous operation.
-->

# AUTONOMOUS_DECISION_TREE_AND_RECOVERY_PROTOCOL

## 1. Purpose

This protocol tells Codex Desktop what to do when the project state is unclear, files are missing, paths are broken, tests fail, QA fails, AWS is unavailable, Civitai fails, GitHub sync fails, or tracker state is inconsistent.

The rule is: diagnose, record evidence, recover safely, and continue making autonomous progress.

## 2. Universal recovery pattern

For any failure:

```text
1. Stop the failing action.
2. Preserve the error/output/log.
3. Classify the failure.
4. Identify the smallest affected unit.
5. Check source-of-truth files.
6. Choose a safe recovery.
7. Run focused validation.
8. Update pursuing goal.
9. Update tracker/issue log.
10. Continue or reroute.
```

## 3. Failure classification

Codex must classify failures as one of:

```text
MISSING_FILE
MISSING_DIRECTORY
BROKEN_PATH
BROKEN_REFERENCE
SCHEMA_INVALID
JSON_INVALID
CSV_INVALID
MARKDOWN_INVALID
GIT_DIRTY_OR_CONFLICTED
GITHUB_AUTH_OR_REMOTE_FAILURE
AWS_IDENTITY_MISMATCH
AWS_INSTANCE_STATE_FAILURE
AWS_SSM_FAILURE
AWS_COST_RISK
CIVITAI_API_FAILURE
CIVITAI_MODEL_METADATA_MISSING
MODEL_FILE_MISSING
MODEL_COMPATIBILITY_FAILURE
COMFYUI_NODE_MISSING
COMFYUI_WORKFLOW_INVALID
COMFYUI_RUNTIME_FAILURE
VRAM_OR_RESOURCE_FAILURE
IMAGE_QA_FAILURE
VIDEO_QA_FAILURE
AUDIO_QA_FAILURE
PROMPT_COMPLIANCE_FAILURE
TRACKER_CONFLICT
ITEM_LIST_CONFLICT
HYDRATION_STALE
UNKNOWN_BLOCKER
```

## 4. Decision tree: unclear task state

If Codex does not know what to do next:

1. Read `CURRENT_SESSION_STATE.md`.
2. Read `CURRENT_PURSUING_GOAL.md`.
3. Read latest tracker summary.
4. Read latest itemized list summary.
5. Read latest wave delivery report.
6. Check Git status.
7. Identify incomplete active wave deliverables.
8. Select the smallest unblocked task.
9. Write the next action.
10. Continue.

If still unclear:
- create `UNKNOWN_BLOCKER` evidence
- do not mark anything complete
- select a safe source-of-truth indexing or validation task

## 5. Decision tree: missing file

If a required file is missing:

```text
1. Search the expected directory.
2. Search related Plan subdirectories.
3. Search Git working tree.
4. Search manifests/file indexes.
5. Search prior wave package if mounted/extracted.
6. If source content exists elsewhere, recreate or copy safely.
7. If not recoverable, create a placeholder only if it is explicitly marked NOT_VERIFIED.
8. Add issue log entry.
9. Update tracker.
```

Never silently invent runtime evidence.

## 6. Decision tree: broken path

If a path is broken:

```text
1. Confirm whether the path is Windows local, repo-relative, EC2 remote, or generated artifact.
2. Normalize slashes only where safe.
3. Check whether the directory exists.
4. Check whether the path should be created by the current task.
5. Update path mapping/index if a better canonical path exists.
6. Run a path validation check.
7. Record fix evidence.
```

## 7. Decision tree: failed static validation

Static validation includes Markdown existence, JSON parse, CSV parse, schema checks, path checks, and reference checks.

If static validation fails:

```text
1. Identify exact file and line/field if possible.
2. Fix the smallest error.
3. Rerun the same validation once.
4. If still failing, run a narrower validation.
5. If still failing, classify root cause and reroute.
6. Do not run runtime/GPU tests until static validation passes.
```

## 8. Decision tree: failed runtime/ComfyUI validation

If ComfyUI or a script fails at runtime:

```text
1. Preserve logs.
2. Check missing node/model/path first.
3. Check engine compatibility.
4. Check VRAM/resource failure.
5. Check input/output contracts.
6. Run smallest workflow or smoke test.
7. Apply one targeted fix.
8. Rerun once.
9. If still failing, log blocker and create a smaller debug item.
```

## 9. Decision tree: visual QA failure

If generated image QA fails:

```text
1. Preserve failed output.
2. Score and classify failure.
3. Identify target area:
   face, eyes, hands, body, pose, skin, fabric, contact, lighting, background, style, anatomy, prompt compliance.
4. Determine likely cause:
   prompt issue, model issue, LoRA issue, ControlNet issue, mask issue, sampler issue, resolution issue, refiner issue, postprocess issue.
5. Create targeted fix.
6. Regenerate with controlled seed/change when useful.
7. Re-score.
8. Record before/after evidence.
```

## 10. Decision tree: video QA failure

If generated video/GIF QA fails:

```text
1. Preserve video and sampled frames.
2. Identify failure:
   flicker, identity drift, anatomy drift, motion discontinuity, contact inconsistency, object permanence issue, compression issue, loop seam, sync issue.
3. Sample key frames and failure frames.
4. Determine likely cause:
   weak reference, bad temporal settings, bad interpolation, inconsistent prompt, model mismatch, excessive denoise, missing control signal.
5. Apply targeted fix.
6. Re-render minimal segment if possible.
7. Re-score temporal QA.
```

## 11. Decision tree: audio QA failure

If generated audio QA fails:

```text
1. Preserve audio.
2. Inspect waveform/loudness when tools are available.
3. Identify failure:
   clipping, noise, distortion, robotic voice, bad pacing, pronunciation, silence, sync, mix imbalance.
4. Determine likely cause:
   TTS settings, source text, voice model, normalization, compression, muxing, sample rate, bad edit.
5. Apply targeted fix.
6. Re-export a small test.
7. Re-score audio QA.
```

## 12. Decision tree: GitHub failure

If GitHub sync fails:

```text
1. Do not expose secrets.
2. Check git status.
3. Check current branch.
4. Check remote URL.
5. Check whether `.env` or secrets are staged; unstage them.
6. Pull/rebase only if safe.
7. Commit local validated work if appropriate.
8. Retry push once.
9. If remote auth fails, log blocker and continue local work.
```

For this personal project, Codex may use simple direct commits after validation. PR-heavy process is not required unless later instructions change this.

## 13. Decision tree: AWS/EC2 failure

Before any AWS work, Codex must verify:

```text
Account: 029530099913
Instance: i-0560bf8d143f93bb1
Name: ComfyUI-LoRA-GPU-Server
Type: g5.xlarge
IAM Profile: ComfyUI-SSM-Profile
Expected idle state: stopped
EBS Volume: vol-0eb9b2c6d3d2706d6
Volume size: 1024 GB
```

If AWS fails:

```text
1. Do not perform destructive actions.
2. Verify identity and region.
3. Verify instance state.
4. Verify SSM connectivity.
5. Verify instance is needed for current task.
6. If not needed, skip AWS.
7. If needed but unavailable, log blocker and continue local/static work.
8. If started successfully, run required GPU work only.
9. Pull back evidence.
10. Stop instance when complete.
```

## 14. Decision tree: Civitai failure

If Civitai model lookup/download fails:

```text
1. Preserve request metadata without secrets.
2. Check model URL/model ID/version ID.
3. Check whether model already exists locally.
4. Check whether metadata can be recovered from existing registry.
5. Retry safely.
6. If still failing, create pending model registry row.
7. Continue with compatible fallback model if task allows.
```

## 15. Decision tree: tracker/items conflict

If the tracker says one thing and files show another:

```text
1. Do not pick one silently.
2. Record conflict.
3. Check evidence paths.
4. Check latest validation report.
5. Check latest Git diff/commit.
6. Determine actual proof level.
7. Set status to the lowest defensible proof state.
8. Add next action to resolve.
```

Example:
If tracker says complete but no validation report exists, downgrade to `IMPLEMENTED_NOT_VERIFIED` or `READY_FOR_CERTIFICATION` depending on evidence.

## 16. Decision tree: hydration stale

If hydration files are outdated:

```text
1. Preserve old hydration as historical evidence.
2. Rebuild state from tracker, items, reports, manifests, and Git.
3. Write corrected CURRENT_SESSION_STATE.md.
4. Write corrected NEXT_ACTION.md.
5. Continue.
```

## 17. Escalation without human work

When a blocker cannot be resolved autonomously:

1. Mark it `BLOCKED_EXTERNAL_RESOURCE` or another accurate status.
2. Include exact evidence and failed attempts.
3. State what would be needed later.
4. Continue with the next unblocked task.

Do not stop the entire project because one external dependency failed.

## 18. Recovery done criteria

A recovery action is complete only when:
- failure is classified
- evidence is saved
- tracker/issue log is updated
- a fix was validated or a blocker was recorded
- next action is clear
