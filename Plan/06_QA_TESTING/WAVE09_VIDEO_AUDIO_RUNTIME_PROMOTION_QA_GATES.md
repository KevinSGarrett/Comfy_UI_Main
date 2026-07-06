# Wave 09 Video/Audio Runtime Promotion QA Gates

## Why this exists
Video/audio are included in the project, but the current Main Flow image canvas should not be used as proof that video/audio are already runtime-promoted. This QA gate prevents false promotion.

## Video promotion requirements
- video workflow/module exists,
- engine route is declared,
- model assets are hydrated and validated,
- input keyframes exist,
- output video/GIF exists,
- temporal QA report exists,
- environment continuity report exists,
- character continuity report exists,
- promotion decision is stored.

## Audio promotion requirements
- audio workflow/module exists,
- audio engine/tool route is declared,
- environment acoustic profile exists,
- output audio exists,
- ambience/Foley/voice QA report exists,
- AV sync report exists when paired with video,
- promotion decision is stored.

## Invalid promotion sources
- notes only,
- planned files without outputs,
- unrelated smoke output,
- missing output hash,
- missing QA report,
- missing environment ID,
- missing character ID.
