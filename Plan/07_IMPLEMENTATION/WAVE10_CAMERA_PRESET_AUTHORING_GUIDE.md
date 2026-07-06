# Wave 10 Camera Preset Authoring Guide

## Preset Anatomy

A camera preset should define:

- shot size
- aspect ratio
- width/height
- lens profile
- camera angle
- camera height
- framing margins
- depth profile
- crop policy
- focus target
- QA goals

## Example Preset Names

```text
full_body_catalog_35mm_eye_level
half_body_portrait_50mm
face_closeup_85mm_identity
wide_room_24mm_deep_focus
two_shot_35mm_layered_depth
macro_skin_100mm_detail
```

## Strength of Prompt Wording

Camera presets should be direct but not overloaded:

```text
full body, head to toe visible, feet visible, centered, 35mm natural perspective
```

Avoid adding too many conflicting camera words:

```text
full body close-up macro wide angle telephoto
```

That should be treated as a conflict and resolved before runtime.
