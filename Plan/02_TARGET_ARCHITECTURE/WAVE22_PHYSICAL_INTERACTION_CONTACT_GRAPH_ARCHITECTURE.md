# Wave 22 Physical Interaction Contact Graph Architecture

## Concept
A physical interaction contact graph is a structured representation of contact relationships in an image/video scene.

Instead of describing contact only in a prompt, the graph records:

```text
source owner + source region
→ contact edge
→ target owner + target region/support surface
```

Each edge also carries:

- contact type
- pressure
- intensity
- occlusion state
- duration
- expected visual deformation
- expected audio force
- evidence requirements

## Contact graph node types
- character
- body part
- clothing/fabric region
- prop
- furniture/support surface
- environment surface
- audio event proxy

## Contact graph edge types
- touch
- press
- squeeze
- pull
- push
- support
- rest
- cover
- occlude
- compress
- slide
- drag
- impact
- rebound

## Relationship to prior waves
- Wave 12: frame integrity.
- Wave 13: owned masks.
- Wave 17: body proportion preservation.
- Wave 18: skin/material realism.
- Wave 19: clothing/fabric/prop/furniture contact.
- Wave 20: hard anatomy repair.
- Wave 21: soft-body material profiles.
- Wave 22: explicit contact graph binding.
