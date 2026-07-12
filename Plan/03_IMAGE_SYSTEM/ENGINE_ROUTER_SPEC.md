# Engine Router Specification

## Purpose

Select the best engine for each pass while avoiding incompatible model/LoRA usage.

## Engine families

- Flux: preferred base and high-quality general generation.
- SDXL/RealVisXL: refinement, inpaint, detail, realism, face/hands, stable low-denoise support.
- Pony: specialty masked pass only unless proven as a base style for the requested scene.
- SD1.5: legacy/specialty only.
- Z-Image: exploratory/base/smoke path until proven.
- Video engines: Wan, HunyuanVideo, LTXV, AnimateDiff fallback.
- Audio engines: provider-neutral speech, SFX, foley, ambience, music.

## Routing rules

1. Base pass should prioritize pose, composition, body silhouette, and identity.
2. Detail passes should prioritize mask compatibility and low-denoise fidelity.
3. Specialty LoRAs must match the engine family.
4. Do not route a Flux LoRA into an SDXL checkpoint or reverse.
5. Bridge engines through images unless latent compatibility is proven.
6. Disabled/rejected models cannot be selected automatically.
7. Every router decision must include reason, fallback, and QA gates.

## Machine implementation

- Resolver: `Plan/07_IMPLEMENTATION/scripts/resolve_wave64_image_engine_route.py`
- Compatibility policy: `Plan/10_REGISTRIES/wave15_model_family_compatibility_matrix.json`
- Local regression gate: `Plan/Instructions/QA/Scripts/Test-ImageEngineRouter.ps1`

Runtime statuses fail closed when a nominal pass prefix also contains a blocked,
failed, pending, missing, incomplete, unproven, or other negative qualifier.
Checkpoint and LoRA compatibility must be accepted by the matrix itself; broad
family normalization is not sufficient evidence. A blocked current lane is not
silently substituted or presented as a selected production route.

## Example

Cellulite on thighs:
- base image: Flux or SDXL
- target: thigh_mask
- likely engine: SDXL/RealVisXL or Flux depending on compatible LoRA
- denoise: 0.18–0.32
- QA: thigh crop confirms cellulite is localized and natural
