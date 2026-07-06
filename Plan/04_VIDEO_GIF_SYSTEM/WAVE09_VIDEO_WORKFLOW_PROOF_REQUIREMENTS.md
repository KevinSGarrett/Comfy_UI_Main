# Wave 09 Video Workflow Proof Requirements

## A video lane is not promoted from notes
A video lane requires:
- workflow/module contract,
- engine route,
- local validation,
- model/hydration proof,
- input keyframes,
- output video/GIF,
- file manifest,
- temporal QA report,
- promotion decision.

## Required evidence fields
```json
{
  "video_run_id": "vid_run_001",
  "scene_id": "scene_001",
  "environment_id": "env_001",
  "character_ids": ["char_001"],
  "engine_route": "wan_or_hunyuan_or_ltxv",
  "input_keyframes": [],
  "output_files": [],
  "temporal_qa": {
    "identity_stability": "pending",
    "environment_stability": "pending",
    "lighting_stability": "pending",
    "prop_stability": "pending"
  }
}
```

## Local-first rule
Do not start EC2 for video proof until static validation confirms:
- required keyframes exist,
- environment profile exists,
- character profile exists,
- engine route is valid,
- model assets are registered,
- output path is defined.
