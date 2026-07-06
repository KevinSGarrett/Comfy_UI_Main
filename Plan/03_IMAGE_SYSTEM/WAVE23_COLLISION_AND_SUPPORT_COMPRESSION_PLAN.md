# Wave 23 Collision and Support Compression Plan

This wave does not simulate rigid-body or cloth physics numerically. It creates a visual approximation pipeline.

## Collision-looking repair goals
- prevent impossible body overlap from reading as merged anatomy,
- show plausible compression at support surfaces,
- preserve limb ownership,
- preserve clean occlusion order.

## Support compression examples
- thigh on chair cushion
- torso on mattress
- hand pressing soft tissue
- foot contact on soft surface
