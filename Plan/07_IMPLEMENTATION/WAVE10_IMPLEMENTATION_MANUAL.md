# Wave 10 Implementation Manual

## Step 1 — Create Camera Plan

Use `compile_camera_plan.py` or the Scene Director to create a camera plan.

```powershell
python 07_IMPLEMENTATION/scripts/compile_camera_plan.py `
  --request 09_EXAMPLES/wave10_app_mode_camera_request.example.json `
  --out runtime/camera_plans/cam_test.json
```

## Step 2 — Validate Camera Plan

```powershell
python 07_IMPLEMENTATION/scripts/validate_camera_plan.py `
  --plan runtime/camera_plans/cam_test.json `
  --out runtime/camera_plans/cam_test.validation.json
```

## Step 3 — Patch Workflow

The workflow compiler should patch:

- latent width/height
- prompt camera module
- negative crop guard
- reference routing
- control map usage when proven
- save prefix

## Step 4 — Run Local ComfyUI

Run locally first. Do not turn on EC2 for camera plan validation unless local static validation passes.

## Step 5 — Collect Evidence

Evidence must include:

- output image/video path
- camera plan id
- dimensions
- prompt module
- workflow hash
- model registry hash
- QA report

## Step 6 — Promote or Block

Promote only if the camera/framing QA gates pass.
