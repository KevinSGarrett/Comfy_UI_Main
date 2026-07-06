# Wave 23 Deformation, Collision, and Indentation Architecture

## Objective
Create a deterministic layer that converts contact intent into localized image/video repair passes.

## Core inputs
- Wave 21 soft-body material profile
- Wave 22 contact graph edge
- mask factory outputs from Wave 13
- body-shape preservation constraints from Wave 17
- skin/material realism constraints from Wave 18
- clothing/prop contact constraints from Wave 19
- hard-anatomy protection constraints from Wave 20

## Core outputs
- deformation pass contract
- ordered pass list
- required masks
- denoise windows
- evidence checklist
- QA block or promotion decision

## Pass stack
1. Contact-edge resolution
2. Mask assembly
3. Contact-shadow primer or preservation pass
4. Primary deformation pass
5. Occlusion/boundary repair
6. Texture continuity pass
7. Preservation QA
8. Rebound/release planning for temporal media
