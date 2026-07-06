# Wave 09 Current Status

## Status
Wave 09 is added as a cumulative update on top of Wave 08.

## What is now formalized
- Environment Bible
- room/world profile
- lighting rig profile
- material/surface profile
- prop/furniture registry
- environmental continuity report
- scale reference profile
- Scene Director environment binding
- image/video/audio environment handoff
- video/audio runtime proof-bound clarification

## Current Main Flow interpretation
The current Main Flow has image-generation lanes and image outputs ready for downstream systems. It includes a note that video/audio are separate runtime lanes until their own ComfyUI node graphs are merged and proven. This is a **runtime-evidence boundary**, not a system-scope exclusion.

## Current proof state
- Image workflow sections: represented in current Main Flow.
- Video/GIF runtime workflows: in architecture scope, require separate workflow/module proof.
- Audio runtime workflows: in architecture scope, require separate workflow/module proof.
- Environment continuity: now specified, not yet runtime proven.
- EC2: not required for this wave.
