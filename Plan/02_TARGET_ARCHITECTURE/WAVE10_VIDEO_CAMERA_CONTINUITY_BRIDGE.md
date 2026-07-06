# Wave 10 Video Camera Continuity Bridge

## Important Boundary

Image camera framing and video camera motion are related but not identical.

A still image plan defines:

- shot size
- lens look
- framing
- crop
- focus
- subject layout

A video camera plan also needs:

- motion type
- start frame composition
- end frame composition
- speed
- stabilization
- subject tracking
- parallax expectations
- motion QA

## Camera Motion Types

- locked tripod
- handheld subtle
- pan left/right
- tilt up/down
- dolly in/out
- zoom in/out
- orbit
- follow subject
- rack focus
- push-in reveal

## Runtime Proof Rule

Video camera motion must not be marked promoted until:

1. video workflow exists
2. required video nodes are visible through ComfyUI `object_info`
3. model assets hydrate successfully
4. test video renders
5. frames are checked for camera continuity
6. identity/body/environment continuity passes
7. audio/AV sync is checked if audio is present
