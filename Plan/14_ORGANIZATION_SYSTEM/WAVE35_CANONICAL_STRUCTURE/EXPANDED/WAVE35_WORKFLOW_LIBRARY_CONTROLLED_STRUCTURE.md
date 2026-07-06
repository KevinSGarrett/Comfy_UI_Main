# Wave 35 Workflow Library Controlled Structure

The workflow library is the main organizational control point for ComfyUI.

## Workflow categories

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

## Canonical workflow rules

- A canonical workflow must have a workflow catalog entry.
- A canonical workflow must have expected output prefixes.
- A canonical workflow must have proof gates.
- Experiments must not overwrite canonical workflows.
- Archived workflows must include replacement/superseded metadata.
