# Model Download and Registry Update Protocol

Wave: 60  
Purpose: Provide Codex Desktop with exact rules for downloading model assets, preventing duplicates, validating files, and updating the model registry/catalogue.

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

## 1. Registry purpose

The model registry is the authoritative inventory of what model files exist, where they live, what they are compatible with, why they were added, and whether they passed runtime/QA validation.

A model file that exists on disk but is not registered is not considered project-ready.

## 2. Suggested registry locations

Primary registry path:

```text
C:\Comfy_UI_Main\Plan\Registries\Models\model_registry.jsonl
```

Supplemental registry files:

```text
C:\Comfy_UI_Main\Plan\Registries\Models\model_registry_index.md
C:\Comfy_UI_Main\Plan\Registries\Models\model_registry_validation_report.json
C:\Comfy_UI_Main\Plan\Registries\Models\model_duplicate_report.json
C:\Comfy_UI_Main\Plan\Registries\Models\model_runtime_validation_queue.csv
```

If these directories do not exist, Codex may create them.

## 3. Required registry record fields

Each model record must include:

```json
{
  "registry_schema_version": "1.0",
  "record_id": "",
  "created_at": "",
  "updated_at": "",
  "source": "civitai|manual|local|github|huggingface|other",
  "source_url": "",
  "source_model_id": "",
  "source_model_version_id": "",
  "model_name": "",
  "model_type": "",
  "base_model": "",
  "version_name": "",
  "file_name": "",
  "file_extension": "",
  "file_size_bytes": 0,
  "sha256": "",
  "source_hashes": {},
  "local_path": "",
  "storage_location": "local|ec2|s3|external",
  "workflow_lane": "",
  "compatibility_status": "candidate|compatible|incompatible|needs_runtime_validation|rejected",
  "compatible_engines": [],
  "trigger_words": [],
  "intended_use": "",
  "prompt_notes": "",
  "negative_prompt_notes": "",
  "qa_status": "not_tested|passed|failed|needs_review",
  "runtime_validation_status": "not_run|queued|passed|failed",
  "visual_impact": "",
  "video_impact": "",
  "audio_impact": "",
  "known_issues": [],
  "last_tested_at": "",
  "evidence_paths": []
}
```

## 4. Download staging

All downloads must go through staging:

```text
C:\Comfy_UI_Main\Models_Staging\
```

Suggested structure:

```text
Models_Staging\
  civitai\
    metadata\
    downloads\
    partial\
    rejected\
    manifests\
```

Do not write directly into ComfyUI model folders until download verification passes.

## 5. Duplicate prevention

Before download, compare against registry using:

- source model ID
- source model version ID
- file hash
- file name
- base model
- model type
- semantic name similarity

If exact hash exists:

```text
do not download
```

If same model ID but newer version:

```text
create new version record only if the newer version is needed
```

If same file name but unknown hash:

```text
download to staging, hash, compare, and only then decide
```

## 6. Version selection rules

Choose the model version based on:

1. exact base model required by workflow lane
2. primary file indicator when available
3. safest format
4. most current stable version
5. required trigger words/features
6. compatibility with existing ComfyUI nodes
7. size and expected VRAM load
8. sample quality and metadata
9. known issue notes

Codex must not select a model only because it is popular.

## 7. Download completion checks

A download is complete only when:

```text
[ ] no `.part` extension remains
[ ] file size is greater than zero
[ ] file extension matches model type
[ ] sha256 hash captured
[ ] Civitai/source hash compared if available
[ ] metadata JSON saved
[ ] registry record written
[ ] file moved into correct model folder
[ ] model folder indexed
```

## 8. Model folder routing

Suggested routing:

| Model type | Suggested folder |
|---|---|
| Checkpoint | `ComfyUI\models\checkpoints` |
| LORA | `ComfyUI\models\loras` |
| Controlnet | `ComfyUI\models\controlnet` |
| VAE | `ComfyUI\models\vae` |
| Upscaler | `ComfyUI\models\upscale_models` |
| Embedding/TextualInversion | `ComfyUI\models\embeddings` |
| Pose asset | `ComfyUI\models\controlnet` or project pose asset directory |
| Video model | project video model directory from index |
| Audio model | project audio model directory from index |

Codex must verify actual directories before moving files.

## 9. Runtime validation queue

After registry update, add a row to:

```text
C:\Comfy_UI_Main\Plan\Registries\Models\model_runtime_validation_queue.csv
```

Columns:

```csv
queue_id,created_at,model_name,model_type,base_model,local_path,workflow_lane,test_workflow_path,expected_result,priority,status,evidence_path
```

Status values:

```text
queued
running
passed
failed
blocked
rejected
```

## 10. Runtime validation requirements

Before marking model usable:

- load model in the intended ComfyUI lane
- run a minimal smoke workflow
- capture logs
- capture output if image/video/audio applicable
- run visual/audio/video QA when applicable
- update registry record with evidence path

## 11. Rejected models

Rejected model records must remain traceable so Codex does not rediscover and retry the same bad candidate repeatedly.

Rejected record must include:

```text
rejection_reason
date_rejected
duplicate_of if applicable
compatibility_mismatch if applicable
failed_hash if applicable
failed_runtime_log if applicable
```

## 12. Done gate

A model download/registry task is complete only when:

```text
[ ] candidate metadata captured
[ ] duplicate check complete
[ ] compatibility lane assigned
[ ] download staged
[ ] hash/size verified
[ ] final path assigned
[ ] registry updated
[ ] runtime validation queued or completed
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
