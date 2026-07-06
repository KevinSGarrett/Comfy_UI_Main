# Wave 03 Local Validation Matrix

| Check | Local only | Requires local ComfyUI | Requires EC2 | Current package result |
|---|---:|---:|---:|---|
| JSON parse | Yes | No | No | PASS |
| Static link validation | Yes | No | No | PASS |
| Node type inventory | Yes | No | No | PASS |
| Terminal output inventory | Yes | No | No | PASS |
| Model reference extraction | Yes | No | No | PASS |
| JSON registry parse | Yes | No | No | PASS |
| `.env.example` exists | Yes | No | No | PASS |
| Real `.env` validation | Yes | No | No | Not run; user-specific |
| `/object_info` capture | No | Yes | Optional | Not run |
| Node visibility validation | No | Yes | Optional | Blocked until object_info |
| Model file local existence | Yes | No | No | Not run against user cache |
| S3 object existence | No | No | Optional AWS API | Not run |
| GPU model load proof | No | Optional local GPU | Yes if local insufficient | Not run |
| Image output proof | No | Optional local GPU | Yes if local insufficient | Future wave |
| Creative QA | No | Optional local GPU | Optional | Future wave |

## Current static inventory numbers

```text
workflow nodes: 356
workflow links: 91
node types: 28
model references: 287
terminal outputs: 16
lora/library nodes: 275
nodes upstream of enabled terminal outputs: 69
nodes not upstream of enabled terminal outputs: 287
tracker rows: 12887
tracker columns: 73
Plans ZIP files: 4870
Advanced Additions files: 20
```

## Required next local command

```powershell
cd C:\Comfy_UI_Main
powershell -ExecutionPolicy Bypass -File .\07_IMPLEMENTATION\templates\powershell\Run-Wave03-LocalValidation.ps1
```

## Required next runtime command when local ComfyUI is running

```powershell
python .\07_IMPLEMENTATION\scripts\collect_comfyui_object_info.py --api-url http://127.0.0.1:8188 --out .\Implementation\manifests\wave03_local_validation\object_info_snapshot.json
```
