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

## Evidence boundary

Camera acceptance is bound to the exact compiled request, profile, runtime output,
and strict visual review. A full-body result from another lane or control workflow
may support framing research, but it cannot supersede a failed required-region
visibility check for the compiler-bound sample. Landmark presence is not proof
that a hand, foot, face, or other requested region is fully visible and inspectable.
