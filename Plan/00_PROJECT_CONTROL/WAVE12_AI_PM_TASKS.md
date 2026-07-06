# Wave 12 AI Project Manager Tasks — Frame Composition Integrity

Generated: 2026-07-05T23:15:07Z

Wave 12 converts frame composition from loose prompt wording into a validated contract. The system must be able to say exactly how many characters should appear, how much of each body should be visible, where cropping is allowed, where cropping is forbidden, and whether bodies remain separated.

## Primary build goals

1. Add a frame composition contract that is produced after the Scene Director, Character Bible, Camera Plan, and Pose/Control Map Plan.
2. Add character-count validation for single-character and multi-character outputs.
3. Add body visibility profiles for full-body, 3/4-body, half-body, 1/3-body, 1/4-body, and close-up framing.
4. Add crop boundary rules so the system can block unwanted cut-off heads, hands, feet, limbs, or primary subject regions.
5. Add no-merged-body rules for multi-character scenes and contact-heavy poses.
6. Add detector/skeleton/segmentation evidence contracts without requiring EC2 during static package validation.
7. Add local scripts that compile, validate, and score frame composition reports.

## Current source observations

- Main Flow nodes observed: 356
- Main Flow SaveImage lanes observed: 8
- Latent size nodes observed: 5
- Disabled/catalog nodes observed: 274
- Tracker rows observed: 12887
- Tracker columns observed: 73

## Wave 12 completion condition

Wave 12 is complete when the cumulative pack contains docs, schemas, registries, example contracts, local validation scripts, and a validation report proving the static artifact is internally consistent.
