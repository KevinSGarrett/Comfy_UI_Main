# Wave 35 Naming and Versioning Standard

## File naming
Use predictable naming:

```text
WAVE##_PURPOSE_NAME.ext
wave##_machine_readable_name.json
Run-Wave##-Purpose.ps1
validate_wave##_purpose.py
```

## Workflow naming

```text
MAIN_FLOW__image_generation__vYYYYMMDD.json
REFINE_FLOW__sdxl_inpaint_detail__vYYYYMMDD.json
VIDEO_FLOW__keyframe_to_video__vYYYYMMDD.json
APP_MODE__image_generator__vYYYYMMDD.json
```

## Version rule
Never overwrite canonical files without updating version metadata and release notes.
