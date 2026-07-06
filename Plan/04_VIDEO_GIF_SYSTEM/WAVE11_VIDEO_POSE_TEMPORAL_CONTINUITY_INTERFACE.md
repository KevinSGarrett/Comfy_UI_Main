# Wave 11 Video Pose Temporal Continuity Interface

## Purpose

Video/GIF generation needs pose and depth consistency over time, not just a single static map.

## Required Inputs

- keyframe pose maps;
- optional per-frame pose maps;
- depth sequence or keyframe depth maps;
- camera motion plan;
- character identity locks;
- motion/action timeline;
- temporal QA goals.

## Video Runtime Proof

Video control is not promoted until:

- the video workflow lane exists;
- the sequence maps exist;
- frame/keyframe dimensions match;
- identity does not drift across frames;
- limbs do not pop/swap;
- depth ordering remains stable;
- output is reviewed with frame-sampling QA.
