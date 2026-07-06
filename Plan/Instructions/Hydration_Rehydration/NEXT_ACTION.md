# Next Action

Run a secret-safe runtime readiness preflight:

```powershell
# Do not print .env values.
# Summarize required key presence only.

git -C C:\Comfy_UI_Main status --branch --short
git -C C:\Comfy_UI_Main ls-remote origin refs/heads/main

# If AWS CLI is available and credentials are configured:
aws sts get-caller-identity
aws ec2 describe-instances --instance-ids i-0560bf8d143f93bb1

# If a Civitai API key is present:
# Call a small metadata endpoint only; do not download models yet.
```

Keep EC2 stopped unless a later runtime gate explicitly requires GPU execution. Record pass/fail/blocked evidence for GitHub, AWS/EC2, Civitai, local ComfyUI path, workflow inventory, and model prerequisites.
