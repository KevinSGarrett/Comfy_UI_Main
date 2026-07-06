# Wave 35 Workflow Library Structure

Workflow folders should be split by purpose:

```text
05_WORKFLOWS/
├── 00_CANONICAL_MAIN_FLOW
├── 01_IMAGE_BASE
├── 02_IMAGE_REFINE
├── 03_MASK_INPAINT
├── 04_CONTROL_POSE_DEPTH
├── 05_VIDEO_GIF
├── 06_AUDIO
├── 07_APP_MODE_TOOLS
├── 08_QA_VALIDATION
├── 09_EXPERIMENTS
└── 10_ARCHIVED
```

## Rule
Only one workflow per purpose should be marked canonical at a time.
