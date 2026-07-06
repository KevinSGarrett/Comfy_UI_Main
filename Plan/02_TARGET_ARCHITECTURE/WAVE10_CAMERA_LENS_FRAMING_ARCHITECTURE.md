# Wave 10 Camera, Lens, Zoom, Angle, Framing Architecture

## Purpose

Wave 10 creates a formal camera layer for image, video, and audio-visual planning. The system must no longer depend on vague prompt fragments to decide camera behavior.

## Core Objects

```text
camera_plan
lens_profile
shot_profile
framing_profile
depth_dof_profile
multi_character_composition
camera_validation_report
```

## Camera Plan Fields

A camera plan must define:

- `shot_size`
- `lens_profile`
- `camera_angle`
- `camera_height`
- `zoom_level`
- `aspect_ratio`
- `resolution`
- `framing`
- `depth_plan`
- `subjects`
- `workflow_patch_targets`
- `qa_goals`

## Shot Size Responsibilities

- Full body: preserve head, hair, hands, feet, outfit edges, floor contact, and scale.
- Half body: preserve face, hands if relevant, upper-body gesture, and outfit context.
- Close-up: preserve identity anchors, eyes/focus target, skin realism, and expression.
- Detail insert: preserve material/skin/prop context enough to identify the location.
- Two-shot/group: preserve subject count, identity separation, screen placement, and depth.

## Workflow Compiler Responsibilities

The workflow compiler should patch or select:

- latent width/height
- positive prompt camera module
- negative prompt crop/identity guards
- reference images / IPAdapter settings
- ControlNet pose/depth/canny maps when proven
- regional prompt slots
- save prefix and evidence manifest path

## QA Responsibilities

The QA layer must confirm:

- shot size matches intent
- crop is intentional
- focus target is sharp
- required body parts/props are visible
- subject count is correct
- identity separation is preserved
- depth order is correct
- full-body/multi-character outputs are not accidentally cropped
