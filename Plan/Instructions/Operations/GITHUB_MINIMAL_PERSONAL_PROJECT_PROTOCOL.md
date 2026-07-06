# GitHub Minimal Personal Project Protocol

Wave: 60  
Purpose: Give Codex Desktop exact instructions for using GitHub as a lightweight personal-project checkpoint, backup, and synchronization layer for `Comfy_UI_Main`.

Project constants:
- Main local project: C:\Comfy_UI_Main\
- Plan directory: C:\Comfy_UI_Main\Plan
- Items directory: C:\Comfy_UI_Main\Plan\Items
- Tracker directory: C:\Comfy_UI_Main\Plan\Tracker
- Instructions directory: C:\Comfy_UI_Main\Plan\Instructions
- Operations directory: C:\Comfy_UI_Main\Plan\Instructions\Operations
- GitHub repo: https://github.com/KevinSGarrett/Comfy_UI_Main
- GitHub token location: C:\Comfy_UI_Main\.env
- AWS account: 029530099913
- EC2 instance ID: i-0560bf8d143f93bb1
- EC2 name tag: ComfyUI-LoRA-GPU-Server
- EC2 type: g5.xlarge
- IAM profile: ComfyUI-SSM-Profile
- Expected normal idle state: stopped
- Public IP when stopped: none
- Attached EBS volume: vol-0eb9b2c6d3d2706d6
- EBS volume size: 1024 GB

## 1. Operating principle

This repository is a personal project repository. Codex Desktop must use GitHub to preserve work, synchronize local and remote state, and create recoverable checkpoints. Codex does not need enterprise-style pull request ceremony unless a branch is useful to isolate risky work.

The repo is not a place to store secrets, raw tokens, private credentials, or temporary machine-only runtime data. The repo is a durable source-of-truth for project code, plans, registries, scripts, indexes, QA protocols, and validated instruction packs.

## 2. Canonical repo identity

Codex must treat the following as the canonical remote unless a future indexed instruction replaces it:

```text
https://github.com/KevinSGarrett/Comfy_UI_Main
```

Codex must verify the remote before pushing:

```powershell
cd C:\Comfy_UI_Main
git remote -v
git status --short
git branch --show-current
```

Expected normal remote names:

```text
origin  https://github.com/KevinSGarrett/Comfy_UI_Main
```

If the remote is missing, Codex may add it:

```powershell
git remote add origin https://github.com/KevinSGarrett/Comfy_UI_Main
```

If a different remote points to an unrelated repository, Codex must not push until it records the mismatch in the tracker and fixes the remote only when the local repository clearly belongs to this project.

## 3. Authentication

The GitHub token is expected in:

```text
C:\Comfy_UI_Main\.env
```

Allowed variable names, in preferred order:

```text
GITHUB_TOKEN
GH_TOKEN
GITHUB_PAT
```

Codex may load the token at runtime but must never print it, echo it, write it into logs, include it in Git remotes, commit it, or add it to any generated report.

Preferred authentication options:

1. Use Git Credential Manager already installed on the machine.
2. Use GitHub CLI if already authenticated.
3. Load token from `.env` into process environment only for the current command.
4. Use HTTPS credential helper rather than embedding a token into the URL.

Codex must not save a token into `.git/config`.

## 4. Required `.gitignore` coverage

Codex must maintain `.gitignore` so that it excludes at minimum:

```gitignore
.env
*.env
.env.*
!.env.example
*.pem
*.key
*.p12
*.pfx
id_rsa
id_ed25519
.aws/
aws_credentials*
secrets/
private/
ComfyUI/output/
ComfyUI/temp/
outputs/
temp/
tmp/
cache/
__pycache__/
*.pyc
*.log
*.tmp
*.part
*.download
*.safetensors
*.ckpt
*.pt
*.pth
*.onnx
*.bin
*.gguf
*.mp4
*.mov
*.avi
*.wav
*.flac
*.mp3
```

Model files and generated media can be large and should usually live in local storage, S3, EBS, or a dedicated artifact path. The repo should store registries and metadata about models, not the model binaries themselves.

## 5. When Codex should commit

Codex should commit after a meaningful verified checkpoint, not after every small edit.

Commit when one of these is true:

| Situation | Commit? | Requirement |
|---|---:|---|
| Instruction/protocol wave completed and static validation passes | Yes | Include delivery report and validation report |
| Tracker/items/index files updated after verified work | Yes | Include tracker supplement and item supplement |
| Script created and dry-run/static validation passes | Yes | Include usage documentation |
| Runtime workflow tested and QA evidence exists | Yes | Include QA report/manifest only, not giant output binaries unless explicitly intended |
| Partially broken experiment | Usually no | Record in issue log; commit only if preserving a deliberate WIP branch |
| Secrets accidentally detected | No | Remove secret first; rotate externally if exposure happened |

## 6. Minimal branch strategy

Default branch:

```text
main
```

Preferred default for routine autonomous development:

```powershell
git pull --ff-only origin main
# edit files
git status --short
git add <safe files>
git commit -m "Wave XX: concise verified checkpoint"
git push origin main
```

Use a short-lived branch only for risky changes:

```powershell
git switch -c wave60-operations-protocols
# work and validate
git push -u origin wave60-operations-protocols
```

For this personal project, Codex may merge locally after validation:

```powershell
git switch main
git pull --ff-only origin main
git merge --ff-only wave60-operations-protocols
git push origin main
```

If fast-forward merge is not possible, Codex must inspect conflicts and resolve only project files it understands.

## 7. Pre-commit secret and binary guard

Before any commit, Codex must run a guard equivalent to:

```powershell
git status --short
git diff --cached --name-only
```

Reject staged files when any path matches:

```text
.env
*.pem
*.key
*.p12
*.pfx
*.safetensors
*.ckpt
*.pt
*.pth
*.onnx
*.bin
*.gguf
```

Codex must scan staged text for likely secrets:

```text
AKIA
ASIA
ghp_
github_pat_
sk-
hf_
CIVITAI
AWS_SECRET_ACCESS_KEY
PRIVATE KEY
```

If found, unstage and log the issue:

```powershell
git restore --staged <file>
```

## 8. Sync workflow

At session start:

```powershell
cd C:\Comfy_UI_Main
git status --short
git fetch origin
git status -sb
```

If local changes exist, Codex must identify whether they are known from the tracker. If unknown, Codex must inventory them before pulling.

When clean:

```powershell
git pull --ff-only origin main
```

Before EC2 work, push a verified local checkpoint so the EC2 server can pull the same state:

```powershell
git add <verified project files>
git commit -m "Wave XX: prepare EC2 validation checkpoint"
git push origin main
```

On EC2, use SSM to pull:

```bash
cd /path/to/Comfy_UI_Main
git fetch origin
git checkout main
git pull --ff-only origin main
```

## 9. Conflict handling

If `git pull --ff-only` fails:

1. Run `git status -sb`.
2. Save current state to a local patch:
   ```powershell
   git diff > C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\last_conflict_local_diff.patch
   ```
3. Inspect changed files.
4. Prefer preserving local tracker/instruction updates if they are newer and validated.
5. Do not delete files unless tracker/index confirms they are obsolete.
6. Record conflict and resolution in the tracker supplement.

## 10. Commit message format

Use direct, searchable messages:

```text
Wave 60: add GitHub AWS EC2 Civitai operations protocols
Wave 60: add EC2 start stop helper scripts
Wave 60: update model registry schema and download templates
```

Avoid vague messages:

```text
update
fix
changes
stuff
```

## 11. Verification before marking GitHub task done

A GitHub sync task is complete only when:

- local `git status --short` has no unintended changes
- remote URL matches the canonical repo
- latest commit includes only intended files
- no secrets or model binaries are staged
- push succeeded or the reason it did not push is recorded
- tracker is updated with commit hash and validation state

Record the commit hash:

```powershell
git rev-parse HEAD
```

## 12. Recovery rules

If Git is broken:

1. Do not delete `.git`.
2. Run:
   ```powershell
   git status
   git remote -v
   git branch -vv
   ```
3. Save any local work into:
   ```text
   C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\recovery_git_diff_<timestamp>.patch
   ```
4. If a file is missing from local but exists in GitHub, restore it from `origin/main`.
5. If GitHub is unavailable, continue local work and write a pending-sync record.

## 13. GitHub done gate

Codex may declare a GitHub operation done only after:

```text
[ ] remote verified
[ ] branch verified
[ ] pull/fetch state understood
[ ] safe files staged
[ ] secret scan passed
[ ] commit completed when needed
[ ] push completed when needed
[ ] tracker updated
[ ] hydration state updated
```

Reference sources checked for Wave 60 protocol drafting on 2026-07-06:
- AWS CLI EC2 describe-instances command reference
- AWS CLI EC2 start-instances / stop-instances command references
- AWS CLI EC2 waiter references for instance-running, instance-status-ok, and instance-stopped
- AWS Systems Manager send-command and Run Command references
- AWS Systems Manager start-session reference
- GitHub personal access token and REST API authentication documentation
- Civitai REST API reference migration notice and historical endpoint reference
