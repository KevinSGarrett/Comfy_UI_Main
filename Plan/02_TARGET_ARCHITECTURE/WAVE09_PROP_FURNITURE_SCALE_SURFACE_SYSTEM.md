# Wave 09 Prop, Furniture, Scale, and Surface System

## Purpose
Props, furniture, and surfaces are realism anchors. If they drift, change size, disappear, or cast wrong shadows, the image/video becomes visibly fake.

## Prop registry
Every reusable prop should have:
- prop ID
- prop type
- display name
- approximate scale class
- material
- surface behavior
- allowed environments
- allowed positions
- contact behavior
- occlusion behavior
- shadow behavior
- reflection behavior
- continuity priority
- replacement rules
- allowed edits
- disallowed edits

## Furniture registry
Furniture is treated as a high-priority prop because it controls scale and physical plausibility:
- bed
- couch
- chair
- table
- desk
- counter
- shelf
- rug
- mirror
- lamp
- curtains
- doors/windows
- bathroom fixtures
- kitchen fixtures

## Scale anchors
The system should use visible anchors to maintain body, room, and object proportions:
- doors/windows
- bed/chair/couch/table
- floor tiles/planks
- lamps
- mirrors
- handles/knobs
- handheld objects
- wall outlets/switches
- human body landmarks

## Surface realism
Surfaces should track:
- roughness
- reflectivity
- wetness
- fabric behavior
- wrinkles/folds
- scratches/wear
- dust/dirt
- contact marks
- pressure/contact shadows
- reflection softness
- translucency

## Physical contact expectations
When a character touches a surface or prop, QA must check:
- contact shadow exists,
- body/prop overlap is plausible,
- surface/object scale matches body,
- hand/foot/body placement is not floating,
- material response matches surface type,
- pose and prop geometry do not contradict each other.
