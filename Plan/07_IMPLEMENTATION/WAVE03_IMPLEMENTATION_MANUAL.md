# Wave 03 Implementation Manual

## Mission

Build and run the local validation harness for ComfyUI workflows, registries, manifests, and model references.

## Step 1 — Place workflow files in the repo

Expected local structure:

```text
C:\Comfy_UI_Main\workflows\main\WAVE42_MAIN_FLOW_20260702.json
C:\Comfy_UI_Main\07_IMPLEMENTATION\scripts\
C:\Comfy_UI_Main\Implementation\manifests\
C:\Comfy_UI_Main\.env
```

## Step 2 — Run static validation

```powershell
python .\07_IMPLEMENTATION\scripts\validate_workflow_graph.py `
  --workflow .\workflows\main\WAVE42_MAIN_FLOW_20260702.json `
  --out-dir .\Implementation\manifests\wave03_local_validation
```

Expected outputs:

```text
workflow_graph_validation_report.json
terminal_outputs.csv
node_type_counts.csv
```

## Step 3 — Extract model references

```powershell
python .\07_IMPLEMENTATION\scripts\extract_workflow_model_references.py `
  --workflow .\workflows\main\WAVE42_MAIN_FLOW_20260702.json `
  --out-csv .\Implementation\manifests\wave03_local_validation\model_references.csv
```

Expected output:

```text
model_references.csv
```

## Step 4 — Validate JSON registries

```powershell
python .\07_IMPLEMENTATION\scripts\validate_json_registries.py `
  --root . `
  --out .\Implementation\manifests\wave03_local_validation\json_registry_parse_report.json
```

## Step 5 — Validate local `.env`

```powershell
python .\07_IMPLEMENTATION\scripts\validate_env_file.py `
  --env-file .\.env `
  --out .\Implementation\manifests\wave03_local_validation\env_validation_report.json
```

Never print actual secrets.

## Step 6 — Collect ComfyUI object info

Start local ComfyUI, then run:

```powershell
python .\07_IMPLEMENTATION\scripts\collect_comfyui_object_info.py `
  --api-url http://127.0.0.1:8188 `
  --out .\Implementation\manifests\wave03_local_validation\object_info_snapshot.json
```

## Step 7 — Validate workflow node types against object info

```powershell
python .\07_IMPLEMENTATION\scripts\validate_object_info_against_workflows.py `
  --object-info .\Implementation\manifests\wave03_local_validation\object_info_snapshot.json `
  --workflow .\workflows\main\WAVE42_MAIN_FLOW_20260702.json `
  --out .\Implementation\manifests\wave03_local_validation\object_info_validation_report.json
```

## Step 8 — Run full local validation wrapper

```powershell
powershell -ExecutionPolicy Bypass -File .\07_IMPLEMENTATION\templates\powershell\Run-Wave03-LocalValidation.ps1
```

## Step 9 — Interpret results

| Result | Meaning |
|---|---|
| `PASS` | Static check passed. |
| `WARN` | Non-blocking issue; review required. |
| `FAIL` | Blocking issue; fix before promotion. |
| `BLOCKED_RUNTIME_PROOF_REQUIRED` | Static validation passed, but ComfyUI runtime proof has not been collected yet. |

## Step 10 — EC2 decision

Only consider EC2 after local validation.

EC2 must remain off if:

- workflow graph validation fails,
- JSON registries fail parsing,
- local `.env` is missing required keys,
- no model hydration manifest exists,
- or the required task is only static metadata validation.

## Output contract

Every validation run must write a final manifest:

```text
Implementation/manifests/wave03_local_validation/wave03_validation_manifest.json
```

The AI project manager must not continue to Wave 04 unless the manifest result is either:

```text
PASS
BLOCKED_RUNTIME_PROOF_REQUIRED with a documented reason
```

For production promotion, `BLOCKED_RUNTIME_PROOF_REQUIRED` is not enough.
