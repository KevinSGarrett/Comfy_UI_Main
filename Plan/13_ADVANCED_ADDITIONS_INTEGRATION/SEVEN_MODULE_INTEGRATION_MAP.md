# Seven Advanced Realism Modules Integration Map

## Core rule

The advanced additions must be represented as structured artifacts. They must not be implemented only as longer prompts.

## Shared artifact flow

```text
Scene Request
  → LLM Scene Director
  → Scene Graph + Character Bible + Environment Bible + Camera Plan
  → Contact Graph + Surface State + Motion Tracks + Audio Force Map
  → Workflow Compiler
  → ComfyUI Modules
  → QA Evidence + State Diff + Rerun Plan
```

## Canonical artifacts

- `scene_graph.json`
- `character_bible.json`
- `environment_bible.json`
- `camera_plan.json`
- `shot_frame_plan.json`
- `pose_control_plan.json`
- `mask_plan.json`
- `contact_graph.json`
- `softbody_profile.json`
- `surface_state_ledger.json`
- `motion_timeline.json`
- `audio_force_map.json`
- `room_acoustics_profile.json`
- `qa_manifest.json`
- `state_diff_report.json`
- `take_variant_manifest.json`

## AI PM enforcement

The AI project manager must fail a wave if a feature is described in prose but lacks schema fields, workflow hooks, QA outputs, and a runtime proof plan.
