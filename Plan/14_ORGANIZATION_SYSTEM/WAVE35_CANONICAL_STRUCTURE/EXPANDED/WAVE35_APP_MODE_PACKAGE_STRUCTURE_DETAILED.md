# Wave 35 App Mode Package Structure Detailed

App Mode turns complex node graphs into usable tools.

```text
13_APP_MODE/
├── apps/
│   ├── image_generator/
│   ├── image_refiner/
│   ├── mask_inpaint_tool/
│   ├── control_pose_tool/
│   ├── video_keyframe_tool/
│   ├── audio_mix_tool/
│   ├── qa_review_tool/
│   └── release_manager/
├── controls/
│   ├── shared_controls/
│   ├── image_controls/
│   ├── video_controls/
│   ├── audio_controls/
│   └── qa_controls/
├── presets/
│   ├── preview_presets/
│   ├── final_presets/
│   ├── app_mode_presets/
│   └── qa_presets/
├── profiles/
│   ├── engine_profiles/
│   ├── realism_profiles/
│   ├── workflow_profiles/
│   └── release_profiles/
├── examples/
├── screenshots/
├── validation/
└── release_exports/
```

## App Mode source-of-truth rule

Every App Mode control must map to:

- workflow input
- schema field
- registry entry
- validation rule
- owner app
