# Wave 25 Multi-Character Interaction Workflow Build Instructions

1. Use Wave 24 instance layout as the first dependency.
2. Use Wave 22 contact graph edge as the interaction event source.
3. Use Wave 13 masks to assemble per-person and contact masks.
4. Use Wave 23 deformation passes only after source/target ownership is proven.
5. Use SDXL inpaint/detail or low-denoise refine lanes for local repair.
6. Block promotion if any merge-prevention evidence fails.
