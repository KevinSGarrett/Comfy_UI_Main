# Wave 60 Scope — GitHub, AWS, EC2, Sync, and Civitai API Operating Protocols

## Main goal

Create operational playbooks that tell Codex Desktop how to safely and autonomously use GitHub, AWS, EC2, model downloads, Civitai lookup, Civitai model metadata, and local/remote sync.

## Created core protocol files

```text
Plan/Instructions/Operations/GITHUB_MINIMAL_PERSONAL_PROJECT_PROTOCOL.md
Plan/Instructions/Operations/AWS_EC2_GPU_SERVER_START_STOP_PROTOCOL.md
Plan/Instructions/Operations/LOCAL_TO_EC2_SYNC_PROTOCOL.md
Plan/Instructions/Operations/EC2_TO_LOCAL_ARTIFACT_PULLBACK_PROTOCOL.md
Plan/Instructions/Operations/CIVITAI_API_OPERATING_PROTOCOL.md
Plan/Instructions/Operations/MODEL_DOWNLOAD_AND_REGISTRY_UPDATE_PROTOCOL.md
Plan/Instructions/Operations/MODEL_METADATA_LOOKUP_PROTOCOL.md
Plan/Instructions/Operations/MODEL_STORAGE_AND_COMPATIBILITY_PROTOCOL.md
Plan/Instructions/Operations/SECRETS_ENV_HANDLING_PROTOCOL.md
```

## Added helper material

```text
Plan/Instructions/Operations/Scripts/
Plan/Instructions/Operations/Templates/
Plan/Instructions/Operations/Schemas/
Plan/Instructions/Operations/Run_Records/
Plan/Instructions/Operations/Pulled_Back_Artifacts/
Plan/Instructions/Operations/MODEL_REGISTRY_FIELD_DICTIONARY.md
Plan/Instructions/Operations/OPERATIONAL_DONE_GATES.md
.env.example
.gitignore
```

## Static packaging status

Wave 60 is a static protocol and packaging wave. It does not execute live GitHub pushes, AWS starts/stops, Civitai downloads, ComfyUI runtime tests, or model validation. Those are execution tasks for Codex Desktop after extracting the pack into `C:\Comfy_UI_Main\`.

## Completion rule

Wave 60 is complete when every core operations protocol exists, contains done gates, the scripts/templates/schemas are present, the package manifest and validation report are generated, and the cumulative zip integrity check passes.
