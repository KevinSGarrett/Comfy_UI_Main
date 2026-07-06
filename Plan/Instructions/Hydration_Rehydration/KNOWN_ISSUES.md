# Known Issues

## Packaging known issues

None known.

## Runtime validation still required

The final pack defines instructions and protocols. It does not prove live runtime execution has succeeded. Runtime validations must be performed by Codex Desktop inside `C:\Comfy_UI_Main\`.

## Fixed issues this session

- `ISSUE-W59-INDEX-001`: Wave 59 live index generator failed under Windows PowerShell because `[System.IO.Path]::GetRelativePath` was unavailable. Fixed by adding `Get-RelativePathCompat`; retest passed. Evidence: `Plan/Instructions/QA/Evidence/Index_Validation/W59_LIVE_INDEX_REGENERATION_20260706T003608-0500.json`.
- `ISSUE-W59-GIT-001`: `C:\Comfy_UI_Main` was not a Git repository. Resolved by initializing Git metadata, adding canonical origin, enabling LFS, committing, pushing `main`, and verifying remote HEAD. Evidence: `Plan/Instructions/QA/Evidence/Git_Verification/W59_W60_GIT_RECOVERY_INITIAL_COMMIT_20260706T010603-0500.json`.
- `ISSUE-W62-ZIP-001`: No cumulative zip file existed under `C:\Comfy_UI_Main`. Resolved by building `Comfy_UI_Main_Autonomous_Codex_Desktop_Waves58_62_Cumulative.zip` from tracked project files and passing the official cumulative pack validator. Evidence: `Plan/Instructions/QA/Evidence/Hydration_Helper_Static_Validation/W62_CUMULATIVE_PACK_VALIDATION_20260706T011548-0500.json`.

## Active known issues

None currently known for local Wave 58-62 static and packaging validation.
