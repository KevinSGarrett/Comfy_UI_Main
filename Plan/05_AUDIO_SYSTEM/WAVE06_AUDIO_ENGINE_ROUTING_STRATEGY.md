# Wave 06 Audio Engine Routing Strategy

## Purpose
Audio engines are not image engines. They must be routed from the scene graph and timeline, not from a visual prompt alone.

## Audio route types
- dialogue/speech
- breathing/body effort
- foley
- contact sound
- clothing/fabric sound
- ambience/room tone
- music
- synchronized AV generation

## Engine candidates
### Separate audio lane
Keep as the default architecture for controllable audio generation, timeline mixing, and QA.

### LTX-2 audio-video lane
Add as a review candidate for synchronized audio-video generation. It should be tested as a companion lane, not as the only audio strategy.

## Required audio manifest fields
- scene_id
- character_id
- speaker_id
- action_id
- contact_event_id
- start_time
- end_time
- intensity
- distance_to_camera
- room/environment
- reverb/spatial profile
- generated_audio_path
- waveform hash
- peak level
- clipping verdict
- sync verdict

## Router rule
If a visual event has physical action but no audio event, the audio router must create an audio planning TODO or block final AV promotion.
