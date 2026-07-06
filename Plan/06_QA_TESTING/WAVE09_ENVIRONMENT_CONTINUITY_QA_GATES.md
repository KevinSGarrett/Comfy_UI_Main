# Wave 09 Environment Continuity QA Gates

## Required gates
1. Environment schema validation.
2. Room profile validation.
3. Lighting rig validation.
4. Prop/furniture registry validation.
5. Material/surface validation.
6. Scale-reference validation.
7. Scene Director binding validation.
8. Image environment QA.
9. Video temporal environment QA.
10. Audio environment/acoustics QA.
11. Cross-modal promotion QA.

## Image QA questions
- Did the room layout remain stable?
- Did the lighting direction remain stable?
- Are contact shadows present?
- Are furniture/props correctly scaled?
- Are reflections plausible?
- Are materials consistent after inpaint/upscale?
- Did the background hallucinate new objects?
- Did environment edits break character identity?

## Video QA questions
- Does the room morph between frames?
- Do props drift?
- Does lighting flicker?
- Does scale remain plausible?
- Does camera movement respect the room?
- Does the background shimmer/boil?
- Are character/environment contacts stable?

## Audio QA questions
- Does ambience match the visual room?
- Does reverb match room/materials?
- Do Foley events match visible action?
- Does voice/location match camera/listener position?
- Does audio remain continuous across cuts?

## Promotion rule
A scene cannot be promoted as final hyper-real output until environment QA passes for the requested modalities.
