# Wave 10 Image Camera Plan Compiler

## Goal

Compile a still-image camera plan into image workflow instructions.

## Inputs

- user request
- character bible
- environment profile
- shot intent
- App Mode camera controls
- engine routing rules
- model registry

## Outputs

- positive prompt camera module
- negative prompt crop guard
- latent width/height
- reference routing plan
- ControlNet/pose map plan when proven
- save prefix
- QA goals

## Pass Integration

Camera planning affects:

- base generation pass
- inpaint/detail pass
- upscaling/crop preservation
- face/identity reference pass
- control-map pass
- multi-character regional prompt pass

## Required QA

Every image output should be scored against the camera plan before promotion.
