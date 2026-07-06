# Wave 10 Delivery Report — Camera, Lens, Zoom, Angle, Framing

## Delivery Summary

Wave 10 adds the camera/framing control layer to the cumulative blueprint. The system now has explicit contracts for:

- full-body shots
- half-body shots
- medium shots
- close-ups
- extreme close-ups
- wide/environment shots
- two-shots
- group shots
- detail inserts
- lens profile
- camera angle
- zoom level
- camera height
- composition preset
- crop policy
- depth of field
- focus target
- multi-character subject slots

## Why This Wave Matters

Prompt-only camera control is unreliable. A request such as “full body” can still crop feet, hands, hair, props, or contact points. A request such as “close-up” can destroy identity if the system does not preserve face landmarks. Multi-character framing can blend people together unless subject slots, screen position, depth order, occlusion, and identity separation are declared.

Wave 10 solves this by making camera intent a structured object before generation.

## Current Main Flow Findings

```text
Nodes observed: 356
Links observed: 91
SaveImage lanes observed: 8
Latent size nodes: 5
IPAdapter nodes: 2
ControlNet nodes: 2
LoRA catalog nodes: 274
Pose/camera category nodes: 1
Camera-related LoRA title matches: 30
```

## New Wave 10 Files

See `00_PROJECT_CONTROL/WAVE10_FILE_INDEX.md` for the complete list.

## Locked Rule

```text
Camera request
→ camera_plan JSON
→ validation
→ workflow patch targets
→ engine/router check
→ runtime output
→ camera/framing/depth QA
→ promotion gate
```

## Runtime Boundary

Wave 10 does not claim that the current Main Flow already solves every camera case. It creates the contracts, registries, scripts, and QA rules needed to make future camera control testable and repeatable.
