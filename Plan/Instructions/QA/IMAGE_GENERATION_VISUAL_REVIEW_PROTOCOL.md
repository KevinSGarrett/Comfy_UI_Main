# Image Generation Visual Review Protocol

## Purpose

This protocol defines strict autonomous inspection for still-image artifacts.

## Required inputs

- generated image path
- generating workflow / prompt reference
- model / LoRA / checkpoint context
- target use case
- prior baseline or expected appearance if applicable

## Review flow

1. Confirm the image loaded successfully.
2. Confirm resolution, file integrity, and readability.
3. Perform global composition review.
4. Perform subject-specific review.
5. Perform anatomy / realism review.
6. Perform rendering artifact review.
7. Perform prompt-compliance review.
8. Score, classify, and record issues.

## Mandatory checklist

Codex must review all applicable dimensions below.

### A. Subject fidelity and realism
- face realism
- eye quality
- skin texture
- hair realism
- teeth / mouth quality
- body proportions
- anatomy consistency
- pose accuracy

### B. Limbs and extremities
- hands / fingers
- feet / toes when visible
- distorted limbs
- joint plausibility

### C. Surface and contact detail
- clothing / fabric
- contact points
- object/body collisions
- deformation realism
- soft-body cues
- texture detail

### D. Cinematic and environmental quality
- lighting
- shadows
- reflections
- background coherence
- camera / lens realism

### E. Failure / artifact detection
- generation artifacts
- identity drift
- over-smoothing
- plastic skin
- waxy faces
- unwanted style contamination

### F. Instruction compliance
- prompt compliance
- negative prompt compliance if applicable
- scene completeness
- intended emotional / stylistic tone

## Scoring model

Score each major category 0–5.

- 5 = excellent / no visible issue
- 4 = strong / minor issue only
- 3 = acceptable but noticeably imperfect
- 2 = weak / requires revision
- 1 = poor / major defect
- 0 = failed / unusable

Recommended decision thresholds:

- **Pass**: no category below 3 and average >= 4.0
- **Pass with issues**: no blocking defect, average >= 3.3
- **Fail**: any blocking defect, or average < 3.3

## Blocking defects

Immediate fail examples:

- severely malformed face or eyes
- broken hands or fused fingers in a focal subject
- implausible anatomy
- severe lighting inconsistency
- obvious object penetration / collision error
- obvious prompt miss
- corrupt or incomplete image file

## Evidence to save

- artifact review record
- issue list
- score summary
- decision
- references to the specific output path and workflow used
