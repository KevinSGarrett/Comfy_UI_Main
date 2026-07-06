# Wave 20 Implementation Manual

## Build steps
1. Start from an approved image.
2. Detect or manually mark failed hard-anatomy regions.
3. Generate crop boxes and masks.
4. Compile hard-anatomy repair contracts.
5. Patch the inpaint/detail workflow.
6. Run low-denoise crop/detail repair.
7. Composite back into the full image.
8. Score local and global QA.
9. Rerun failed local regions only.
