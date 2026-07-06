# Wave 09 Lighting Continuity and Rigs

## Lighting rig purpose
Lighting is not just prompt text. It controls realism, shadows, skin/material appearance, depth, reflections, video continuity, and audio/video mood.

## Lighting rig fields
Each `lighting_rig` should define:
- lighting rig ID
- rig version
- mood
- time of day
- dominant color temperature description
- key light source
- fill light source
- rim/back light source
- practical lights
- window or exterior light contribution
- shadow direction
- shadow softness
- reflection behavior
- exposure notes
- high dynamic range notes
- pass compatibility
- video continuity notes
- audio mood notes

## Lighting continuity rules
1. The base generation pass establishes the lighting rig.
2. Inpaint/detail passes must preserve the lighting rig unless the edit is explicitly lighting-related.
3. Upscale passes must preserve shadow boundaries and specular highlights.
4. Video keyframes must reuse the same rig or a versioned rig transition.
5. Audio ambience must match the environment and mood implied by the lighting.

## Common failure modes
- different light direction after face/body inpaint,
- over-smoothed shadows after upscale,
- props casting no shadow,
- mirror/window reflections not matching light direction,
- video frames flickering between lighting states,
- room ambience inconsistent with visual environment.

## Rig transition model
A lighting rig can change over time only through a `lighting_transition_plan`, such as:
- daylight to evening,
- light flicker,
- character turns on lamp,
- camera moves from window light to interior shadow,
- outdoor-to-indoor transition.

Transitions must be explicit in the scene plan and checked by QA.
