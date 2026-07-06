# Secrets and `.env` Handling Protocol

Wave: 60  
Purpose: Define how Codex Desktop should read, use, protect, and avoid leaking tokens/keys for GitHub, AWS, Civitai, and any future model or cloud service integrations.

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

## 1. Canonical secret file

Secrets are expected at:

```text
C:\Comfy_UI_Main\.env
```

Codex may read `.env` for runtime operations but must never copy secret values into generated Markdown, JSON reports, tracker rows, logs, screenshots, commit messages, command output, or Git remotes.

## 2. Allowed secret names

GitHub:

```text
GITHUB_TOKEN
GH_TOKEN
GITHUB_PAT
```

Civitai:

```text
CIVITAI_API_TOKEN
CIVITAI_TOKEN
CIVITAI_API_KEY
```

AWS:

```text
AWS_PROFILE
AWS_REGION
AWS_DEFAULT_REGION
AWS_ACCESS_KEY_ID
AWS_SECRET_ACCESS_KEY
AWS_SESSION_TOKEN
```

Other future services should follow:

```text
SERVICE_NAME_API_KEY
SERVICE_NAME_TOKEN
SERVICE_NAME_SECRET
```

## 3. `.env` loading rules

Codex may load `.env` into the current process only.

PowerShell loader pattern:

```powershell
Get-Content "C:\Comfy_UI_Main\.env" | ForEach-Object {
  if ($_ -match "^\s*#" -or $_ -match "^\s*$") { return }
  $parts = $_ -split "=", 2
  if ($parts.Count -eq 2) {
    [Environment]::SetEnvironmentVariable($parts[0].Trim(), $parts[1].Trim().Trim('"'), "Process")
  }
}
```

Codex must not print the loaded values.

## 4. Secret redaction

Before writing any command output to reports, apply redaction for patterns:

```text
ghp_[A-Za-z0-9_]+
github_pat_[A-Za-z0-9_]+
AKIA[0-9A-Z]{16}
ASIA[0-9A-Z]{16}
sk-[A-Za-z0-9_-]+
hf_[A-Za-z0-9_-]+
Bearer [A-Za-z0-9._-]+
AWS_SECRET_ACCESS_KEY=.* 
CIVITAI_API_TOKEN=.*
```

Replacement:

```text
[REDACTED_SECRET]
```

## 5. Git protection

`.gitignore` must include:

```gitignore
.env
*.env
.env.*
!.env.example
*.pem
*.key
*.p12
*.pfx
secrets/
private/
```

Before commit:

```powershell
git diff --cached --name-only
```

If `.env` or any secret file appears, unstage:

```powershell
git restore --staged .env
```

## 6. Reporting rule

Reports may say:

```text
CIVITAI_API_TOKEN present: yes
```

Reports must not say:

```text
CIVITAI_API_TOKEN=actual_value
```

## 7. Command history risk

Codex should avoid command forms that put tokens in command line arguments or URLs. Prefer headers or environment variables.

Prefer:

```powershell
$headers["Authorization"] = "Bearer $env:CIVITAI_API_TOKEN"
```

Avoid unless required and logged safely:

```powershell
https://example.com/download?token=$env:CIVITAI_API_TOKEN
```

## 8. AWS credentials

Preferred AWS authentication:

1. AWS profile already configured
2. SSO/session profile
3. environment variables loaded into process
4. instance role on EC2

Codex must not write AWS access keys into project files.

## 9. Secret leak response

If Codex detects a secret in a generated file:

1. Stop commit/push.
2. Remove secret from file.
3. Write redacted issue record.
4. Check Git status.
5. If already committed but not pushed, amend or reset safely.
6. If already pushed, record that token rotation is required externally.

Codex cannot rotate secrets by itself unless explicit credentials and instructions exist.

## 10. `.env.example`

Codex may create or update:

```text
C:\Comfy_UI_Main\.env.example
```

Example contents must contain placeholders only:

```env
GITHUB_TOKEN=
CIVITAI_API_TOKEN=
AWS_PROFILE=
AWS_REGION=
```

## 11. Done gate

Secret handling is complete only when:

```text
[ ] `.env` exists or absence is recorded
[ ] needed keys checked by presence only
[ ] no secret values printed
[ ] `.gitignore` protects secret files
[ ] staged files checked
[ ] reports redacted
[ ] tracker updated if any issue found
```

Reference sources checked for Wave 60 protocol drafting on 2026-07-06:
- AWS CLI EC2 describe-instances command reference
- AWS CLI EC2 start-instances / stop-instances command references
- AWS CLI EC2 waiter references for instance-running, instance-status-ok, and instance-stopped
- AWS Systems Manager send-command and Run Command references
- AWS Systems Manager start-session reference
- GitHub personal access token and REST API authentication documentation
- Civitai REST API reference migration notice and historical endpoint reference
