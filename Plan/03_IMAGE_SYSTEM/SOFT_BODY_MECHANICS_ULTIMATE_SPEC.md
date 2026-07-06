# Ultimate Soft-Body Mechanics, Deformation, and Contact Spec

## Core principle

This system creates visual soft-body realism through controlled references, masks, contact graphs, denoise schedules, and QA. It is not a full physical simulator unless future 3D/simulation tools are integrated. The system must never mark soft-body behavior as successful unless visual evidence proves it.

## Soft-body region profiles

Each region can define:

```json
{
  "region": "thigh|abdomen|butt|breast|upper_arm|cheek|fabric|mattress",
  "firmness": "firm|average|soft|very_soft",
  "sag": "none|light|medium|heavy",
  "compression_visibility": "low|medium|high",
  "rebound_speed": "fast|medium|slow",
  "ripple_likelihood": "none|low|medium|high",
  "pressure_mark_likelihood": "none|low|medium|high"
}
```

## Contact pass recipe

```text
Input approved image
  → source mask: hand/finger/object/body part
  → target mask: body region/material/furniture
  → contact-zone intersection/nearby falloff mask
  → depth/normal/edge guidance
  → selected compatible LoRA or no LoRA
  → inpaint/detail sampler
  → before/after crop QA
```

## Interaction categories

- light touch,
- held contact,
- firm grip,
- compression,
- squeeze,
- pull/push displacement,
- support weight,
- impact,
- repeated rhythmic motion,
- release/rebound.

## QA must prove

- source body part is anatomically readable,
- target area is anatomically readable,
- contact point is correct,
- indentation/compression appears where planned,
- shadow/occlusion supports contact,
- no melted fingers,
- no duplicated limbs,
- no merged people,
- surrounding anatomy is continuous,
- deformation does not bleed into unrelated regions.
