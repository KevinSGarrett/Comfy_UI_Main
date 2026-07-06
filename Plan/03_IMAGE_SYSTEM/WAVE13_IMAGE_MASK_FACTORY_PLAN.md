# Wave 13 — Image Mask Factory Plan

## Image workflow role

For still images, masks are used for:

- identity protection,
- regional inpaint,
- fabric detail,
- skin/material detail,
- contact/occlusion repair,
- hand/face correction,
- edge cleanup,
- output promotion evidence.

## Main image pipeline

```text
Scene Director
→ Camera/Pose/Frame contracts
→ Mask Factory contract
→ Mask generation or manual mask intake
→ Mask validation
→ Workflow patching
→ ComfyUI generation/inpaint/detail
→ Mask evidence scoring
→ Promotion
```

## Hard rule

No regional detail pass should run without a named, validated mask and a maximum denoise limit.
