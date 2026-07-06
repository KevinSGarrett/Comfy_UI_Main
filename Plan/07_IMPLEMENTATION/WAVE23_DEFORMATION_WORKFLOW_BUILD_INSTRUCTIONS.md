# Wave 23 Deformation Workflow Build Instructions

1. Start from the approved base or refine image.
2. Load the Wave 22 contact graph event.
3. Load the Wave 21 soft-body profile for the target region.
4. Build or retrieve the Wave 13 mask bundle.
5. Patch the SDXL inpaint/refine lane with the deformation prompt block.
6. Apply the required low-denoise range.
7. Render a crop-first proof when the contact region is small.
8. Score evidence.
9. Promote or rerun.
