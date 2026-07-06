# Wave 27 Reference Video and Keyframe Route Selection

Wave 27 supports two major temporal entry modes:
- reference-video-file-driven routing
- still/keyframe-plan-driven routing

## Selection logic
Use reference-video-driven routing when:
- motion must follow a supplied video source,
- timing/physics/interaction cadence already exists,
- exact action reference is more important than invented motion.

Use keyframe-driven routing when:
- no reference video exists,
- the motion should be constructed from planned scene states,
- the system can safely interpolate between approved keyframes.
