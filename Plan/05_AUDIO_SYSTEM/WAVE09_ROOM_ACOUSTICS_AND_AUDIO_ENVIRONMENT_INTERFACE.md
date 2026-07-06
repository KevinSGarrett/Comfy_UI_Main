# Wave 09 Room Acoustics and Audio Environment Interface

## Purpose
Audio must match the visual environment. A scene in a small tiled bathroom should not sound like an open warehouse, and a carpeted bedroom should not sound like a reflective hallway.

## Audio environment package
The audio module should receive:
- environment ID/version,
- room size class,
- surface materials,
- reflection/absorption profile,
- ambience profile,
- Foley/contact events,
- character positions,
- camera/listener position,
- distance/occlusion notes,
- voice profile references,
- AV sync constraints.

## Acoustic fields
- `room_size_class`
- `surface_absorption_profile`
- `reverb_profile`
- `occlusion_profile`
- `ambience_bed`
- `foley_event_list`
- `listener_position`
- `source_positions`
- `distance_curve`
- `continuity_priority`

## Foley/contact examples
The environment plan can request Foley for:
- footsteps on floor type,
- fabric movement,
- furniture contact,
- door/window movement,
- object placement,
- body/prop contact,
- water or wet surfaces,
- environmental room tone.

## Proof-bound clarification
Audio is a core runtime target. It is proof-bound only because the current image Main Flow does not execute audio generation. Audio must be promoted through its own output evidence and QA.
