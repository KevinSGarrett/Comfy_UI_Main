# Wave 13 — Ultimate Mask Factory Architecture

## Core idea

The Mask Factory is the system layer that turns scene plans into executable mask requirements.

It receives:

- Scene Director plan
- Character Bible references
- Camera/framing contract
- Pose/action/blocking plan
- Frame composition integrity contract
- Environment/prop/fabric/contact requirements

It outputs:

- Mask Factory contract
- Required mask scales
- Person-instance mask list
- Body-part mask list
- Fabric mask list
- Contact mask list
- Mask routing instructions
- QA scoring requirements
- Runtime evidence manifest requirements

## Mask hierarchy

```text
macro  → scene zones, background, foreground, floor, walls, large prop groups
major  → person instance, torso, head, limbs, full garment, major prop
minor  → face, hands, feet, hair, fabric folds, contact regions
micro  → eyes/mouth area, skin texture, fabric texture, seam zones, small occlusion
nano   → halo edges, tiny seams, artifact cleanup, individual edge repair
```

## Why this belongs before inpaint/detail

A regional inpaint pass should never run from vague prompt instructions. It should run from a validated mask layer that names:

- what the mask targets,
- which character or object owns it,
- how large it is,
- whether it overlaps another mask,
- what pass is allowed to use it,
- what evidence is required after generation.

## Runtime boundary

The current Main Flow has mask-related wiring, but the Ultimate Mask Factory becomes runtime-proven only after actual mask PNGs, output files, and score reports are generated.
