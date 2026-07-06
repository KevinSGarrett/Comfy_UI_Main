# Wave 12 Image Frame Integrity Plan

For image generation, frame integrity QA runs after each selected SaveImage lane creates output.

## Required image checks

1. Confirm image exists and decodes.
2. Detect person instances.
3. Detect faces when faces should be visible.
4. Detect pose skeletons.
5. Estimate body visibility ratio per character.
6. Check crop boundaries.
7. Check for merged bodies or unassigned fragments.
8. Score the result.
9. Promote, review, or repair.

## Repair pass examples

- Rerun with wider framing.
- Use ControlNet/OpenPose with more padding.
- Use outpaint to recover cropped limbs.
- Use regional inpaint only when the body count and crop boundaries are already correct.
- Reject merged-body generations instead of trying to polish them.
