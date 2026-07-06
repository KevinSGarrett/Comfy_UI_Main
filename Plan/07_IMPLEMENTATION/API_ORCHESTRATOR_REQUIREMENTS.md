# API Orchestrator Requirements

## Required services

- scene_request_parser
- pass_plan_builder
- engine_router
- workflow_template_patcher
- comfyui_api_client
- upload_manager
- output_collector
- mask_factory_runner
- control_map_runner
- qa_evaluator
- rerun_decision_engine
- manifest_writer
- promotion_gate

## Required ComfyUI API usage

- `/object_info` before runtime to confirm node classes.
- `/prompt` to submit API workflow JSON.
- `/history/{prompt_id}` to locate outputs.
- `/upload/image` for source images and masks.
- WebSocket progress tracking for long runs.
- Output file scanning only as fallback; prefer history when possible.

## Required run folder

```text
runs/{run_id}/
  request/
  workflow_inputs/
  control_maps/
  masks/
  pass_outputs/
  crops/
  qa/
  manifests/
  logs/
  final/
```

## Required pass lifecycle

1. Build pass JSON.
2. Validate required inputs.
3. Patch workflow template.
4. Validate workflow schema.
5. Submit to ComfyUI.
6. Wait for completion.
7. Collect outputs.
8. Hash outputs.
9. Run QA.
10. Decide next pass.
11. Write manifest.
