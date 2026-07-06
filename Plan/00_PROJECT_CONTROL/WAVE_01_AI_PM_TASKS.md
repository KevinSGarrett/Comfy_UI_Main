# Wave 01 AI Project Manager Task List

## Required tasks

### W01-001 — Create local repo root

Create:

```powershell
C:\Comfy_UI_Main
```

The AI system must not use `C:\Comfy_UI` as the new Git root if that folder contains runtime/model/cache material. The local repo should be a clean project-control and implementation repository.

### W01-002 — Initialize Git and remote

Target remote:

```text
https://github.com/KevinSGarrett/Comfy_UI_Main
```

The AI must check whether the repo already exists locally before running `git init`. It must not overwrite existing local history.

### W01-003 — Install repo safety files

Required files:

```text
.gitignore
.gitattributes
README.md
PROJECT_MANIFEST.json
```

### W01-004 — Create project directory structure

Required root directories:

```text
docs/
workflows/
orchestration/
schemas/
configs/
scripts/
manifests/
evidence/
tests/
app_mode/
external_assets/
.github/workflows/
```

### W01-005 — Exclude all model and large runtime files from Git

Forbidden inside Git:

```text
*.safetensors
*.ckpt
*.pt
*.pth
*.bin
*.gguf
*.onnx
*.engine
*.trt
*.mp4
*.mov
*.avi
*.mkv
*.wav
*.flac
*.zip
*.7z
*.rar
ComfyUI/output/
ComfyUI/input/
models/
checkpoints/
loras/
vae/
clip/
controlnet/
upscale_models/
```

### W01-006 — Set up model references through manifests

The repo must only store model metadata and references, not the model files themselves.

Required fields for each model reference:

```json
{
  "asset_id": "string",
  "engine": "flux|sdxl|pony|sd15|zimage|wan|hunyuan|ltxv|audio|upscale|controlnet|ipadapter",
  "role": "checkpoint|lora|vae|clip|controlnet|upscale|encoder|audio_model",
  "s3_uri": "s3://bucket/key",
  "local_cache_path": "D:/ComfyUI_Models/...",
  "ec2_path": "/opt/comfyui/models/...",
  "sha256": "required_when_known",
  "size_bytes": 0,
  "status": "planned|path_verified|hash_verified|runtime_verified"
}
```

### W01-007 — Keep EC2 off by default

No script may start EC2 unless all of the following are true:

1. Local static QA passes.
2. A runtime proof request JSON exists.
3. The request lists exact workflows and exact model assets.
4. A dry-run command report exists.
5. The user/AI operator provides the explicit confirmation token.

### W01-008 — Create local validation gates

Local validation must check:

- JSON parse.
- JSON Schema validation where schemas exist.
- No model binaries in Git-tracked paths.
- Required directories exist.
- Workflow JSON files are stored in the expected folders.
- Source inventories exist.
- EC2 proof is blocked by default.
- S3 hydration commands are dry-run/manifest-based unless explicitly approved.

### W01-009 — Register ongoing upstream sources

The tracker CSV and Plans ZIP are not frozen. They must be registered as mutable upstream sources and revisited at each wave.

### W01-010 — Produce evidence

Wave 01 evidence must include:

```text
manifests/source_inventory/wave01_source_inventory.json
manifests/repo_validation/wave01_local_repo_validation.json
evidence/local/wave01_no_model_binary_scan.txt
evidence/local/wave01_git_remote_check.txt
evidence/local/wave01_ec2_guard_check.txt
```
