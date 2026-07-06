# Wave 16 — Engine Bridge Graph

The engine bridge graph defines which image-generation families may hand off to which refinement families.

## Preferred bridge direction

```text
Flux2 base      ┐
Flux1 base      ├─→ decoded image → SDXL/RealVisXL low-denoise refine
Z-Image base    ┘
```

This works because the transfer object is a decoded image artifact, not an engine-specific latent or model object.

## Same-family path

```text
SDXL/RealVisXL base → SDXL/RealVisXL low-denoise refine → SDXL/RealVisXL masked detail
```

This is the safest high-control path for your current LoRA-rich system.

## Specialty path

```text
SDXL/RealVisXL base → masked Pony specialty pass → SDXL/RealVisXL cleanup
```

Pony is not the default refiner. It is used only when the specialty pass is explicitly justified and masked.

## Last-resort path

```text
approved image → tiny masked SD1.5 repair → strict regression QA
```

This is only for very small artifact repairs.

## Held path

```text
SDXL base → Flux/Flux2 refiner
```

This path is held until a local Flux/Flux2 reference-conditioning or image-to-image workflow is proven to preserve the input image at low denoise.

## Bridge object contract

Every bridge has:

- source engine family;
- target engine family;
- allowed transfer objects;
- forbidden transfer objects;
- denoise limits;
- required evidence;
- risk category;
- fallback behavior.

## Directly forbidden

The bridge graph forbids:

- Flux LoRA in SDXL chain;
- SDXL LoRA in Flux chain;
- Pony LoRA in Flux chain;
- SD1.5 LoRA in SDXL/Flux chain;
- direct latent handoff between unrelated engines;
- hidden fallback that changes engine family without recording a reason.
