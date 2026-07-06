# Wave 03 Validation Harness Requirements

## Required commands

The local repository must support these commands:

```powershell
python .\07_IMPLEMENTATION\scripts\validate_workflow_graph.py --workflow <workflow.json> --out-dir <out-dir>
python .\07_IMPLEMENTATION\scripts\extract_workflow_model_references.py --workflow <workflow.json> --out-csv <refs.csv>
python .\07_IMPLEMENTATION\scripts\validate_json_registries.py --root <repo-root> --out <report.json>
python .\07_IMPLEMENTATION\scripts\validate_env_file.py --env-file .\.env --out <report.json>
python .\07_IMPLEMENTATION\scripts\collect_comfyui_object_info.py --api-url http://127.0.0.1:8188 --out <object_info.json>
python .\07_IMPLEMENTATION\scripts\validate_object_info_against_workflows.py --object-info <object_info.json> --workflow <workflow.json> --out <report.json>
python .\07_IMPLEMENTATION\scripts\run_wave03_local_validation.py --repo-root . --workflow <workflow.json>
```

## Required behavior

The validation harness must:

- run on Windows,
- use Python standard library wherever possible,
- not require EC2 for static checks,
- not require model files for graph checks,
- not print secret values,
- not copy model binaries into Git,
- produce deterministic JSON/CSV reports,
- return non-zero exit code for blocking failures,
- separate static pass from runtime proof.

## Required report locations

```text
Implementation/manifests/wave03_local_validation/
10_REGISTRIES/
11_RELEASES/
```

## Required AI project manager behavior

The AI project manager must read validation reports before making implementation decisions.

It must not assume:

- a node exists because a workflow references it,
- a model exists because a filename appears,
- a LoRA is active because it appears in a disabled catalog node,
- a QA lane works because a note describes it,
- EC2 is required before local validation proves it.

## Runtime validation hierarchy

```text
static local validation
→ local ComfyUI object_info
→ local model cache validation
→ S3 hydration validation
→ EC2 runtime proof
→ image/video/audio creative QA
```
