# Unified Model Asset Acquisition And Wiring Protocol

Status: active
Project authority: `C:\Comfy_UI_Main`
Controller: `Plan/07_IMPLEMENTATION/scripts/manage_model_asset_acquisition.py`

## Purpose

The main session must acquire and integrate models and related generation assets while it builds each image, video, or audio capability. Asset acquisition is part of implementation, not an end-of-project cleanup phase.

An asset is not integrated merely because it was downloaded. The required chain is:

```text
concrete capability need
-> exact candidate and version selection
-> duplicate/license/compatibility check
-> API download or authenticated-browser fallback
-> staged hash verification
-> deterministic ComfyUI placement
-> registry and runtime-queue update
-> runtime-requirements and workflow wiring
-> local /object_info visibility
-> bounded runtime smoke
-> modality-specific QA
-> promotion decision
```

## Main-session operating rule

Whenever implementation discovers a missing checkpoint, LoRA, ControlNet, VAE, text encoder, diffusion model, upscaler, motion model, audio model, preprocessor weight, workflow resource, or other exact runtime asset, the session must do one of the following in the same delivery batch:

1. Reuse an existing exact-hash asset and bind it to the new lane.
2. Acquire, place, register, wire, and queue the required asset.
3. Record one exact external blocker such as unavailable license acceptance, paid access, deleted source, insufficient disk, or incompatible runtime.

It must not leave a vague `download later` or `wire later` note when the source is available and the task is authorized.

Do not bulk-download popular models without a declared capability or workflow lane. The objective is a complete system with proven assets, not an unbounded collection of unused files.

## Source selection

Use this preference order:

1. Exact local or registered hash already present in `C:\Comfy_UI_Main`, `C:\Comfy_UI`, or a verified local cache record.
2. Official or creator-published Hugging Face repository pinned to an exact revision.
3. Exact Civitai model version and file.
4. Authenticated browser download when API download is blocked but the signed-in account is allowed to download the asset.

Selection must be based on the required engine, base family, precision, loader node, VRAM target, license/use scope, and expected quality contribution. Popularity alone is not a selection rule.

Adult or NSFW labels are metadata, not filters. `content_based_suppression` must remain `false`; assets are assessed by technical function and compatibility. This does not bypass paid, private, gated, early-access, or license restrictions.

## Credential handling

The controller loads credentials from process environment or `C:\Comfy_UI_Main\.env` using these names:

```text
CIVITAI_API_TOKEN
CIVITAI_TOKEN
CIVITAI_API_KEY
HF_TOKEN
HUGGING_FACE_HUB_TOKEN
```

Rules:

- Never print, log, serialize, or commit secret values.
- Never place a Civitai token in a saved URL. The controller may use one redacted, in-memory token-query retry after a Bearer-header `401/403`; that URL must never be serialized, logged, or placed in browser history.
- Never export browser cookies.
- Never paste an API token into a web page.
- Do not copy `.env` into deploy bundles, evidence, or handoff packets.

## Request contract

Every acquisition starts from a JSON request conforming to:

```text
Plan/08_SCHEMAS/model_asset_acquisition_request.schema.json
```

The request records:

- capability need and intended use;
- provider and exact source identity;
- model type, base model, filename, and ComfyUI target subfolder;
- workflow lane and compatible engines;
- runtime requirements and exact workflow node/input bindings;
- license/access state;
- `content_based_suppression: false`.

For Civitai, `model_version_id` is mandatory and `file_id` or exact filename should be supplied whenever a version has multiple files. For Hugging Face, `repo_id`, exact `revision`, and exact `filename` are mandatory.

## Preflight

Run before the first acquisition in a session or after credential/config changes:

```powershell
python Plan/07_IMPLEMENTATION/scripts/manage_model_asset_acquisition.py `
  --project-root C:\Comfy_UI_Main `
  preflight --network
```

The output reports only credential presence, never values.

## Resolve an exact asset

For Civitai discovery, generate a compact candidate packet first:

```powershell
python Plan/07_IMPLEMENTATION/scripts/manage_model_asset_acquisition.py `
  --project-root C:\Comfy_UI_Main `
  discover-civitai `
  --query "exact capability terms" `
  --types LORA `
  --base-model SDXL `
  --limit 20 `
  --out runtime_artifacts/model_acquisition/discovery/<need>.json
```

Discovery preserves adult/NSFW metadata but does not use it as a filter. It does not automatically select by popularity. The main session must choose the exact compatible version and file ID from the packet.

```powershell
python Plan/07_IMPLEMENTATION/scripts/manage_model_asset_acquisition.py `
  --project-root C:\Comfy_UI_Main `
  resolve `
  --request runtime_artifacts/model_acquisition/requests/<request>.json `
  --out runtime_artifacts/model_acquisition/manifests/<request>.json
```

Resolution captures the exact Civitai version/file metadata or the exact Hugging Face repository/revision/file identity. A Civitai version with ambiguous files fails closed.

## API acquisition

```powershell
python Plan/07_IMPLEMENTATION/scripts/manage_model_asset_acquisition.py `
  --project-root C:\Comfy_UI_Main `
  acquire `
  --manifest runtime_artifacts/model_acquisition/manifests/<request>.json `
  --wire
```

The API path:

- downloads to `Models_Staging/<provider>/downloads/<manifest>/`;
- preserves `.part` bytes after network failure and resumes when range requests are supported;
- rejects HTML/login responses;
- verifies source SHA-256 and exact bytes when supplied;
- refuses to overwrite a different target hash;
- atomically moves the verified file to `models/<target_subdir>/`;
- idempotently updates the model registry and runtime queue;
- updates declared workflow inputs and runtime requirements when `--wire` is present;
- checks local `/object_info` visibility without posting a prompt;
- leaves runtime and QA status queued.

If Civitai returns `401`, `403`, `404`, or an HTML/login page, classification is `BROWSER_DOWNLOAD_REQUIRED`. Do not keep retrying the API in a loop.

## Authenticated browser fallback

Create a browser request:

```powershell
python Plan/07_IMPLEMENTATION/scripts/manage_model_asset_acquisition.py `
  --project-root C:\Comfy_UI_Main `
  prepare-browser `
  --manifest runtime_artifacts/model_acquisition/manifests/<request>.json `
  --out runtime_artifacts/model_acquisition/browser_requests/<request>.json
```

Then the main session must:

1. Use the Codex Chrome control tool with the existing signed-in browser profile.
2. Navigate to the exact `page_url` in the browser request.
3. Select the already resolved model version and file; do not substitute a different file.
4. Complete any access/license acknowledgement that the account is authorized to complete.
5. Download to either `C:\Users\kevin\Downloads` or `runtime_artifacts\model_acquisition\browser_inbox`.
6. Ingest the downloaded file through the controller:

```powershell
python Plan/07_IMPLEMENTATION/scripts/manage_model_asset_acquisition.py `
  --project-root C:\Comfy_UI_Main `
  ingest-browser `
  --manifest runtime_artifacts/model_acquisition/manifests/<request>.json `
  --downloaded-file C:\Users\kevin\Downloads\<file> `
  --wire
```

Browser bytes receive the same hash, placement, duplicate, registry, queue, workflow, and `/object_info` checks as API bytes. The browser path is not a weaker manual-import lane.

## Hugging Face behavior

Prefer immutable commit revisions. Public and token-authorized files may use the controller API path. For gated repositories, accept access in the signed-in browser when authorized, then retry with `HF_TOKEN` or ingest the exact browser-downloaded file. The controller must not claim that an unpinned `main` download is immutable.

## Placement and visibility

The authoritative active local target is:

```text
C:\Comfy_UI_Main\models\<ComfyUI model subfolder>\<filename>
```

`config/comfyui_extra_model_paths.yaml` exposes these folders to local ComfyUI. The exact subfolder must match the loader node family, for example:

```text
checkpoints
loras
controlnet
vae
text_encoders
clip
clip_vision
diffusion_models
unet
upscale_models
embeddings
ipadapter
animatediff_models
audio_encoders
mmaudio
frame_interpolation
optical_flow
```

If `/object_info` is unavailable, acquisition may finish as installed and queued, but runtime use remains blocked until visibility is confirmed. If `/object_info` is available and the filename is absent, investigate folder routing or restart/refresh behavior before generation.

## Wiring contract

`integration.workflow_bindings` identifies exact API workflow JSON, node ID, and input name. The controller updates only those declared inputs. `integration.runtime_requirements_path` identifies the lane requirements file; the controller upserts the exact role, subfolder, filename, bytes, SHA-256, and source.

After wiring, run the existing static workflow/model coverage validator and the lane-specific object-info proof. A workflow reference without installed bytes is blocked; installed bytes without workflow and requirements bindings are also blocked.

## Runtime and QA done gate

Acquisition completion means only:

```text
MODEL_ASSET_INSTALLED_REGISTERED_AND_QUEUED
```

It does not mean the model is production-ready. The same implementation batch should proceed to the smallest honest bounded smoke and modality QA that the lane allows:

- image: decode plus whole-image visual QA and intended feature comparison;
- video: decode, frame/timing integrity, temporal review, and intended motion/state comparison;
- audio: decode, duration/sync/metric gates, then playback or production authority as required;
- preprocessors/control assets: output-map technical and visual correctness;
- custom nodes: node import, `/object_info`, workflow schema, and bounded execution proof.

Only after those pass may registry runtime/QA status advance.

## No-redownload and no-end-of-project backlog rule

Before network contact, check exact hashes and source/version IDs in:

```text
Plan/Registries/Models/model_registry.jsonl
Plan/Registries/Models/model_runtime_validation_queue.csv
C:\Comfy_UI_Main\models
C:\Comfy_UI_Main\ComfyUI\models
C:\Comfy_UI\Runtime_Data\models
```

Reuse verified existing bytes rather than downloading them again. When a new implementation lane is added, its asset acquisition and wiring are part of that lane’s delivery batch. Do not defer a known available dependency until project completion.
