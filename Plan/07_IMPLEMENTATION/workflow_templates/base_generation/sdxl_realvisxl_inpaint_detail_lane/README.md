# SDXL RealVisXL Inpaint Detail Lane

Concrete local-first extraction for `MOD-13-SDXL-INPAINT-DETAIL-LANE`.

This lane replaces the Wave04 fixed/bad inpaint references with project-owned inputs:

- RealVisXL checkpoint `realvisxlV50_v50Bakedvae.safetensors`, matching the already proven SDXL runtime path.
- Pass-planner style image input `sdxl_inpaint_detail_source_canny_v1.png`.
- Pass-planner style mask input `sdxl_inpaint_detail_face_mask_v1.png`.
- Controlled inpaint denoise at `0.28`.

Promotion is blocked until static validation, object_info proof, model/input path proof, runtime output, pullback, technical image QA, and strict whole-image visual QA pass. This template intentionally omits the old incompatible Flux checkpoint and body LoRA stack from the deconstructed Wave04 inpaint lane.
