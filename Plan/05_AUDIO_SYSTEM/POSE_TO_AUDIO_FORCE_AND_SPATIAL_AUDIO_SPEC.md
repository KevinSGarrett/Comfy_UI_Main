# Pose-to-Audio Force and Spatial Audio Spec

## Goal

Audio must be generated from the same scene graph as visuals. Contact intensity, motion rhythm, room geometry, character placement, and camera distance must shape dialogue, breathing, foley, ambience, and spatial mix.

## Required artifacts

- `audio_force_map.json`
- `room_acoustics_profile.json`
- `speaker_voice_registry.json`
- `foley_event_timeline.json`
- `audio_mix_manifest.json`
- `av_sync_qa_report.json`

## Force mapping

Visual contact graph edges produce audio hints:

```json
{
  "event_id": "contact_001",
  "frame": 48,
  "source": "character_A_left_hand",
  "target": "character_B_upper_arm",
  "force": "firm_grip",
  "expected_audio": ["skin_contact", "fabric_rustle", "subtle_breath_change"],
  "spatial_position": "left_midground"
}
```

## QA

- no clipping,
- voice intelligibility passes,
- audio events align to visual frames,
- room reverb matches environment,
- panning matches camera/spatial plan,
- no stale audio state after visual revision,
- generated audio manifest references exact video/image take.
