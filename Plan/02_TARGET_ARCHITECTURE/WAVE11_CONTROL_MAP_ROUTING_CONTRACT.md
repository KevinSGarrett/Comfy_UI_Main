# Wave 11 Control Map Routing Contract

## Contract Inputs

Every control-map route needs:

- `scene_plan_id`
- `engine_family`
- `character_id` when the control map affects a specific character
- `control_map_type`
- `source_image_or_asset`
- `generated_map_path`
- `control_model_path_or_id`
- `strength`
- `start_percent`
- `end_percent`
- `mask_path` when regional/per-character
- `qa_goals`
- `promotion_policy`

## Supported Map Types

- DWPose
- OpenPose
- Depth
- Normal
- Canny
- Lineart
- Segmentation/region mask
- Pose sequence for video
- Depth sequence for video
- Canny/lineart sequence for video

## Routing Rules

- SDXL routes use SDXL-compatible ControlNet models.
- Flux/Flux2 routes must use Flux/Flux2-compatible control workflows or bridge by saved image.
- Video engines require sequence-aware control maps and temporal QA.
- Do not mix model objects or latent objects across engines.
- Cross-engine control transfer must occur through saved image/map files and manifests.

## Failure Policy

Promotion is blocked if:

- the preprocessor node is missing from `/object_info`;
- the control model is missing from the model registry;
- the generated control map is missing;
- map dimensions do not match the target workflow plan;
- required per-character skeletons are missing;
- final output does not match the intended action/blocking.
