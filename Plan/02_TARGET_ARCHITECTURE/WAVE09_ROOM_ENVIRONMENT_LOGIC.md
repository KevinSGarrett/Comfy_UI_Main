# Wave 09 Room and Environment Logic

## Room graph
Every reusable room should be represented as a simple graph:

```text
room
├─ zones
│  ├─ foreground action zone
│  ├─ midground character zone
│  ├─ background prop zone
│  └─ camera-safe movement zone
├─ boundaries
│  ├─ walls
│  ├─ floor
│  ├─ ceiling
│  ├─ windows
│  ├─ mirrors
│  └─ doors
├─ occluders
│  ├─ furniture
│  ├─ foreground props
│  └─ architectural obstructions
└─ anchors
   ├─ character placement anchors
   ├─ prop anchors
   ├─ camera anchors
   └─ scale anchors
```

## Environment types
The registry supports:
- bedroom
- bathroom
- kitchen
- living room
- studio
- office
- hotel room
- hallway
- exterior residential
- exterior street
- vehicle interior
- fantasy/fictional interior
- product/still-life set
- custom set

## Required room fields
A room profile must define:
- room name
- environment type
- intended use
- camera-safe regions
- lighting-safe regions
- prop anchors
- floor/wall/ceiling material
- window/mirror locations
- background continuity details
- allowed camera angles
- disallowed camera angles
- scale anchors
- character placement constraints
- motion constraints for video

## Local coordinate model
The system does not need full CAD precision at first, but it needs stable references:
- `x_axis`: left/right in frame or room.
- `y_axis`: depth from camera.
- `z_axis`: height.
- `origin`: default character action point or room center.
- `camera_anchor`: named camera placement.
- `prop_anchor`: named prop placement.

## Scene Director instruction
The Scene Director must never invent a room layout after an environment is locked. It may request a new environment version, but it must not silently move doors, windows, mirrors, furniture, or lights unless the revision says to do so.
