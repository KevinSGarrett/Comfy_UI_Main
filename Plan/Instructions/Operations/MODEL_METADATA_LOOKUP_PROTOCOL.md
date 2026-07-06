# Model Metadata Lookup Protocol

Wave: 60  
Purpose: Define how Codex Desktop should research, compare, and select model metadata before downloading or using any model asset.

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

## 1. Metadata is a decision layer

Codex must treat metadata lookup as a formal decision step. It must not download a model until it has enough metadata to decide whether the model fits a project need.

Metadata lookup answers:

```text
What is this model?
What base model does it require?
What workflow lane can use it?
What trigger words or special prompt handling are needed?
What file should be downloaded?
Does the model already exist locally?
What quality or runtime risk exists?
What evidence is needed before use?
```

## 2. Required metadata sources

Preferred source order:

1. local model registry
2. existing Plan/Indexes catalogue
3. Civitai API detail response
4. Civitai model page metadata
5. local file hash/name inspection
6. runtime load result
7. QA evidence

Codex must never overwrite confirmed local registry facts with weaker external guesses.

## 3. Lookup by need

Start with a need statement:

```text
Need ID: MODEL_NEED_YYYYMMDD_###
Purpose: improve SDXL fabric microtexture without damaging anatomy.
Required lane: SDXL refine.
Allowed types: LORA.
Disallowed: SD1.5-only, Flux-only, unknown base.
QA focus: fabric detail, skin preservation, prompt compliance.
```

Then search and create candidates.

## 4. Candidate comparison table

For every candidate, Codex must compare:

| Field | Candidate A | Candidate B | Candidate C |
|---|---|---|---|
| model name | | | |
| model type | | | |
| base model | | | |
| version | | | |
| trigger words | | | |
| file format | | | |
| hash available | | | |
| expected workflow lane | | | |
| duplicate status | | | |
| likely quality impact | | | |
| known risk | | | |
| decision | accept/reject/defer | accept/reject/defer | accept/reject/defer |

## 5. Base model classification

Codex must normalize base model names:

| Raw value examples | Normalized base |
|---|---|
| `SDXL`, `SDXL 1.0`, `Pony` | `sdxl` or `pony_sdxl` |
| `Flux.1 D`, `Flux Dev`, `FLUX.1-dev` | `flux_dev` |
| `Flux Schnell`, `FLUX.1-schnell` | `flux_schnell` |
| `SD 1.5`, `Stable Diffusion 1.5` | `sd15` |
| `SD 2.1` | `sd21` |
| unknown/blank | `unknown` |

Unknown base means blocked from runtime use until resolved.

## 6. Trigger words and prompt notes

Codex must capture trigger words exactly but also create practical prompt notes.

Example:

```json
{
  "trigger_words": ["skin texture", "realistic pores"],
  "prompt_notes": "Use at low weight in SDXL refine pass; avoid stacking with more than one skin-detail LoRA until QA confirms no waxy/plastic effect."
}
```

## 7. File metadata

Capture:

```text
file_name
file_id
file_type
format
size
primary
hashes
pickle_scan_result
virus_scan_result
scanned_at
download_url
```

For multiple files, Codex must choose the correct one and explain why.

## 8. Model page notes

Codex should summarize creator notes only into operational fields:

```text
intended_use
recommended_weight
recommended_sampler
recommended_resolution
known_limitations
example_prompt_patterns
negative_prompt_notes
```

Do not paste long creator descriptions into the registry.

## 9. Decision outcomes

Allowed outcomes:

```text
accepted_for_download
already_available
candidate_pending_more_metadata
candidate_pending_runtime_validation
rejected_duplicate
rejected_incompatible_base
rejected_bad_format
rejected_missing_metadata
rejected_failed_runtime
```

Each rejection must have a reason so Codex does not loop.

## 10. Done gate

Metadata lookup is complete only when:

```text
[ ] need statement exists
[ ] local duplicate search completed
[ ] external metadata retrieved if needed
[ ] version/file selected or rejected
[ ] compatibility lane assigned
[ ] candidate decision recorded
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
