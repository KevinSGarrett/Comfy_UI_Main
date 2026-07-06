# Wave 05 — Workflow Template and API JSON Strategy

## Purpose

The system needs workflow templates that can be patched safely by an AI project manager. The current Main Flow is too broad to patch directly for production. Wave 05 defines the conversion strategy from source canvas to module-level API workflow templates.

## Template categories

### Static validation templates

These are used locally without GPU work. They validate JSON structure, expected node IDs, required patch points, and model reference rules.

### Local ComfyUI templates

These are used when local ComfyUI is running and can provide `/object_info`, `/models`, `/system_stats`, and `/prompt` validation.

### EC2 GPU proof templates

These are used only after local validation passes and a GPU proof is actually needed.

## Required template files

Each module must eventually have:

```text
workflow_templates/<module_id>/workflow_api.template.json
workflow_templates/<module_id>/patch_points.json
workflow_templates/<module_id>/input_contract.json
workflow_templates/<module_id>/output_contract.json
workflow_templates/<module_id>/qa_contract.json
workflow_templates/<module_id>/README.md
```

## Required patch point types

Every patch point must be named and typed.

Examples:

```json
{
  "patch_point_id": "base_positive_prompt",
  "node_id": 83,
  "field": "widgets_values[0]",
  "type": "structured_prompt_text",
  "required": true
}
```

```json
{
  "patch_point_id": "seed",
  "node_id": 17,
  "field": "widgets_values[0]",
  "type": "integer_seed",
  "required": true
}
```

```json
{
  "patch_point_id": "output_prefix",
  "node_id": 19,
  "field": "widgets_values[0]",
  "type": "safe_output_path_prefix",
  "required": true
}
```

## Prompt handling rule

The AI system must not blindly reuse raw prompt text from source workflows. Prompts must be converted into structured fields:

- subject
- character IDs
- pose/action
- environment
- camera
- lighting
- material/detail goals
- negative constraints
- QA expectations

This makes the system testable and prevents uncontrolled prompt drift.

## Model handling rule

Workflow templates should use profile references first, raw model paths second.

Preferred:

```json
{
  "engine_profile": "sdxl_realvisxl_base",
  "lora_stack_profile": "sdxl_base_realism"
}
```

Avoid exposing:

```json
{
  "lora_path": "raw/path/to/model.safetensors"
}
```

Raw paths may exist inside private registries and patch manifests, but not in App Mode.

## Runtime execution order

1. Select module.
2. Load workflow template.
3. Validate template schema.
4. Resolve engine profile.
5. Resolve model references.
6. Patch prompt/camera/mask/reference inputs.
7. Validate patched workflow.
8. Submit to `/prompt`.
9. Poll `/history/{prompt_id}`.
10. Collect outputs.
11. Write evidence manifest.
12. Run QA gate.
13. Promote, rerun, or block.

## Failure handling

A template must fail closed if:

- a required patch point is missing
- a required node class is absent from object_info
- a model reference is unresolved
- a disabled catalog node is used as runtime
- engine/LoRA compatibility fails
- output path is unsafe
- evidence manifest cannot be written
