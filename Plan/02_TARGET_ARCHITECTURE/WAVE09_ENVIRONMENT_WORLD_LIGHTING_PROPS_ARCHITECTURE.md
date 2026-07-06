# Wave 09 Environment, World, Lighting, and Props Architecture

## Purpose
Wave 09 makes environments first-class entities. Before this wave, a scene could describe a room or background in prompt text, but there was no strict object that could be reused by the Scene Director, workflow compiler, engine router, image generator, video module, audio module, and QA gate.

## Core entities
The system now separates these records:

| Entity | Purpose |
|---|---|
| `environment_id` | Stable identifier for a reusable world, room, set, exterior, studio, or location. |
| `environment_version` | Versioned update to layout, lighting, materials, or props. |
| `room_profile_id` | Room dimensions, zones, walls, doors, windows, mirrors, camera-safe areas, and occluders. |
| `lighting_rig_id` | Key/fill/rim/practical/window/HDRI/light-color/softness/shadow direction plan. |
| `material_surface_profile_id` | Surface types, roughness, reflectivity, translucency, fabric/wood/metal/glass/skin-adjacent contact behavior. |
| `prop_registry_id` | Furniture, handheld objects, background objects, scale anchors, and continuity props. |
| `scale_reference_id` | Real-world size anchors that keep people, rooms, props, camera focal length, and perspective coherent. |
| `environment_reference_pack_id` | Reference images, masks, depth maps, edge maps, layout sketches, material swatches, and prompt rules. |
| `environment_continuity_report_id` | QA evidence showing the room, props, light, and camera stayed consistent across passes/shots. |

## High-level runtime flow
```text
User request
→ LLM Scene Director
→ character_id / environment_id / scene intent resolution
→ Environment Bible lookup
→ room + lighting + prop + surface + scale plan
→ pass plan + mask plan + camera plan
→ engine router
→ image workflow modules
→ video workflow modules
→ audio workflow modules
→ continuity QA
→ promotion gate
```

## Why this matters
Hyper-realism fails when the environment is treated as loose text. Common failures include:
- furniture scale drifting between passes,
- lighting changing after inpaint,
- contact shadows disappearing,
- reflections pointing the wrong way,
- props changing shape or location between frames,
- the same room looking like a different room in the next shot,
- audio ambience not matching room size/materials,
- video motion not matching camera placement.

Wave 09 fixes this by requiring every scene to carry an environment contract, not just an environment prompt.

## Relationship to current Main Flow
The current Main Flow should consume environment plans as prompts, masks, references, ControlNet maps, IPAdapter references, and inpaint constraints. It should not own the entire environment intelligence itself. The Scene Director and environment registry own the environment plan; workflow modules execute it.
