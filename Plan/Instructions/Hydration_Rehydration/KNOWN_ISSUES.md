# Known Issues

## Packaging known issues

None known.

## Runtime validation still required

The final pack defines instructions and protocols. It does not prove live runtime execution has succeeded. Runtime validations must be performed by Codex Desktop inside `C:\Comfy_UI_Main\`.

## Fixed issues this session

- `ISSUE-W59-INDEX-001`: Wave 59 live index generator failed under Windows PowerShell because `[System.IO.Path]::GetRelativePath` was unavailable. Fixed by adding `Get-RelativePathCompat`; retest passed. Evidence: `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REGENERATION_20260706T003608-0500.json`.

## Active known issues

- `ISSUE-W59-GIT-001`: `C:\Comfy_UI_Main` is not currently a Git repository, so live Git remote/status verification is blocked. `.gitignore` and `.env.example` have been created and validated, but no Git push/pull/commit should be attempted from this folder until a dedicated Git recovery task is selected. Evidence: `Plan/Instructions/QA/Evidence/Git_Verification/W59_W60_GIT_LOCAL_VERIFICATION_20260706T004200-0500.json`.
- `ISSUE-W62-ZIP-001`: No cumulative zip file exists under `C:\Comfy_UI_Main`; cumulative pack tester parsed successfully but live pack validation is pending until a real zip is restored or created. Evidence: `Plan/Instructions/QA/Evidence/Hydration_Helper_Static_Validation/W62_HYDRATION_HELPER_STATIC_VALIDATION_20260706T005425-0500.json`.
