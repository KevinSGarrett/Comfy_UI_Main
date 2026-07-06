# Wave 13 — Scene Director Mask Binding

The Scene Director must request masks structurally.

## Scene Director output additions

```json
{
  "mask_requirements": {
    "required_scales": ["macro", "major", "minor"],
    "person_instance_masks": true,
    "body_part_masks": ["face", "hands", "hair"],
    "fabric_masks": ["full_garment", "fabric_fold_group"],
    "contact_masks": ["hand_object_contact", "person_person_boundary"],
    "promotion_gates": ["mask_evidence_scored", "no_mask_bleed"]
  }
}
```

## Binding rules

- Character count decides person-instance mask count.
- Camera/framing decides visibility and crop masks.
- Pose/control maps decide limb and skeleton-linked masks.
- Outfit profiles decide fabric masks.
- Contact/action plans decide contact masks.
- Frame integrity QA decides merge/fragment blockers.
