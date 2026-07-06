# Wave 13 — Mask Scale Hierarchy

## Macro masks

Used for full-frame and environment zones. These are useful for lighting, background repair, and broad composition corrections.

## Major masks

Used for large subjects or regions. These include person instances, full garments, large props, torso regions, and major limbs.

## Minor masks

Used for localized detail and repair. These include hands, feet, face, hair, fabric folds, contact areas, and prop boundaries.

## Micro masks

Used for very controlled low-denoise corrections. These include facial feature regions, skin texture patches, fabric weave, seams, and small occlusion details.

## Nano masks

Used only for cleanup. These should be tiny masks for edge halos, single artifacts, cutout seams, or tiny boundary fixes.

## Locked rule

The smaller the mask scale, the lower the denoise and the stricter the QA evidence requirement.
