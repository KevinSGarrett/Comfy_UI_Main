# Resume Here - Next Codex Desktop Session

## First instruction

Start by reading this file, then re-open:

```text
Plan\Instructions\Hydration_Rehydration\SESSION_START_REHYDRATION_CHECKLIST.md
Plan\Instructions\Hydration_Rehydration\CURRENT_SESSION_STATE.md
Plan\Instructions\Hydration_Rehydration\CURRENT_PURSUING_GOAL.md
Plan\Instructions\Hydration_Rehydration\NEXT_ACTION.md
Plan\Instructions\Hydration_Rehydration\BLOCKERS.md
Plan\Instructions\Hydration_Rehydration\KNOWN_ISSUES.md
Plan\Instructions\Hydration_Rehydration\QA_EVIDENCE_INDEX.md
```

## Current session completed

- Rehydrated the Wave 58-62 instruction system.
- Ran Wave 59 live local index regeneration after patching `Generate-Project-Indexes.ps1` for Windows PowerShell compatibility.
- Created Wave 59 live index evidence and done certification.
- Created root `.gitignore` and `.env.example`; validated required secret/binary ignore coverage.
- Resolved the missing `.git` blocker by initializing Git in `C:\Comfy_UI_Main`, setting canonical origin, enabling LFS, committing, pushing, and verifying remote HEAD.
- Ran Wave 60 operations helper/schema/template local static validation and created done certification.
- Ran Wave 61 QA helper/schema/template local validation and created done certification.
- Ran Wave 62 hydration helper/template local validation and created done certification.
- Added Git LFS coverage for zip artifacts.
- Built `C:\Comfy_UI_Main\Comfy_UI_Main_Autonomous_Codex_Desktop_Waves58_62_Cumulative.zip` from tracked project files.
- Validated the cumulative zip with `Test-CumulativeWavePack.ps1`.
- Created Wave 62 cumulative pack validation evidence and done certification.
- Ran secret-safe readiness preflight. GitHub API, AWS account, EC2 identity, EBS volume, and Civitai metadata checks passed. Local ComfyUI runtime is absent.

## Active blockers

- `BLOCKER-RUNTIME-COMFYUI-LOCAL-001`: local `C:\Comfy_UI_Main\ComfyUI` runtime and model folders are absent. Use bounded EC2 runtime discovery after committing the readiness checkpoint.

## Current goal

Run bounded EC2 runtime discovery with SSM and stopped-state verification.

## Next exact action

Commit/push the readiness preflight checkpoint, then run EC2 discovery:

```powershell
git -C C:\Comfy_UI_Main status --branch --short
git -C C:\Comfy_UI_Main add Plan\Instructions
git -C C:\Comfy_UI_Main commit -m "Runtime: record readiness preflight"
git -C C:\Comfy_UI_Main push origin main
```

After the checkpoint is clean, start only `i-0560bf8d143f93bb1`, verify SSM, run minimal remote path/GPU discovery, stop the instance, and verify final state is `stopped`.

## Tracker rows that changed

- `TRK-W59-002`: complete / qa_passed for live directory scan.
- `TRK-W59-003`: complete / qa_passed for live index regeneration.
- `TRK-W59-004`: complete / qa_passed for Git repository verification.
- `TRK-W60-001`: complete / qa_passed for GitHub/local repository readiness.
- `TRK-W60-002`: complete / qa_passed for AWS identity, EC2 identity, and EBS volume preflight.
- `TRK-W60-005`: complete / qa_passed for Civitai authenticated metadata preflight.
- `TRK-W60-008`: local runtime blocker recorded because local ComfyUI model folders are absent.
- `TRK-W60-009`: complete / qa_passed for `.env` protection and Git status safety.
- `TRK-W60-010`: complete / qa_passed for operations static validation.
- `TRK-W61-006`: local runtime blocker recorded because local ComfyUI runtime is absent.
- `TRK-W61-007`: local model binary absence recorded.
- `TRK-W61-011`: complete / qa_passed for QA helper validation.
- `TRK-W62-003`: complete / qa_passed for session-state helper validation.
- `TRK-W62-009`: complete / qa_passed for cumulative pack zip validation.

## Evidence created

- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REGENERATION_20260706T003608-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_VALIDATION_20260706T003608-0500.md`
- `Plan/Instructions/QA/Evidence/Git_Verification/W59_W60_GIT_LOCAL_VERIFICATION_20260706T004200-0500.json`
- `Plan/Instructions/QA/Evidence/Git_Verification/W59_W60_GIT_RECOVERY_INITIAL_COMMIT_20260706T010603-0500.json`
- `Plan/Instructions/QA/Evidence/Git_Verification/W59_W60_GIT_RECOVERY_EVIDENCE_COMMIT_VERIFICATION_20260706T011016-0500.json`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_STATIC_VALIDATION_20260706T004632-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_OPERATIONS_STATIC_VALIDATION_20260706T004632-0500.md`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_STATIC_VALIDATION_20260706T005111-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_QA_HELPER_STATIC_VALIDATION_20260706T005111-0500.md`
- `Plan/Instructions/QA/Evidence/Hydration_Helper_Static_Validation/W62_HYDRATION_HELPER_STATIC_VALIDATION_20260706T005425-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W62_SESSION_STATE_HELPER_VALIDATION_20260706T005425-0500.md`
- `Plan/Instructions/QA/Evidence/Hydration_Helper_Static_Validation/W62_CUMULATIVE_PACK_VALIDATION_20260706T011548-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W62_CUMULATIVE_PACK_VALIDATION_20260706T011548-0500.md`
- `Plan/Instructions/QA/Evidence/Runtime_Readiness/W60_W61_RUNTIME_READINESS_PREFLIGHT_20260706T012301-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_W61_RUNTIME_READINESS_PREFLIGHT_20260706T012301-0500.md`

## GitHub state

- `C:\Comfy_UI_Main` is a Git repository on `main`.
- Local `main` was verified against `origin/main`.
- `.env` is ignored and untracked.
- Git LFS is enabled for oversized tracker CSVs and zip artifacts.
- Latest pushed checkpoint before readiness preflight: `3804bfc3a39d4cac6821105ff4859b988f910c75`.

## Package state

- Zip: `C:\Comfy_UI_Main\Comfy_UI_Main_Autonomous_Codex_Desktop_Waves58_62_Cumulative.zip`
- SHA-256: `82fbd1d2c8fcd452e9efb76e68105cb81467ec84efe0b94892f11af72b8ef4cf`
- Official validator: pass

## AWS/EC2 state

- EC2 was not started during readiness preflight.
- AWS account matched `029530099913`.
- Instance `i-0560bf8d143f93bb1` matched expected type/name/profile/volume and was `stopped`.
- Expected idle state remains stopped until bounded runtime discovery starts.

## Civitai/model state

- Civitai authenticated metadata endpoint returned HTTP 200 with one metadata item in readiness preflight.
- No model download was performed.
- No local model binaries were found.

## Must not repeat

- Do not rerun completed Wave 59 index, Wave 60 operations, Wave 61 QA helper, Wave 62 session-state helper, Wave 62 zip validation, or runtime readiness preflight unless their files change.
- Do not print token values from `.env`.
- Do not start any EC2 instance except `i-0560bf8d143f93bb1`.
- Do not leave EC2 running after discovery.
- Do not claim final project completion until runtime and artifact QA gates have direct evidence.
