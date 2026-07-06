# Wave 05 — Audio Module Interface

## Purpose

Wave 05 defines how the audio system receives scene state from the image/video system. Audio is not a side project. It should be tied to the same scene graph and timeline.

## Required input from visual modules

Audio modules must receive:

- scene environment
- room size/materials
- camera distance
- character IDs
- speaker IDs
- action timeline
- contact/action force profile
- movement/foley events
- voice profile references
- mood/intensity state
- output format requirements

## Audio module output contract

```json
{
  "audio_take_id": "audio_take_001",
  "dialogue_tracks": [],
  "foley_tracks": [],
  "ambience_tracks": [],
  "music_tracks": [],
  "spatial_audio_manifest": {},
  "sync_points": [],
  "qa_report": {}
}
```

## Required QA

Audio must be checked for:

- clipping
- silence
- wrong duration
- intelligibility
- voice mismatch
- spatial mismatch
- sync mismatch
- missing foley/ambience events

## Wave dependency

Full implementation is deferred to Waves 30–31.
