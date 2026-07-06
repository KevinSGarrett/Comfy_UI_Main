# Wave 15 — Model Family Compatibility and Checkpoint Boundaries

This file defines the strict model-family boundary required before base image generation.

## Families

| Family | Can use | Must not mix with |
|---|---|---|
| Flux2 | Flux2 checkpoints and proven Flux2 LoRAs | Flux1/SDXL/Pony/SD1.5/Z-Image |
| Flux1 | Flux1 checkpoints and Flux1 LoRAs | Flux2 unproven assets, SDXL, Pony, SD1.5, Z-Image |
| SDXL/RealVisXL | SDXL checkpoints and SDXL LoRAs | Flux, SD1.5, unproven Pony assets |
| Z-Image | Z-Image models/templates | Flux/SDXL/Pony/SD1.5 assets |
| Pony | Pony-family checkpoints/tags/LoRAs | Flux, SDXL unless explicitly Pony-SDXL proven, SD1.5 |
| SD1.5 | SD1.5 checkpoints/LoRAs | Flux, SDXL, Pony, Z-Image |

## Image bridge rule

When one family feeds another, the bridge must be:

```text
saved image → evidence manifest → loaded image → next workflow
```

Never:

```text
Flux latent/model → SDXL sampler
SDXL LoRA → Flux checkpoint
Pony tags/LoRAs → Flux/SDXL default base
```

## Current Main Flow caution

Some current lane names imply SDXL/RealVisXL while certain loader names require verification. Wave 15 does not delete those lanes. It blocks their promotion until the loader/checkpoint/LoRA family is proven consistent.
