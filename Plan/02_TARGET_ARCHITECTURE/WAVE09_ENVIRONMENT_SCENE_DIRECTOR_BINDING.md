# Wave 09 Scene Director Environment Binding

## Purpose
The Scene Director must bind every request to an environment plan the same way it binds every character request to a Character Bible.

## Required Scene Director additions
The structured scene plan must include:

```json
{
  "environment_binding": {
    "environment_id": "env_bedroom_modern_001",
    "environment_version": "v001",
    "room_profile_id": "room_bedroom_modern_001",
    "lighting_rig_id": "light_soft_window_lamp_001",
    "prop_registry_ids": ["prop_bed_queen_001", "prop_lamp_table_001"],
    "material_surface_profile_ids": ["surface_wall_painted_001", "surface_cotton_bedding_001"],
    "scale_reference_id": "scale_bed_door_human_001",
    "continuity_priority": "strict",
    "allowed_environment_changes": [],
    "disallowed_environment_changes": ["move_window", "change_room_layout", "remove_scale_anchor"]
  }
}
```

## Binding sequence
1. Parse the user request.
2. Determine if an existing environment should be used.
3. If yes, resolve `environment_id` and `environment_version`.
4. If no, create an environment draft and mark it `unproven`.
5. Bind room, lighting, prop, surface, scale, and camera constraints.
6. Generate pass plan and QA goals from the environment constraints.
7. Block execution if required environment fields are missing.

## Interaction with characters
Environment and character plans must be compatible:
- character height/body scale must match furniture and camera framing,
- skin/material lighting must match room lighting,
- outfit and fabric must respond to surfaces and contact,
- pose must fit the room and prop anchors,
- camera angle must not break identity/continuity requirements.

## Interaction with models and LoRAs
Environment-specific LoRAs should be routed by scene role:
- global environment style,
- lighting,
- material/surface,
- prop/furniture,
- background detail,
- final polish.

They must not be mixed across incompatible engines or enabled globally without profile selection.
