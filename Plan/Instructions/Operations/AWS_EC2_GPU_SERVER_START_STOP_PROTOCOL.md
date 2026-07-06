# AWS EC2 GPU Server Start / Stop Protocol

Wave: 60  
Purpose: Tell Codex Desktop exactly how to use the ComfyUI GPU server safely, only when needed, and return it to the expected stopped idle state.

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

## 1. Server role

The EC2 GPU server is a runtime validation machine for ComfyUI, GPU model tests, LoRA validation, workflow execution, asset compatibility checks, generated sample review, and heavy runtime QA.

The expected normal idle state is:

```text
stopped
```

Codex must not leave the instance running after work is complete unless a current validated task explicitly requires a continuing run.

## 2. Required identity constants

Codex must confirm all identity values before using the GPU server:

| Field | Required value |
|---|---|
| AWS Account | `029530099913` |
| EC2 Instance ID | `i-0560bf8d143f93bb1` |
| Name tag | `ComfyUI-LoRA-GPU-Server` |
| Instance type | `g5.xlarge` |
| IAM profile | `ComfyUI-SSM-Profile` |
| Attached EBS volume | `vol-0eb9b2c6d3d2706d6` |
| Volume size | `1024 GB` |
| Expected idle state | `stopped` |

If any value does not match, Codex must stop the operation, write an AWS identity mismatch record, and avoid running commands on the instance.

## 3. Required environment variables

Preferred `.env` keys:

```text
AWS_PROFILE=...
AWS_REGION=...
AWS_DEFAULT_REGION=...
```

If no region is present, Codex must discover the instance region from the existing project index or AWS config. It must not guess randomly.

Codex may use the AWS CLI, but it must not write AWS credentials into project files.

## 4. Preflight identity check

Run:

```powershell
aws sts get-caller-identity
```

Confirm Account equals:

```text
029530099913
```

Then run:

```powershell
aws ec2 describe-instances `
  --instance-ids i-0560bf8d143f93bb1 `
  --query "Reservations[0].Instances[0].{InstanceId:InstanceId,State:State.Name,Type:InstanceType,Name:Tags[?Key=='Name']|[0].Value,IamProfile:IamInstanceProfile.Arn,Volumes:BlockDeviceMappings[].Ebs.VolumeId,PublicIp:PublicIpAddress}" `
  --output json
```

Required checks:

- `InstanceId` equals `i-0560bf8d143f93bb1`
- `Type` equals `g5.xlarge`
- `Name` equals `ComfyUI-LoRA-GPU-Server`
- IAM profile ARN contains `ComfyUI-SSM-Profile`
- `Volumes` includes `vol-0eb9b2c6d3d2706d6`
- stopped state has no public IP

## 5. When Codex may start the instance

Start the instance only for:

- ComfyUI workflow runtime testing
- GPU dependency validation
- Flux / SDXL / Pony / video model load testing
- LoRA compatibility validation
- large model metadata-to-runtime verification
- visual sample generation needed for QA
- video generation sample testing
- audio/video sync or heavy processing test requiring GPU
- remote artifact validation that cannot reasonably run locally

Do not start EC2 for:

- editing Markdown
- updating tracker rows
- indexing files
- writing protocols
- local static validation
- Git-only sync
- simple JSON schema checks
- non-runtime planning

## 6. Start sequence

If state is `stopped`:

```powershell
aws ec2 start-instances --instance-ids i-0560bf8d143f93bb1
aws ec2 wait instance-running --instance-ids i-0560bf8d143f93bb1
aws ec2 wait instance-status-ok --instance-ids i-0560bf8d143f93bb1
```

After running, re-describe the instance:

```powershell
aws ec2 describe-instances --instance-ids i-0560bf8d143f93bb1 --output json
```

Then check SSM availability:

```powershell
aws ssm describe-instance-information `
  --filters "Key=InstanceIds,Values=i-0560bf8d143f93bb1" `
  --output json
```

If SSM is not ready, Codex may wait and retry with a bounded loop. It must not spin forever.

Recommended retry limit:

```text
10 attempts, 30 seconds apart
```

## 7. SSM-first access rule

Preferred command path:

```powershell
aws ssm send-command `
  --instance-ids i-0560bf8d143f93bb1 `
  --document-name "AWS-RunShellScript" `
  --comment "ComfyUI autonomous validation command" `
  --parameters commands="pwd","hostname","nvidia-smi"
```

Use interactive Session Manager only when Run Command is not enough:

```powershell
aws ssm start-session --target i-0560bf8d143f93bb1
```

Manual SSH is not the normal workflow. It is an exception path only after SSM failure has been logged and the tracker indicates SSH is allowed for a specific recovery step.

## 8. Runtime session structure

Every EC2 run must produce a run record:

```text
C:\Comfy_UI_Main\Plan\Instructions\Operations\Run_Records\aws_gpu_run_<timestamp>.json
```

Required fields:

```json
{
  "wave": "Wave60+",
  "task_id": "",
  "start_time_local": "",
  "end_time_local": "",
  "aws_account": "029530099913",
  "instance_id": "i-0560bf8d143f93bb1",
  "started_by": "Codex Desktop autonomous session",
  "start_state": "",
  "end_state": "",
  "commands_run": [],
  "artifacts_generated": [],
  "artifacts_pulled_back": [],
  "qa_reports": [],
  "stop_attempted": false,
  "stop_verified": false,
  "errors": []
}
```

## 9. Stop sequence

After runtime validation and artifact pullback:

```powershell
aws ec2 stop-instances --instance-ids i-0560bf8d143f93bb1
aws ec2 wait instance-stopped --instance-ids i-0560bf8d143f93bb1
aws ec2 describe-instances --instance-ids i-0560bf8d143f93bb1 --query "Reservations[0].Instances[0].State.Name" --output text
```

The final state must be:

```text
stopped
```

If stop fails, Codex must retry once, then log a high-priority issue in the tracker.

## 10. Cost-control behavior

Codex must track the runtime window. The instance should be stopped immediately after GPU work is done. If Codex loses task context while EC2 is running, the safe default is:

1. Pull back logs/artifacts if possible.
2. Stop the instance.
3. Record incomplete task state.
4. Rehydrate next session from the local run record.

## 11. Failure handling

| Failure | Action |
|---|---|
| AWS account mismatch | Do not proceed. Log identity mismatch. |
| Instance not found | Do not proceed. Verify region/profile. |
| Instance type mismatch | Do not proceed. Log mismatch. |
| Volume mismatch | Do not proceed until confirmed. |
| SSM unavailable | Retry bounded loop; use Session Manager only if available; SSH exception only if tracker authorizes. |
| GPU unavailable after start | Run `nvidia-smi`, capture logs, stop instance. |
| ComfyUI fails to launch | Capture logs, do not mark runtime test complete, stop instance. |
| Artifact pullback fails | Retry pullback; if still failing, preserve remote manifest and stop instance. |
| Stop fails | Retry once, log critical issue. |

## 12. Done gate

An EC2 runtime task is complete only when:

```text
[ ] AWS account verified
[ ] instance identity verified
[ ] instance started only if needed
[ ] SSM or command channel verified
[ ] intended runtime command executed
[ ] logs/artifacts captured
[ ] QA evidence generated where applicable
[ ] artifacts pulled back or pullback failure recorded
[ ] instance stopped
[ ] stopped state verified
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
