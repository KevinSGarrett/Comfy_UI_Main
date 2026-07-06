# Wave 22 Contact Mask and Occlusion Pass Plan

## Required masks
- source region mask
- target region mask
- contact boundary mask
- occlusion mask
- protected identity/body/frame masks

## Occlusion checks
- source should not disappear unless intentionally occluded
- target should not bleed through source
- boundary should not show cutout artifacts
- contact shadow should align with lighting
- multi-character edges must preserve separation
