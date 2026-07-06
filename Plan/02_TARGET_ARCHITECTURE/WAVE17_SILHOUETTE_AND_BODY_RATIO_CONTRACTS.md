# Wave 17 — Silhouette and Body Ratio Contracts

## Purpose
The body-ratio contract defines what the corrected image must preserve and what it is allowed to change.

## Contract fields
- character_id
- source image hash
- target profile
- target regions
- protected regions
- mask artifacts
- maximum allowed shape delta
- denoise range
- pass sequence
- QA thresholds
- rerun policy

## Core body ratio checks
- Waist-to-hip plausibility.
- Left/right thigh balance.
- Abdomen plane continuity.
- Shoulder-to-hip consistency.
- Pelvis and knee alignment.
- Silhouette smoothness.
- Body/camera crop safety.
- Clothing/surface continuity.

## The goal is controlled correction
The system should not blindly force a universal body shape. It should apply the requested target profile while preserving the character's identity and scene constraints.

## Required evidence
A promoted output must include:
- before/after artifact IDs,
- body-region masks,
- source and candidate hashes,
- skeleton/pose preservation report,
- silhouette score report,
- body proportion QA report,
- fail flags,
- final promotion decision.
