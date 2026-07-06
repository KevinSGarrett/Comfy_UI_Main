# Wave 35 App Mode Structure

App Mode should expose simplified controls and hide the node graph.

```text
13_APP_MODE/
├── apps/
│   ├── image_generator/
│   ├── image_refiner/
│   ├── video_keyframe_planner/
│   ├── qa_review/
│   └── release_manager/
├── controls/
├── presets/
├── profiles/
├── examples/
├── screenshots/
└── release_exports/
```

## App Mode rule
Every App Mode control must map to a registry entry and a workflow input field.
