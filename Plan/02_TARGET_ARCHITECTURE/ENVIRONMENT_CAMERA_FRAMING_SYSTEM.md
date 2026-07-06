# Environment, Camera, Framing, and Shot-Control System

## Goal

Hyper-realism requires controlled environment, camera, and frame composition. Prompting `low angle` or `full body in frame` is not enough. The system must create a structured shot plan, then verify the output against it.

## Environment system

Every scene must have an `environment_bible.json`:

```json
{
  "environment_id": "bedroom_warm_softbox_001",
  "room_type": "bedroom",
  "dimensions_hint": "small|medium|large",
  "primary_surfaces": ["bed", "wall", "floor"],
  "furniture": ["bed", "nightstand"],
  "lighting": {
    "key": "large soft window left",
    "fill": "weak warm bounce",
    "practical": "lamp in background"
  },
  "camera_blocking_constraints": ["do_not_crop_feet", "show_two_full_bodies"],
  "audio_room_profile": "small_soft_furnished_room"
}
```

## Camera plan

Every shot must define:

- lens look: 24mm, 35mm, 50mm, 85mm, macro, telephoto,
- camera distance,
- camera height,
- angle: eye-level, low-angle, high-angle, overhead, side, rear, POV,
- zoom/framing: full body, knees-up, waist-up, bust, close-up, macro,
- depth of field,
- subject placement,
- occlusion expectations,
- characters that must remain fully visible.

## Frame integrity QA

QA must fail if:

- requested character count is wrong,
- full-body request crops feet/head/hands,
- multiple characters merge,
- foreground character blocks required target contact,
- camera angle contradicts shot plan,
- lens perspective is implausible for the requested shot,
- environment scale is wrong,
- background/furniture moves inconsistently across shots.
