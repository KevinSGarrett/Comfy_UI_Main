# Wave 05 — App Mode and Orchestrator Boundary

## Core decision

App Mode is the clean interface. The orchestrator is the brain.

The system must not treat App Mode as the autonomous planner. App Mode should help the operator or AI project manager provide clean structured inputs. The external orchestrator/pass planner must decide which module runs first, which module runs second, when to rerun, when to repair, and when to block final promotion.

## Responsibilities

| Layer | Responsibility |
|---|---|
| App Mode | Provide clean controls and hide the node graph. |
| Scene Director Bridge | Convert App Mode inputs into structured scene request JSON. |
| Pass Planner | Decide pass order, module sequence, masks, engines, and QA checkpoints. |
| Engine Router | Select compatible engine/model/LoRA/profile groups. |
| Workflow Templates | Execute one module at a time. |
| QA Gate | Decide pass/fail/promotion/block. |

## What App Mode should expose

App Mode should expose controls for:

- output type: still image, GIF loop, video clip, audio-only, audio-video
- runtime target: local static validation, local ComfyUI runtime, EC2 GPU runtime
- QA level: draft, strict, production, maximum
- environment preset
- lighting preset
- character count
- character references
- shot type
- camera angle
- lens
- zoom/distance
- depth of field
- engine profile
- enabled passes
- export formats
- rerun behavior

## What App Mode should not expose

App Mode should not expose:

- GitHub tokens
- Civitai API keys
- AWS keys
- EC2 instance IDs
- raw model paths
- raw LoRA paths
- internal node IDs
- disabled LoRA catalog nodes
- raw prompt text that should be structured and validated first

## Recommended App Mode profile levels

### Basic operator mode

Used for normal generation. Exposes only scene, character, camera, output, and QA controls.

### Advanced operator mode

Used by the AI project manager. Exposes pass toggles, engine profile, runtime target, and module selection.

### Developer/debug mode

Not intended for normal use. Exposes workflow template IDs, node patch maps, and validation reports. This mode should not be publicly exported.

## App Mode output

Every App Mode submission should generate an operator request JSON like this:

```json
{
  "project_id": "hyperrealism_test",
  "runtime_target": "local_static_validation",
  "output_type": "still_image",
  "qa_level": "strict",
  "scene_environment": {
    "environment_preset": "studio",
    "lighting_preset": "soft_window"
  },
  "camera_framing": {
    "shot_type": "full_body",
    "camera_angle": "eye_level",
    "lens_mm": 85,
    "depth_of_field": "medium"
  },
  "characters": {
    "character_count": 1,
    "character_bible_ids": []
  },
  "enabled_passes": ["base", "qa"],
  "allow_final_promotion": false
}
```

## Promotion boundary

An App Mode run may start a workflow. It may not promote a result by itself. Promotion requires:

- workflow template validated
- model references validated
- object_info captured
- runtime output exists
- QA evidence exists
- promotion gate passes
