# Repository Structure and Manifests

## Recommended root

```text
Ultra_Hyperrealism_System/
  00_PROJECT_CONTROL/
  01_MANUALS/
  02_ARCHITECTURE/
  03_WORKFLOWS/
    ui/
    api/
    subgraphs/
    templates/
  04_PROFILES_AND_PROMPTS/
  05_REGISTRIES/
  06_SCHEMAS/
  07_CONFIG/
  08_SCRIPTS/
  09_ASSET_LIBRARY_STRUCTURE/
  10_TESTING_QA/
  11_RELEASES/
  12_EXAMPLES/
  13_ENGINE_LANES/
  14_AUDIO_LANES/
  15_APP_MODE/
  16_RUNS/
  17_EVIDENCE/
```

## Required manifests

- project_manifest.json
- workflow_manifest.json
- model_registry.json
- lora_registry.json
- engine_registry.json
- custom_node_manifest.json
- pass_template_manifest.json
- qa_gate_registry.json
- release_manifest.json
- run_manifest.json

## Required hash policy

Hash:
- source references
- masks
- control maps
- workflow templates
- patched workflows
- output images
- output frames
- audio files
- final exports
- QA reports
