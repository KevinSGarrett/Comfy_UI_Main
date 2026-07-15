# Civitai API Operating Protocol

Wave: 60  
Purpose: Tell Codex Desktop how to look up Civitai model metadata, resolve versions/files, download models when needed, and record all metadata needed by the ComfyUI hyperrealism system.

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

## 1. API role in this project

Civitai is used as a model discovery, metadata lookup, version lookup, file download, and trigger-word source for checkpoints, LoRAs, ControlNet assets, poses, textual inversions, and related model assets.

Codex must use the Civitai API only as part of a traceable model acquisition workflow:

```text
Need identified → metadata lookup → compatibility decision → duplicate check → download → hash/size verification → registry update → runtime validation → QA record
```

No model is considered usable simply because it downloaded.

## 2. Documentation source rule

The Civitai GitHub wiki indicates that Civitai REST API documentation has moved to:

```text
https://developer.civitai.com/site/reference
```

Codex must prefer the current developer site when live internet access is available. Historical endpoints remain useful as a fallback reference, but Codex must verify current behavior before building automation that depends on exact endpoint behavior.

## 3. Token handling

Expected `.env` keys, in preferred order:

```text
CIVITAI_API_TOKEN
CIVITAI_TOKEN
CIVITAI_API_KEY
```

Token rules:

- Never print token.
- Never write token into logs.
- Never commit token.
- Never embed token in registry files.
- Prefer `Authorization: Bearer <token>` for authenticated requests when supported.
- Avoid query-string token usage unless the current API requires it because URLs can be logged by shells, proxies, and command history.
- If a model requires authentication and header auth fails, Codex must log the auth failure without exposing token contents.

## 4. Core metadata endpoints

Known historical/public endpoint patterns that Codex may use after verifying current docs:

```text
GET https://civitai.com/api/v1/models
GET https://civitai.com/api/v1/models/{modelId}
GET https://civitai.com/api/v1/model-versions/{modelVersionId}
GET https://civitai.com/api/v1/model-versions/by-hash/{hash}
GET https://civitai.com/api/v1/images
GET https://civitai.com/api/v1/tags
GET https://civitai.com/api/download/models/{modelVersionId}
```

Useful query parameters for model search historically include:

```text
query
tag
username
types
sort
period
primaryFileOnly
```

Common model types historically include:

```text
Checkpoint
TextualInversion
Hypernetwork
AestheticGradient
LORA
Controlnet
Poses
```

Codex must not assume these are the only possible current values; it must record unknown types.

## 5. Model lookup workflow

When Codex needs a model:

1. Define the need in concrete terms:
   ```text
   Need: SDXL skin pore realism LoRA compatible with RealVisXL/SDXL lane.
   ```
2. Search Civitai metadata.
3. Read the model detail page/API response.
4. Resolve model version.
5. Choose file.
6. Record candidate.
7. Check duplicates by:
   - Civitai model ID
   - model version ID
   - file name
   - SHA256/hash
   - local registry semantic match
8. Approve or reject candidate based on compatibility and intended lane.

## 6. Metadata Codex must capture

For every candidate and every downloaded file, record:

```text
model_name
model_id
model_type
model_version_name
model_version_id
base_model
file_name
file_id
file_size
file_format
file_hash_sha256_if_available
civitai_hashes_if_available
download_url_or_api_source
creator_username
tags
trained_words_or_trigger_words
description_summary
version_description_summary
compatibility_lane
intended_use
workflow_lane
local_path
download_timestamp
registry_timestamp
duplicate_check_result
qa_result
visual_impact
video_impact
audio_impact_if_any
runtime_validation_status
known_risks_or_notes
```

## 7. Download workflow

Preferred download behavior:

1. Use API metadata to obtain `downloadUrl`.
2. Download with authentication header if needed.
3. Preserve content-disposition filename when available.
4. Save to a temporary `.part` path first.
5. Verify size and hash.
6. Move atomically into final model directory.
7. Update registry only after verification.

Temporary example:

```text
C:\Comfy_UI_Main\Models_Staging\civitai\downloads\<modelVersionId>\<file>.part
```

Final path examples:

```text
C:\Comfy_UI_Main\ComfyUI\models\checkpoints\
C:\Comfy_UI_Main\ComfyUI\models\loras\
C:\Comfy_UI_Main\ComfyUI\models\controlnet\
C:\Comfy_UI_Main\ComfyUI\models\vae\
C:\Comfy_UI_Main\ComfyUI\models\upscale_models\
```

If actual local model folders differ, Codex must update the location index.

## 8. Download command examples

PowerShell metadata lookup example:

```powershell
$headers = @{}
if ($env:CIVITAI_API_TOKEN) {
  $headers["Authorization"] = "Bearer $env:CIVITAI_API_TOKEN"
}
Invoke-RestMethod -Uri "https://civitai.com/api/v1/models?query=realism&types=LORA&primaryFileOnly=true" -Headers $headers
```

Download example:

```powershell
$headers = @{}
if ($env:CIVITAI_API_TOKEN) {
  $headers["Authorization"] = "Bearer $env:CIVITAI_API_TOKEN"
}
Invoke-WebRequest `
  -Uri "https://civitai.com/api/download/models/<modelVersionId>" `
  -Headers $headers `
  -OutFile "C:\Comfy_UI_Main\Models_Staging\civitai\downloads\model.part"
```

Then verify:

```powershell
Get-Item "model.part"
Get-FileHash "model.part" -Algorithm SHA256
```

## 9. Compatibility assessment

Codex must classify model compatibility before runtime use:

| Base/model family | Compatible with |
|---|---|
| Flux | Flux workflows and compatible Flux LoRA/control layers only |
| SDXL | SDXL checkpoints, SDXL LoRAs, SDXL ControlNet, SDXL refiners |
| Pony | Pony-derived SDXL-compatible lanes, with prompt/style caveats |
| SD 1.5 | SD1.5 workflows only unless explicitly converted/bridged |
| ControlNet | Must match base family and preprocessor output |
| Pose assets | Need workflow-specific loader/adapter |
| VAE | Must match expected latent format/base family |

If compatibility is unknown, Codex must not mark the asset usable. It may mark it as `candidate_pending_runtime_validation`.

## 10. Registry-first rule

Before downloading, search registry:

```text
C:\Comfy_UI_Main\Plan\Registries
C:\Comfy_UI_Main\Plan\Instructions\Indexes
C:\Comfy_UI_Main\Plan\Instructions\Operations\Templates
```

If a matching model already exists, Codex must not duplicate it unless the new version is intentionally different and documented.

## 11. File integrity rules

Codex must prefer:

```text
.safetensors
```

over legacy pickle-based formats when possible.

If a file is `.ckpt`, `.pt`, `.pth`, or otherwise pickle-based, Codex must record scan fields and treat it as requiring stricter validation before use.

For every file:

```text
[ ] size > 0
[ ] extension matches expected file type
[ ] hash captured
[ ] file moved from temporary path to final path only after complete download
[ ] registry entry written
[ ] runtime load test planned or completed
```

## 12. Failure handling

| Failure | Response |
|---|---|
| API 401/403 | Check token presence and auth method; do not expose token |
| API 404 | Mark model/version missing; search by hash/name |
| Rate limit or timeout | Retry with backoff; do not spin |
| Partial download | Delete `.part` or resume only if hash can be verified |
| Hash mismatch | Reject file, re-download once, then mark failed |
| Incompatible base model | Registry as rejected or candidate for another lane |
| Duplicate detected | Do not download; reference existing path |
| Metadata missing | Registry as incomplete; runtime use blocked until resolved |

## 13. Done gate

A Civitai acquisition task is complete only when:

```text
[ ] need statement written
[ ] metadata lookup completed
[ ] version/file selected
[ ] duplicate check completed
[ ] compatibility lane assigned
[ ] download completed if needed
[ ] file hash/size verified
[ ] registry updated
[ ] runtime load validation completed or queued
[ ] QA result recorded
[ ] tracker updated
```

## 14. Enforced acquisition controller and browser fallback

This protocol is implemented by the active unified controller and must not be treated as documentation-only guidance:

```text
Plan/Instructions/Operations/UNIFIED_MODEL_ASSET_ACQUISITION_AND_WIRING_PROTOCOL.md
Plan/07_IMPLEMENTATION/scripts/manage_model_asset_acquisition.py
Plan/10_REGISTRIES/model_acquisition_control_registry.json
```

The main session must use that controller for exact Civitai version/file resolution, API acquisition, staged verification, placement, registry/queue updates, and declared workflow wiring. If API download returns an access/login response, it must create a browser request and use the signed-in Chrome session, then ingest the downloaded file through the same hash-bound controller path. Browser cookies and API tokens must never be exported or serialized.

Adult or NSFW metadata must not suppress discovery, acquisition, placement, or runtime use. Technical compatibility and recorded license/access terms remain required.

Reference sources checked for Wave 60 protocol drafting on 2026-07-06:
- AWS CLI EC2 describe-instances command reference
- AWS CLI EC2 start-instances / stop-instances command references
- AWS CLI EC2 waiter references for instance-running, instance-status-ok, and instance-stopped
- AWS Systems Manager send-command and Run Command references
- AWS Systems Manager start-session reference
- GitHub personal access token and REST API authentication documentation
- Civitai REST API reference migration notice and historical endpoint reference
