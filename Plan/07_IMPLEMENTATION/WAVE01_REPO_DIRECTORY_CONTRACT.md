# Wave 01 Repository Directory Contract

## Required directory contract

```text
C:\Comfy_UI_Main
├── docs
├── workflows
│   ├── ui
│   │   ├── current
│   │   └── archive
│   ├── api
│   │   └── templates
│   ├── subgraphs
│   ├── modules
│   └── app_mode
├── orchestration
│   ├── planner
│   ├── runner
│   ├── qa
│   ├── repair
│   └── registries
├── schemas
├── configs
├── scripts
│   ├── powershell
│   └── python
├── manifests
│   ├── source_inventory
│   ├── model_assets
│   ├── workflow_validation
│   ├── qa
│   └── ec2_runtime_proof
├── evidence
│   ├── local
│   ├── ec2
│   └── visual_qa
├── tests
│   ├── unit
│   ├── integration
│   ├── golden_scenes
│   └── no_gpu_static
├── app_mode
│   └── specs
├── external_assets
└── .github
    └── workflows
```

## Directory roles

### docs

Project manuals and AI-PM instructions.

### workflows

ComfyUI UI exports, workflow API templates, future subgraphs, module definitions, and App Mode workflow specs.

### orchestration

The non-ComfyUI brain: pass planner, workflow patcher, runner, QA/rerun decision logic, repair planner.

### schemas

JSON schemas for every contract the AI system must enforce.

### configs

Environment examples only. Secrets must not be committed.

### scripts

PowerShell/Python scripts for local validation, repo setup, source inventory, S3 hydration, and EC2 proof gates.

### manifests

Machine-readable proof and source tracking.

### evidence

Local/EC2/visual QA evidence. Generated media remains excluded unless small and explicitly allowed.

### tests

No-GPU static tests first; runtime tests later.

### external_assets

Documentation for assets stored outside Git.
