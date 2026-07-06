# Wave 28A Reference Video vs Generated Micro-Motion

## Reference video path
Use this when the user supplies a real MP4/MOV/WebM/MKV/AVI/M4V or extracted frame sequence and wants the generated output to follow that motion.

The system extracts:
- pose timeline
- depth timeline
- contact timeline
- breathing/micro-motion cues when visible
- camera timing
- frame cadence

## Generated/planned path
Use this when no reference video exists.

The system generates micro-motion from:
- scene state
- fatigue state
- action phase
- contact graph
- character state
- motion profile registry
- QA bounds

## Hybrid path
Use reference video for primary motion and generate extra subtle micro-motion only when it does not conflict with the reference.
