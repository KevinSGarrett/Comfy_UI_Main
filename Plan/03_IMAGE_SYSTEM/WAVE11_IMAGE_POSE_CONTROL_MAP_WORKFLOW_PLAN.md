# Wave 11 Image Pose Control Map Workflow Plan

## Image Workflow Module Stack

1. Base image generation module.
2. DWPose/OpenPose module for body/action skeleton.
3. Depth module for room and camera distance.
4. Canny/lineart module for edges and prop contours.
5. Normal map module for surface orientation when needed.
6. IPAdapter/identity module.
7. Regional inpaint/detail module.
8. Upscale and QA module.

## Current Main Flow Integration

The current Main Flow already has Canny and IPAdapter/reference staging. Wave 11 adds the contracts needed to add DWPose/OpenPose/depth/normal/lineart as separate workflow modules instead of cramming all controls into the single giant canvas.

## Output Requirements

Every generated image should carry:

- control plan ID;
- source map paths;
- map hashes;
- strength/start/end settings;
- workflow module ID;
- model hashes;
- output hash;
- QA decision.
