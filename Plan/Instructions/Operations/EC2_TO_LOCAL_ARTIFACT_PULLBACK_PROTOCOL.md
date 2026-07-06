# EC2 to Local Artifact Pullback Protocol

Wave: 60  
Purpose: Define how Codex Desktop retrieves generated outputs, logs, screenshots, QA artifacts, validation records, and runtime evidence from EC2 back to the local project after GPU testing.

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

## 1. Pullback rule

Every EC2 runtime session must produce evidence locally before the task can be marked complete.

Evidence includes:

- runtime command log
- ComfyUI console log
- workflow execution log
- generated sample outputs
- screenshots where relevant
- QA review notes
- model load results
- VRAM/GPU telemetry
- error traces
- final EC2 stop verification

## 2. Preferred pullback path

Preferred path:

```text
EC2 artifact folder → S3 staging path → Local C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts\<run_id>\
```

Alternative path:

```text
EC2 artifact folder → GitHub only for small text reports
```

Do not commit large media output to GitHub unless it is a deliberate small evidence sample and not excluded by `.gitignore`.

## 3. Required EC2 artifact manifest

Before pullback, Codex must generate a remote manifest on EC2:

```json
{
  "run_id": "aws_gpu_run_YYYYMMDD_HHMMSS",
  "instance_id": "i-0560bf8d143f93bb1",
  "artifact_root": "",
  "created_at": "",
  "files": [
    {
      "relative_path": "",
      "size_bytes": 0,
      "sha256": "",
      "artifact_type": "log|image|video|audio|json|workflow|report|other",
      "qa_required": true
    }
  ]
}
```

Remote Linux example:

```bash
cd /path/to/artifacts
find . -type f -print0 | while IFS= read -r -d '' f; do
  sha256sum "$f"
done
```

## 4. Artifact categories

| Category | Pull back? | Local destination |
|---|---:|---|
| ComfyUI logs | Yes | `Plan\Instructions\Operations\Pulled_Back_Artifacts\<run_id>\logs` |
| Runtime JSON reports | Yes | `...\reports` |
| Generated images for QA | Yes | `...\images` |
| Generated videos for QA | Yes | `...\videos` |
| Generated audio for QA | Yes | `...\audio` |
| Temporary cache | No | Do not pull unless needed for debugging |
| Model binaries | Usually no | Keep on EC2/EBS or model storage; pull only metadata/hash |
| Failed partial downloads | No | Log and delete/retry |

## 5. S3 staging pullback

EC2 upload:

```bash
aws s3 sync /path/to/artifacts s3://<bucket>/comfy-ui-main/pullback/<run_id>/ --only-show-errors
```

Local download:

```powershell
aws s3 sync s3://<bucket>/comfy-ui-main/pullback/<run_id>/ C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts\<run_id>\ --only-show-errors
```

Codex must verify file count and hashes after local download.

## 6. Local pullback record

Write:

```text
C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts\<run_id>\PULLBACK_RECORD.json
```

Required fields:

```json
{
  "run_id": "",
  "source_instance": "i-0560bf8d143f93bb1",
  "source_artifact_root": "",
  "s3_prefix": "",
  "local_destination": "",
  "file_count_remote": 0,
  "file_count_local": 0,
  "hashes_verified": false,
  "qa_required_files": [],
  "qa_completed_files": [],
  "errors": []
}
```

## 7. Pullback before stop

Preferred order:

1. Finish runtime command.
2. Create remote artifact manifest.
3. Upload/pull back artifacts.
4. Verify local count/hash.
5. Stop EC2.
6. Verify stopped state.
7. Update tracker and hydration state.

If pullback is failing and EC2 has been running too long, Codex must prioritize preserving remote manifest and stopping EC2. Then it can resume pullback later.

## 8. QA routing after pullback

Pulled-back artifacts must be routed:

| Artifact | Required next file/protocol |
|---|---|
| Image samples | `QA/IMAGE_GENERATION_VISUAL_REVIEW_PROTOCOL.md` |
| Video samples | `QA/VIDEO_GENERATION_REVIEW_PROTOCOL.md` |
| Audio samples | `QA/AUDIO_GENERATION_REVIEW_PROTOCOL.md` |
| Workflow logs | `QA/COMFYUI_WORKFLOW_TESTING_PROTOCOL.md` |
| Model load logs | `Operations/MODEL_DOWNLOAD_AND_REGISTRY_UPDATE_PROTOCOL.md` |
| Runtime failures | `Operations/AWS_EC2_GPU_SERVER_START_STOP_PROTOCOL.md` + tracker issue |

## 9. Failure handling

| Failure | Response |
|---|---|
| S3 upload fails | Retry once, then generate compressed manifest/log bundle if possible |
| Local download fails | Retry once, then keep S3 prefix and log pending pullback |
| Hash mismatch | Re-download file; if mismatch persists, mark artifact corrupted |
| Media missing | Runtime test incomplete unless artifact is optional |
| EC2 stop pending | Stop after preserving enough evidence |

## 10. Done gate

Artifact pullback is complete only when:

```text
[ ] remote artifact manifest created
[ ] artifacts copied or failure documented
[ ] local pullback record created
[ ] file count verified
[ ] hashes verified for required files
[ ] QA queue updated
[ ] EC2 stopped or stop failure logged
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
