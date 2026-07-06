# Wave 37 Organization Handoff

## What to do next locally
1. Create the canonical local root directory.
2. Move files only by migration manifest.
3. Separate repo files from runtime/generation files.
4. Register workflows in the workflow catalog.
5. Register models/LoRAs/assets in the asset catalog.
6. Regenerate the file catalog after every large move.
7. Run Wave37 organization validation after each structural change.
8. Keep final renders blocked until preview QA/preflight proof passes.

## Validation command

```powershell
powershell -ExecutionPolicy Bypass -File .\07_IMPLEMENTATION\templates\powershell\Run-Wave37-OrganizationValidation.ps1 -Root "."
```
