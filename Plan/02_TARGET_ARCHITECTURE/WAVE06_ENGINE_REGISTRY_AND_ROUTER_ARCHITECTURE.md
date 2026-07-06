# Wave 06 Engine Registry and Router Architecture

## Purpose
The engine registry and router is the compatibility brain of the system. It decides which engine family, checkpoint, LoRA stack, workflow template, and bridge strategy should be used for each pass.

This prevents the system from treating all `.safetensors` files as interchangeable.

## Engine families in scope
Wave 06 covers:

| Family | Role |
|---|---|
| Flux2 | Planned next-generation image/editing/reference family |
| Flux1 | Existing Flux-family image generation and fast smoke/proxy route |
| SDXL/RealVisXL | Existing specialty, Civitai LoRA, refine, inpaint, and detail route |
| Pony-SDXL | Specialty-only route for Pony-compatible checkpoints/assets |
| SD1.5 | Legacy-only route |
| Z-Image | Existing experimental/proxy image route |
| Qwen-Image | Review candidate for text rendering/editing |
| SD3.5 | Review candidate for complex prompt/typography comparison |
| Wan2.2 | Planned primary video candidate |
| HunyuanVideo 1.5 | Planned efficient video candidate |
| LTX-2 | Planned audio-video candidate |

## Router layers
The router must operate in layers:

1. **Request layer**
   - scene type
   - output type
   - character count
   - camera/framing
   - realism target
   - video/audio requirements
   - cost/runtime budget

2. **Pass layer**
   - base generation
   - identity/reference
   - body shape
   - skin/fabric detail
   - contact/deformation
   - multi-character
   - video
   - audio/AV sync
   - QA/retry

3. **Engine layer**
   - family
   - variant
   - checkpoint
   - text encoder
   - VAE
   - sampler profile
   - workflow template
   - compatible LoRA families

4. **Asset layer**
   - model path
   - S3 path
   - local cache path
   - EC2 path
   - hash
   - Civitai model/version metadata
   - source
   - license/access note
   - promotion status

5. **Proof layer**
   - object_info visibility
   - model path exists
   - model loads
   - workflow submits
   - output file exists
   - QA manifest passes
   - promotion manifest recorded

## Hard compatibility rules
1. Flux2 assets stay in Flux2 routes.
2. Flux1 assets stay in Flux1 routes.
3. SDXL assets stay in SDXL routes.
4. Pony assets stay in Pony routes unless explicitly proven compatible with a specific SDXL/Pony checkpoint.
5. SD1.5 assets stay in SD1.5 routes.
6. Video engines do not receive image LoRA stacks unless their own training/adapter format is proven.
7. Audio engines do not receive image/video assets unless the AV model explicitly supports them.
8. Cross-engine transfer is image-based only.

## Why image bridges are required
Flux, Flux2, SDXL, Pony, SD1.5, SD3.5, Qwen-Image, and video engines may all use different architectures, encoders, latent formats, conditioning formats, and LoRA adapter assumptions.

Therefore, the safe bridge is:

```text
engine_A output image
→ save image + manifest
→ optional crop/mask/depth/control extraction
→ load image into engine_B workflow
→ low-denoise img2img/inpaint/edit pass
→ QA before promotion
```

The unsafe bridge is:

```text
Flux model object → SDXL LoRA → Pony conditioning → SD1.5 VAE
```

That must be blocked.
