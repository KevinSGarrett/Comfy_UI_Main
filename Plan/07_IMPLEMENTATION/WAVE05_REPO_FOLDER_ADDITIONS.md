# Wave 05 — Repo Folder Additions

## New recommended folders for `C:\Comfy_UI_Main`

```text
C:\Comfy_UI_Main\
  workflows\
    source\
    templates\
    subgraphs\
    app_mode\
  workflow_modules\
    MOD-00-APP-OPERATOR-SURFACE\
    MOD-10-SDXL-BASE-LANE\
    MOD-11-ZIMAGE-BASE-LANE\
    MOD-13-SDXL-INPAINT-DETAIL-LANE\
    MOD-14-ZIMAGE-TO-SDXL-REFINE-LANE\
  app_mode\
    controls\
    exports\
    screenshots\
  orchestrator\
    pass_planner\
    workflow_patcher\
    runtime_client\
  qa\
    manifests\
    crop_reports\
    promotion_reports\
  registries\
    modules\
    app_mode\
    workflow_templates\
```

## What belongs in Git

- module contracts
- App Mode control definitions
- workflow templates
- subgraph JSON exports
- patch-point maps
- schemas
- validation scripts
- QA rule files
- manifests without secrets

## What does not belong in Git

- model binaries
- LoRA binaries
- API keys
- AWS credentials
- GitHub tokens
- Civitai API keys
- generated private outputs unless intentionally committed
- EC2 machine-specific temp/cache paths
