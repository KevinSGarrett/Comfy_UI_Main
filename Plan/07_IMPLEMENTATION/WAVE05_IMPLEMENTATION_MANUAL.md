# Wave 05 Implementation Manual

## Objective

Create the modular workflow architecture layer that future waves will implement. This wave does not modify the production ComfyUI runtime directly. It defines how the AI project manager must extract, template, validate, and expose modules.

## Step 1 — Ingest the current source workflow

Input:

```text
C:\Comfy_UI_Main\workflows\Wave42_Runtime_Bound__UI__WAVE42_MAIN_FLOW_20260702.json
```

Process:

1. Parse JSON.
2. Count nodes and links.
3. Identify SaveImage terminal lanes.
4. Identify Note boundary nodes.
5. Identify disabled catalog LoRA nodes.
6. Identify upstream nodes for each SaveImage lane.
7. Write extraction map.

Output:

```text
10_REGISTRIES/wave05_module_extraction_map.json
```

## Step 2 — Build module catalog

Each module must include:

- module_id
- module_name
- status
- source
- purpose
- current node IDs if extracted from current flow
- input contract
- output contract
- QA requirements
- owner wave

Output:

```text
10_REGISTRIES/wave05_module_catalog.json
```

## Step 3 — Define App Mode control surface

The App Mode surface must expose only safe high-level controls:

- runtime target
- output type
- QA level
- scene/environment
- character count/reference IDs
- camera/framing
- engine profile
- enabled pass types
- export formats

Output:

```text
10_REGISTRIES/wave05_app_mode_control_surface.json
```

## Step 4 — Define workflow template contracts

Each module must have a template contract requiring:

- workflow API template
- patch points
- input schema
- output schema
- QA schema
- README

Output:

```text
10_REGISTRIES/wave05_workflow_template_contracts.json
```

## Step 5 — Create starter template folders

For each module, future waves should create:

```text
07_IMPLEMENTATION/workflow_templates/<module_id>/README.md
07_IMPLEMENTATION/workflow_templates/<module_id>/workflow_api.template.json
07_IMPLEMENTATION/workflow_templates/<module_id>/patch_points.json
07_IMPLEMENTATION/workflow_templates/<module_id>/input_contract.json
07_IMPLEMENTATION/workflow_templates/<module_id>/output_contract.json
07_IMPLEMENTATION/workflow_templates/<module_id>/qa_contract.json
```

Wave 05 includes starter examples only. Full runtime templates are deferred to later waves after object_info and model proof.

## Step 6 — Validate

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\07_IMPLEMENTATION\templates\powershell\Run-Wave05-ModuleAppModeValidation.ps1
```

Required result:

```text
Validation: PASS
Runtime proof: REQUIRED LATER
```

## What not to do in Wave 05

- Do not rewrite the full source workflow into one production workflow.
- Do not enable disabled LoRA catalog nodes.
- Do not push model binaries into Git.
- Do not start EC2.
- Do not claim creative QA is complete.
- Do not expose secrets or raw model paths in App Mode.
