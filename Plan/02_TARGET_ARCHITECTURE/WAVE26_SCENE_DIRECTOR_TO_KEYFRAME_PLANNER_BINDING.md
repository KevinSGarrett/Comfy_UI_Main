# Wave 26 Scene Director to Keyframe Planner Binding

The LLM Scene Director does not output raw video. It outputs structured intent.
Wave 26 consumes that intent and converts it into:
- shot goals
- keyframe count estimates
- motion phase sequence
- continuity targets
- pose/depth/mask deltas across time
- QA targets for the temporal run
