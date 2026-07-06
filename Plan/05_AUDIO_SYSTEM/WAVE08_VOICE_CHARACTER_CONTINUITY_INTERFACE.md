# Wave 08 — Voice Character Continuity Interface

## Purpose

A character can have a voice profile so audio generation, dialogue, breathing, foley, and spatial audio can align with the same entity used in image/video scenes.

## Voice Profile Fields

- voice_profile_id
- character_id
- character_version
- voice source class
- language/accent notes
- pitch range
- pace
- energy
- emotional range
- dialogue style
- breath/effort style
- reference audio manifest
- audio engine compatibility
- QA goals

## Voice Continuity Rules

- Voice identity is versioned like visual identity.
- Voice changes can be temporary emotional states or permanent revisions.
- Dialogue style is not the same thing as voice identity.
- Audio outputs must carry character_id and scene_instance_id metadata.
- Audio QA should check voice match, timing, spatial placement, and scene consistency.

## Future Handoff

Wave 30 and Wave 31 should use this voice profile contract for dialogue, breathing, force-synced audio, foley, room acoustics, and AV sync.
