# Local Repository Bootstrap Plan

## Target

Create `C:\Comfy_UI_Main` as the structured local working repository connected to `https://github.com/KevinSGarrett/Comfy_UI_Main`.

## Step sequence for AI project manager

1. Check whether `C:\Comfy_UI_Main` exists.
2. If absent, clone the GitHub repository.
3. If present, verify it is a Git repo and has the expected remote.
4. Create required folders.
5. Add `.gitignore` that excludes models, outputs, secrets, generated media, caches, and huge binaries.
6. Add schemas, registries, scripts, docs, and workflow templates.
7. Run local validation.
8. Commit only lightweight project files.
9. Never commit model binaries or private references.

## Required repo bootstrap acceptance criteria

- `git status` clean after intentional commit.
- No files over 50 MiB unless explicitly approved and tracked by LFS policy.
- No secrets committed.
- No model binaries committed.
- Local validation passes.
- README explains local/EC2/S3 split.
