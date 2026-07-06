# Image Pipeline Blueprint

## Preferred production path

```text
Scene request
→ character bible + references
→ pose/camera/depth/control maps
→ base image generation
→ base QA
→ full-image realism refine
→ refine QA
→ mask factory
→ body-shape correction if required
→ skin/fabric/detail passes if required
→ face/hands/detail passes
→ contact/deformation passes if required
→ upscale/final detail
→ final crop QA
→ promotion manifest
```

## Base pass

Responsible for:
- number of characters
- identity seed
- body silhouette
- pose
- camera angle
- lighting
- composition
- environment

Not responsible for:
- cellulite
- pores
- finger indentation
- contact pressure
- individual skin blemishes
- final hand detail

## Detail pass

Responsible for:
- surface details
- local blemishes
- textile texture
- hair details
- skin details
- local body-part changes

## Shape pass

Responsible for:
- waist/stomach/hips proportions
- body silhouette
- large body morph corrections

## Contact pass

Responsible for:
- hand/body interaction
- pressure
- deformation
- indentation
- occlusion
- contact shadow

## Final pass

Responsible for:
- resolution
- final polish
- artifacts
- crop QA
- metadata and release
