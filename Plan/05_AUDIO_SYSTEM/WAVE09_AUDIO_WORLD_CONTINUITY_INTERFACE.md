# Wave 09 Audio World Continuity Interface

## Audio continuity goals
Audio should preserve:
- environment ambience,
- room tone,
- character voice identity,
- source distance,
- source position,
- acoustic material response,
- scene-to-scene continuity,
- video sync.

## Binding to Environment Bible
The audio runtime must use the same environment ID as the image/video scene. It should not invent a different room unless the scene transition explicitly changes environments.

## QA checks
- ambience matches room type,
- reverb matches materials,
- Foley matches visible actions,
- voice distance matches camera/listener position,
- no audio event contradicts video,
- no room tone discontinuity across cuts unless planned.
