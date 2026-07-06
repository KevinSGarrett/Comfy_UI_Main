# Wave 22 Contact Graph Workflow Build Instructions

## Workflow patch targets
- source image input
- source mask input
- target mask input
- contact boundary mask
- prompt conditioning for contact edge type
- negative conditioning for drift/floating/clipping
- low-denoise KSampler settings
- SaveImage prefix for edge evidence

## Recommended denoise ranges
- contact shadow repair: 0.10–0.20
- occlusion boundary repair: 0.15–0.28
- fabric/contact correction: 0.18–0.32
- soft-body indentation: 0.22–0.35
- strong deformation: blocked unless separately approved and QA-proven
