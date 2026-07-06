# Wave 07 Audio Scene Director Interface

## Purpose

The Scene Director must convert audio/AV requests into structured plans tied to the same scene graph used by image/video.

## Audio planning fields

Required:

- audio output type
- voice/dialogue requirement
- foley requirement
- ambience requirement
- room acoustics
- speaker positions
- event timeline
- contact/force timeline
- mix target
- AV sync QA goals

## Scene-graph dependency

Audio should not be planned independently of the scene.

Examples:

- room size and surfaces affect reverb
- camera distance affects perceived voice/foley balance
- contact graph affects foley events
- motion intensity affects force markers
- character position affects panning/spatial audio

## Pose-to-audio force map

For scenes with physical motion/contact, the Director should create a force map:

```json
{
  "event_id": "audio_force_001",
  "visual_contact_id": "contact_001",
  "timestamp_or_phase": "peak_contact",
  "intensity": "medium",
  "audio_event": "soft_contact_foley",
  "room_response": "small_room_short_decay"
}
```

## Audio QA goals

Required checks may include:

- audio file exists
- duration matches plan
- event timestamps match visual contact graph
- voice/foley/ambience levels are not clipping
- room acoustics match environment
- AV sync offset within threshold
- mix manifest exists

## Boundary

The Scene Director plans audio. Audio rendering, mixing, and sync proof happen in later audio/runtime waves.
