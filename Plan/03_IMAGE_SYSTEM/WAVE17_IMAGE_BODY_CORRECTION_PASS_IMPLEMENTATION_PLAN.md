# Wave 17 — Image Body Correction Pass Implementation Plan

## Implementation sequence

1. Select approved base image.
2. Run frame-composition QA to confirm full/half/partial body visibility.
3. Resolve character_id and instance mask.
4. Generate body-region masks.
5. Compile body shape correction contract.
6. Choose pass profile.
7. Patch inpaint/refine workflow JSON.
8. Run low-denoise correction.
9. Run clothing/skin/silhouette cleanup if needed.
10. Score evidence.
11. Rerun or stop based on QA.
12. Promote only passing output.

## Default pass order
- Precheck.
- Large-mask stomach/waist correction.
- Hip/thigh/silhouette correction.
- Clothing surface blend.
- Skin texture restore.
- Silhouette edge cleanup.
- QA and promotion decision.

## Main Flow hooks
The current Main Flow contains:
- SDXL/RealVisXL lane,
- Flux/Z-Image lane,
- Flux-to-SDXL refine lane,
- SDXL inpaint/detail lane,
- IPAdapter branch,
- Canny ControlNet branch,
- mask input slot for inpaint,
- optional IPAdapter attention mask slot.

Wave 17 uses those as staging hooks, but runtime proof is still required before promotion.
