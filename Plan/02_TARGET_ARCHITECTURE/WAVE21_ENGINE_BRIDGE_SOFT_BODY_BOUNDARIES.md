# Wave 21 Engine Bridge Soft-Body Boundaries

Soft-body passes may use the Wave 16 engine bridge, but only through image/mask/control-map artifacts.

## Allowed
- approved image -> masked SDXL/RealVisXL refine
- approved Flux/Z-Image base -> image bridge -> masked SDXL refine
- profile-selected specialty model -> small/medium owned mask only

## Not allowed
- direct cross-family latent mixing
- global activation of soft-body/detail libraries
- unmasked specialty profile passes
- soft-body pass that overwrites identity, pose, frame, or approved body proportions
