# Wave 09 Environment-to-Character Scene Binding

## Binding principle
Characters and environments must be resolved together. A character is not just inserted into any room; the room must support the character scale, pose, lighting, outfit, and action.

## Binding checklist
- character ID exists,
- character version exists,
- environment ID exists,
- environment version exists,
- character scale fits room scale,
- pose fits room geometry,
- outfit fits environment/material plan,
- lighting fits skin/hair/outfit profile,
- props are compatible with body/pose plan,
- camera plan preserves identity and environment layout,
- video plan preserves identity and environment,
- audio plan matches environment.

## Conflict examples
- camera angle hides required identity detail,
- character pose collides with furniture,
- lighting rig destroys skin tone/texture continuity,
- room scale makes character look too large/small,
- audio ambience contradicts visual room,
- video camera path passes through walls/props.

## Resolution
Conflicts should be resolved by revising:
1. camera plan,
2. prop anchors,
3. lighting rig,
4. character pose,
5. environment version,
6. pass plan.
