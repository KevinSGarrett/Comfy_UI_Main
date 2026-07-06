# Wave 11 Per-Character Skeleton Validation Matrix

## Required Checks

- character ID exists in character registry;
- skeleton ID exists;
- pose source image exists;
- generated map exists;
- keypoint JSON exists when configured;
- mask exists;
- skeleton dimensions match workflow plan;
- depth layer is assigned;
- blocking slot is assigned;
- occlusion role is assigned;
- required body regions are visible;
- hand/face keypoints exist when action requires them.

## Failure Examples

- skeleton missing for secondary character;
- left/right limbs swapped;
- hands mapped to the wrong character;
- skeleton visible but mask missing;
- control map dimensions mismatch target latent/image size;
- full-body request with feet cut off.
