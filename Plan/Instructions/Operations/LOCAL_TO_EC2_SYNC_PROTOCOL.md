# Local to EC2 Sync Protocol

Wave: 60  
Purpose: Define how Codex Desktop moves verified project changes from `C:\Comfy_UI_Main\` to the EC2 GPU server without making manual SSH the normal workflow.

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

## 1. Sync philosophy

Local development and planning happen in:

```text
C:\Comfy_UI_Main\
```

The EC2 server is primarily a runtime validation machine. Codex should not use the EC2 machine as the planning source-of-truth. The local project and GitHub repository remain the source-of-truth for instructions, trackers, indexes, scripts, schemas, and registries.

Preferred sync path:

```text
Local verified checkpoint → GitHub push → EC2 SSM command → git pull on EC2
```

Secondary sync path for large files/artifacts:

```text
Local file manifest → S3 staging bucket/path → EC2 SSM command → aws s3 sync on EC2
```

Manual SSH/SCP is exception-only.

## 2. What should sync through GitHub

Use GitHub for:

- project scripts
- Markdown instruction files
- JSON schemas
- registries
- tracker supplements
- itemized-list supplements
- validation reports
- small metadata files
- workflow JSON files if size is reasonable
- index/catalogue files

Do not sync through GitHub:

- `.env`
- credential files
- model binaries
- generated videos
- generated audio
- large image batches
- temp/cache folders
- partial downloads
- large ComfyUI outputs unless intentionally committed as small QA examples

## 3. Pre-sync local validation

Before sync:

```powershell
cd C:\Comfy_UI_Main
git status --short
```

Codex must ensure:

```text
[ ] no untracked secret files
[ ] no model binaries staged
[ ] no generated media accidentally staged
[ ] current tracker status is updated
[ ] current goal/pursuing goal text is current
[ ] local validation reports exist for files being synced
```

## 4. GitHub checkpoint sync

```powershell
cd C:\Comfy_UI_Main
git fetch origin
git pull --ff-only origin main
git add <verified files only>
git commit -m "Wave XX: verified checkpoint before EC2 runtime validation"
git push origin main
git rev-parse HEAD
```

Record the commit hash in:

```text
C:\Comfy_UI_Main\Plan\Instructions\Operations\Run_Records\sync_<timestamp>.json
```

## 5. EC2 pull via SSM

After EC2 is started and SSM is ready:

```powershell
aws ssm send-command `
  --instance-ids i-0560bf8d143f93bb1 `
  --document-name "AWS-RunShellScript" `
  --comment "Pull latest Comfy_UI_Main checkpoint" `
  --parameters commands="cd /path/to/Comfy_UI_Main && git fetch origin && git checkout main && git pull --ff-only origin main && git rev-parse HEAD"
```

Codex must replace `/path/to/Comfy_UI_Main` with the actual EC2 repo path from the AWS/EC2 directory index once Wave 59/60 live discovery confirms it.

If the remote path is unknown, Codex must use SSM to locate it:

```bash
find / -maxdepth 5 -type d -name ".git" 2>/dev/null | grep Comfy_UI_Main
```

Then write the discovered path into the EC2 index.

## 6. S3 staging for large runtime assets

Use S3 staging when a file is too large or inappropriate for GitHub but needed on EC2.

Suggested staging pattern:

```text
s3://<project-artifact-bucket>/comfy-ui-main/staging/local-to-ec2/<timestamp>/
```

Codex must discover the real bucket from project config or AWS index. If no bucket exists, Codex may create a plan item for bucket creation but must not invent a bucket name as if it exists.

S3 sync example:

```powershell
aws s3 sync C:\Comfy_UI_Main\staging\local_to_ec2\ s3://<bucket>/comfy-ui-main/staging/local-to-ec2/<timestamp>/ --only-show-errors
```

EC2 pull example:

```bash
aws s3 sync s3://<bucket>/comfy-ui-main/staging/local-to-ec2/<timestamp>/ /path/to/Comfy_UI_Main/staging/local_to_ec2/ --only-show-errors
```

## 7. Required sync manifest

Every sync must create a manifest:

```json
{
  "sync_id": "local_to_ec2_YYYYMMDD_HHMMSS",
  "direction": "local_to_ec2",
  "source": "C:\\Comfy_UI_Main",
  "target": "EC2:i-0560bf8d143f93bb1",
  "method": "github|s3|hybrid",
  "git_commit": "",
  "s3_prefix": "",
  "files": [
    {
      "relative_path": "",
      "size_bytes": 0,
      "sha256": "",
      "purpose": "",
      "expected_remote_path": ""
    }
  ],
  "validation": {
    "local_preflight_passed": false,
    "remote_pull_passed": false,
    "remote_hash_check_passed": false
  },
  "errors": []
}
```

## 8. Hash verification

For each non-GitHub staged file, Codex must compute local hash:

```powershell
Get-FileHash <path> -Algorithm SHA256
```

On EC2:

```bash
sha256sum <path>
```

Mismatch means the sync failed and the runtime test cannot proceed.

## 9. What to do if EC2 has uncommitted changes

Before pulling on EC2:

```bash
git status --short
```

If EC2 has uncommitted changes:

1. Create a remote patch:
   ```bash
   git diff > /tmp/ec2_uncommitted_<timestamp>.patch
   ```
2. Copy or upload the patch to artifact storage.
3. Do not overwrite unknown changes.
4. Record the issue.
5. Continue only if changes are known generated outputs that should be ignored.

## 10. Done gate

Local-to-EC2 sync is complete only when:

```text
[ ] local source verified
[ ] GitHub checkpoint pushed if using GitHub
[ ] EC2 identity verified
[ ] EC2 repo path known
[ ] EC2 pull or S3 sync executed
[ ] hash/commit verified
[ ] sync manifest written
[ ] tracker updated
```

Reference sources checked for Wave 60 protocol drafting on 2026-07-06:
- AWS CLI EC2 describe-instances command reference
- AWS CLI EC2 start-instances / stop-instances command references
- AWS CLI EC2 waiter references for instance-running, instance-status-ok, and instance-stopped
- AWS Systems Manager send-command and Run Command references
- AWS Systems Manager start-session reference
- GitHub personal access token and REST API authentication documentation
- Civitai REST API reference migration notice and historical endpoint reference
