# Wave 09 Video Environment Continuity Interface

## Purpose
Video generation must reuse the Environment Bible. Video cannot be treated as a completely separate prompt because room, lighting, props, scale, and character placement must remain stable across frames and shots.

## Video input package
A video workflow should receive:
- scene ID,
- environment ID/version,
- room profile,
- lighting rig,
- camera path,
- keyframe list,
- character placement anchors,
- prop anchors,
- material/surface constraints,
- scale anchors,
- negative drift constraints,
- temporal QA goals.

## Keyframe strategy
Approved image outputs become:
- first-frame image,
- last-frame image,
- reference keyframes,
- shot continuity references,
- camera/path anchors.

## Temporal environment QA
Video QA must check:
- room does not morph,
- lighting does not flicker unless planned,
- furniture does not drift,
- props do not disappear,
- scale remains stable,
- character/room contact remains plausible,
- camera path respects room geometry,
- background does not boil or shimmer.

## Proof-bound clarification
Video is a core runtime target. It is not marked fully promoted until a concrete video/GIF workflow produces output files and passes temporal QA.
