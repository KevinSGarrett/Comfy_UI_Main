# Wave 05 AI Project Manager Tasks — Workflow Modules, Subgraphs, App Mode

## Wave identity

Wave 05 converts the current source/staging canvas into a modular workflow architecture plan. This wave does not claim final runtime proof. It creates the contracts, module catalog, UI control map, extraction order, validation rules, and App Mode boundary that later waves must implement.

## Required AI project manager behavior

The AI project manager must treat the current Main Flow as a source canvas and never as the final production graph. It must extract small reusable workflow templates and subgraphs from the source canvas, validate them one at a time, and only promote modules after evidence exists.

## Non-negotiable requirements

1. Do not expose raw model paths, raw LoRA paths, private API keys, AWS details, or GitHub tokens in App Mode.
2. Do not enable disabled catalog LoRA nodes as runtime nodes.
3. Do not combine Flux, SDXL, Pony, SD1.5, Z-Image, video, or audio assets in one model chain unless the bridge is image-based and explicitly validated.
4. Do not claim a module is production-ready because its nodes exist.
5. Do not claim App Mode can autonomously plan multi-pass generation. App Mode is an operator interface; the orchestrator/pass planner remains the brain.
6. Do not promote a module unless its static schema, object_info visibility, model reference check, runtime output check, and QA evidence manifest pass.

## Wave 05 output files the AI PM must understand

- `10_REGISTRIES/wave05_module_catalog.json`
- `10_REGISTRIES/wave05_app_mode_control_surface.json`
- `10_REGISTRIES/wave05_module_extraction_map.json`
- `10_REGISTRIES/wave05_workflow_template_contracts.json`
- `02_TARGET_ARCHITECTURE/WAVE05_WORKFLOW_MODULES_SUBGRAPHS_APP_MODE_ARCHITECTURE.md`
- `02_TARGET_ARCHITECTURE/WAVE05_APP_MODE_ORCHESTRATOR_BOUNDARY.md`
- `07_IMPLEMENTATION/WAVE05_IMPLEMENTATION_MANUAL.md`
- `06_QA_TESTING/WAVE05_MODULE_SUBGRAPH_APPMODE_QA_GATES.md`

## Required completion proof for this wave

Wave 05 is complete only if:

- The cumulative pack builds successfully.
- All JSON registries parse successfully.
- The module catalog contains both current-flow extraction modules and future target modules.
- The App Mode control surface exists and separates operator controls from advanced/hidden runtime controls.
- The module extraction map identifies current SaveImage lanes and future extraction targets.
- The validation report marks runtime proof as required later, not complete now.
