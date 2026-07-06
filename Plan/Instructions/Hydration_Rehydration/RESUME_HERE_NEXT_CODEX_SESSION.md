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
- Inspected Plan, Items, Tracker, Instructions, Indexes, Operations, QA, and Hydration/Rehydration.
- Ran Wave 59 live local index regeneration after patching `Generate-Project-Indexes.ps1` for Windows PowerShell compatibility.
- Created and validated Wave 59 live index evidence and done certification.
- Ran secret-safe local Git verification. It is blocked because `C:\Comfy_UI_Main` has no `.git` directory.
- Created root `.gitignore` and `.env.example`; validated required secret/binary ignore coverage.
- Ran Wave 60 operations helper/schema/template local static validation and created done certification.
- Ran Wave 61 QA helper/schema/template local validation, generated sample QA/done-cert records, and created done certification.
- Ran Wave 62 hydration helper/template local validation, generated sample session state, and recorded cumulative zip validation as pending because no zip exists under `C:\Comfy_UI_Main`.

## Active blockers

- `BLOCKER-W59-GIT-001`: `C:\Comfy_UI_Main` is not a Git repository. Do not commit, push, pull, fetch, or initialize until a dedicated Git recovery decision is recorded.
- `BLOCKER-W62-ZIP-001`: no cumulative zip file exists under `C:\Comfy_UI_Main`; do not claim cumulative pack zip validation until a real zip is restored or created and tested.

## Current goal

Resolve `BLOCKER-W59-GIT-001` with a dedicated Git recovery preflight.

## Next exact action

Run read-only/redacted Git recovery diagnostics:

```powershell
Test-Path C:\Comfy_UI_Main\.git
Test-Path C:\Comfy_UI_Main\.gitignore
Test-Path C:\Comfy_UI_Main\.env
Test-Path C:\Comfy_UI_Main\.env.example
git -C C:\Comfy_UI rev-parse --show-toplevel
git -C C:\Comfy_UI config --get remote.origin.url
git -C C:\Comfy_UI status --short
```

Redact any token-like remote output before writing evidence. Do not mutate Git state yet.

## Tracker rows that changed

- `TRK-W59-002`: complete / qa_passed for live directory scan.
- `TRK-W59-003`: complete / qa_passed for live index regeneration.
- `TRK-W59-004`: blocked because `C:\Comfy_UI_Main` lacks `.git`.
- `TRK-W60-001`: blocked because live Git verification cannot run without `.git`.
- `TRK-W60-009`: implemented_pending_git / qa_passed for `.gitignore` and `.env.example`; `.env` tracking check awaits Git metadata.
- `TRK-W60-010`: complete / qa_passed for operations static validation.
- `TRK-W61-011`: complete / qa_passed for QA helper validation.
- `TRK-W62-003`: complete / qa_passed for session-state helper validation.
- `TRK-W62-009`: pending_validation / blocked_no_zip.

## Evidence created

- `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REGENERATION_20260706T003608-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W59_LIVE_INDEX_VALIDATION_20260706T003608-0500.md`
- `Plan/Instructions/QA/Evidence/Git_Verification/W59_W60_GIT_LOCAL_VERIFICATION_20260706T004200-0500.json`
- `Plan/Instructions/QA/Evidence/Operations_Static_Validation/W60_OPERATIONS_STATIC_VALIDATION_20260706T004632-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W60_OPERATIONS_STATIC_VALIDATION_20260706T004632-0500.md`
- `Plan/Instructions/QA/Evidence/QA_Helper_Static_Validation/W61_QA_HELPER_STATIC_VALIDATION_20260706T005111-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W61_QA_HELPER_STATIC_VALIDATION_20260706T005111-0500.md`
- `Plan/Instructions/QA/Evidence/Hydration_Helper_Static_Validation/W62_HYDRATION_HELPER_STATIC_VALIDATION_20260706T005425-0500.json`
- `Plan/Instructions/QA/Evidence/Done_Certifications/CERT_W62_SESSION_STATE_HELPER_VALIDATION_20260706T005425-0500.md`

## GitHub state

- `C:\Comfy_UI_Main` has no `.git` directory.
- `.env` exists locally.
- `.gitignore` and `.env.example` now exist and passed required pattern checks.
- No commit, push, pull, fetch, or Git initialization was performed.

## AWS/EC2 state

- EC2 was not started.
- No AWS CLI command was run.
- Expected idle state remains stopped, but live AWS identity/state validation is still pending.

## Civitai/model state

- No Civitai API call was made.
- No model download was performed.
- Model registry helper static smoke test passed using sample values only.

## Must not repeat

- Do not rerun completed Wave 59 index, Wave 60 operations, Wave 61 QA helper, or Wave 62 session-state helper validations unless their files change.
- Do not attempt Git commit/push/pull from `C:\Comfy_UI_Main` until `BLOCKER-W59-GIT-001` is resolved.
- Do not claim cumulative zip validation until a real zip file exists and `Test-CumulativeWavePack.ps1` passes against it.
