# App Mode + Orchestrator Design

## App Mode role

App Mode should be the clean UI for non-node operation. It should expose task-level controls, not internal node details.

## Recommended App Mode controls

- Scene request text
- Output mode: still, GIF, video, full AV
- Character count
- Character reference uploads
- Pose/camera reference uploads
- Body-shape target selector
- Detail target selector
- Contact/soft-body target selector
- Engine mode: Auto, Flux-first, SDXL, Pony specialty, video-auto
- QA strictness: draft, normal, strict, release
- Final output preview
- QA report preview

## Orchestrator role

The orchestrator:
- reads the App Mode inputs
- builds a pass plan
- edits API workflow JSON values
- submits workflows to ComfyUI
- waits for outputs
- runs QA
- reruns failed modules
- writes manifests
- returns final outputs and QA report

## Required ComfyUI API operations

- Get node metadata with object_info.
- Upload input images/masks.
- Submit workflows to prompt queue.
- Poll or subscribe for progress.
- Read history and locate outputs.
- Save outputs, masks, control maps, and crops.
- Write run manifest.

## Required orchestrator services

- pass_plan_builder
- workflow_template_patcher
- comfyui_client
- output_collector
- mask_factory_client
- qa_evaluator
- rerun_decision_engine
- manifest_writer
- promotion_gate
