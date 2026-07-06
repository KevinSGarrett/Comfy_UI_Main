# Wave 15 — Base Image to Audio Scene Handoff

Base image generation also provides visual context for audio scene planning.

## Audio handoff context

- Room/environment ID
- Character count and placement
- Camera distance and shot scale
- Action/blocking summary
- Surface/material context
- Dialogue or non-dialogue intent
- Video/keyframe intent if present

The audio system should use this context to plan room tone, spatial position, timing, and later AV sync. The base image does not by itself prove audio generation runtime.
