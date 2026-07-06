# Blockers

No packaging blockers known.

## Current local validation blockers

None for Wave 59 live local directory/index validation. `ISSUE-W59-INDEX-001` was fixed and retested.

## Active blockers

- `BLOCKER-W59-GIT-001`
  - affected tracker IDs: `TRK-W59-004`, `TRK-W60-001`
  - blocker type: local_git_repository_missing
  - failed condition: `C:\Comfy_UI_Main` does not contain `.git`, so Git root, remote, branch, HEAD, working tree, and `.env` tracking status cannot be verified.
  - local filesystem involved: yes
  - GitHub involved: yes, but no network action was attempted.
  - fix already applied: root `.gitignore` and `.env.example` were created and validated.
  - best non-blocked next task: continue local non-Git validation, or explicitly select a dedicated Git recovery task to initialize/link/fetch safely.
  - evidence: `Plan/Instructions/QA/Evidence/Git_Verification/W59_W60_GIT_LOCAL_VERIFICATION_20260706T004200-0500.json`

- `BLOCKER-W62-ZIP-001`
  - affected tracker ID: `TRK-W62-009`
  - blocker type: local_cumulative_zip_missing
  - failed condition: no `.zip` file was found under `C:\Comfy_UI_Main`, so `Test-CumulativeWavePack.ps1` could not be run against a real cumulative pack.
  - local filesystem involved: yes
  - best non-blocked next task: continue local validation; run cumulative pack validation only after a real zip is restored or created.
  - evidence: `Plan/Instructions/QA/Evidence/Hydration_Helper_Static_Validation/W62_HYDRATION_HELPER_STATIC_VALIDATION_20260706T005425-0500.json`

## Runtime blockers to detect later

- Missing or invalid `.env`
- GitHub token missing or invalid
- AWS CLI not configured
- AWS account mismatch
- EC2 instance not found
- EC2 not using expected IAM profile
- Civitai API access unavailable
- Required model files missing
- ComfyUI runtime path mismatch
