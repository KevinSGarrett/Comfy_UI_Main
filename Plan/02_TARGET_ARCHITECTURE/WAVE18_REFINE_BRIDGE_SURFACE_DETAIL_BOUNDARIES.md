# Wave 18 Refine Bridge Surface-Detail Boundaries

Wave 18 reuses the Wave 16 refine bridge but narrows it to surface-detail work.

## Boundary rules
- Flux/Flux2/Z-image base -> SDXL/RealVisXL regional refine is allowed.
- Pony specialty surface-detail passes are allowed only as masked specialty passes.
- SD1.5 remains legacy-only and cannot be the default surface-detail family.
- Cross-family detail passes must preserve the approved base image and approved body-correction results.

## Denoise guidance
- micro texture: 0.10–0.22
- medium texture: 0.18–0.30
- strong regional texture correction: 0.22–0.35
- anything beyond 0.35 requires explicit justification and higher QA scrutiny
