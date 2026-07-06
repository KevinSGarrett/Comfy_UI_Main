# Wave 06 Engine Bridge and Compatibility Rules

## Core rule
No cross-engine model object mixing.

The system may move images between engines. It may not move model objects, LoRA adapters, conditioning objects, or latents between incompatible engine families.

## Safe bridge types

### Image bridge
Used when a base image from one engine needs refinement/detail/editing in another engine.

```text
Flux2 image → SDXL low-denoise refine
Flux1 image → SDXL inpaint/detail
SDXL image → video keyframe lane
Z-Image preview → Flux2 or SDXL regeneration
```

### Masked crop bridge
Used for local repairs.

```text
base image → crop body/face/hand/contact zone → target engine inpaint/detail → composite → QA
```

### Control-map bridge
Used for geometry preservation.

```text
base image → depth/edge/pose extraction → target workflow ControlNet/depth/pose branch → QA
```

### Timeline bridge
Used for video.

```text
approved keyframe images → pose/depth/mask timeline → video engine → per-frame QA
```

### Audio event bridge
Used for audio/AV.

```text
scene graph action/contact event → audio event manifest → audio/AV engine → timeline QA
```

## Unsafe bridge examples
Block these:

```text
Flux2 checkpoint + SDXL LoRA
Flux1 checkpoint + Pony LoRA
Pony checkpoint + SDXL LoRA without explicit Pony-compatible proof
SDXL latent passed into Flux KSampler
SD1.5 LoRA used in SDXL
Video LoRA used in image checkpoint
Audio prompt injected as image model conditioning without AV model support
```

## Same-engine stack policy
A stack profile must contain only assets compatible with the selected engine family.

Example:

```json
{
  "engine_family": "sdxl",
  "checkpoint": "RealVisXL",
  "loras": ["sdxl_skin_detail", "sdxl_fabric_detail"],
  "blocked_loras": ["flux_body", "pony_pose", "sd15_face"]
}
```

## Bridge promotion rule
Every bridge must produce a before/after QA manifest:

- source engine
- target engine
- source image hash
- target workflow hash
- denoise/strength values
- masks used
- output image hash
- visual QA verdict
- identity drift verdict
- anatomy/contact verdict
- promotion decision

No bridge can promote without this manifest.
