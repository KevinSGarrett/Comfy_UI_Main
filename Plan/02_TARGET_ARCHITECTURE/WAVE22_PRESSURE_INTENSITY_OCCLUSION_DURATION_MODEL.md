# Wave 22 Pressure, Intensity, Occlusion, and Duration Model

## Pressure
Pressure describes how strongly the source affects the target surface.

Levels:
- none
- feather
- light
- medium
- firm
- heavy

## Intensity
Intensity describes the visual consequence of pressure.

Levels:
- none
- subtle
- visible
- strong
- extreme_blocked_by_default

## Occlusion
Occlusion defines what must be hidden or partially hidden.

States:
- none
- partial_edge
- partial_region
- majority_region
- full_region
- ambiguous_blocked

## Duration
Duration is required for video/audio planning.

Duration classes:
- instantaneous
- brief
- held
- sustained
- repeated
- rhythmic
- unresolved

## Expected deformation
The edge must declare whether it expects:
- no deformation
- skin/fabric contact shadow only
- surface compression
- soft-body indentation
- fabric stretch/cling
- hard-surface support flattening
- rebound / release recovery
