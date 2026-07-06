# Wave 08 — Video/GIF Character Continuity Interface

## Purpose

Video and GIF systems must carry the same character identity across frames, shots, and revisions.

## Required Video Inputs

- character_id and version per visible character
- reference pack manifest
- keyframe identity targets
- per-frame/segment masks
- body/hair/outfit continuity rules
- motion-state notes
- temporal QA goals

## Keyframe Character Locks

Each keyframe must define:

- character instance id
- pose state
- face visibility
- hair state
- outfit state
- body silhouette expectation
- depth order
- mask ownership

## Temporal Failures

Fail video/GIF continuity if:

- face drifts frame-to-frame
- body shape changes without planned motion/deformation
- hair length/color changes unexpectedly
- outfit flickers or swaps
- character count changes unexpectedly
- two characters merge during movement
- voice/audio identity does not match the bound character

## Handoff to Later Waves

Wave 26–29 should reuse this character continuity contract for keyframe planning, temporal repair, micro-motion, and long-form state memory.
