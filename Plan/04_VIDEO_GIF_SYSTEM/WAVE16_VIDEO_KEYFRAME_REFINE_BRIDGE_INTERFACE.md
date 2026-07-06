# Wave 16 — Video Keyframe Refine Bridge Interface

Video remains in scope for the full system. Wave 16 defines how refined still images may feed video lanes without destabilizing temporal consistency.

## Keyframe rule

Only promoted image artifacts may become video keyframes.

A keyframe is eligible only if:

- base image QA passed;
- refine bridge QA passed;
- character count and body visibility passed;
- identity/camera/environment continuity passed;
- output hash is recorded;
- frame contract is exported.

## Avoiding video instability

Do not feed unpromoted experimental refine outputs into video generation. A small still-image drift can become severe flicker, identity drift, or body drift across frames.

## Video handoff manifest

A refined keyframe handoff should include:

- keyframe image path;
- image hash;
- source/base engine;
- refine engine;
- denoise history;
- camera plan;
- character ids;
- environment id;
- control map ids;
- masks used;
- QA score;
- failure/rerun history.

## Temporal refinement

For video, region/detail passes should be consistent across keyframes. The same character mask and identity references should be reused whenever possible.
