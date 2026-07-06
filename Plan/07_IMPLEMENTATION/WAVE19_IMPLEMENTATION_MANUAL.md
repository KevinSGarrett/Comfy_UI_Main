# Wave 19 Implementation Manual

## Build steps
1. Start with an approved Wave 15/17/18 image.
2. Generate or load person, body, clothing, prop, furniture, and contact-edge masks.
3. Compile a Wave 19 contact contract.
4. Validate the contact ownership graph.
5. Patch the workflow with source image, masks, prompt fragments, low-denoise sampler settings, and output paths.
6. Run contact/fabric/support passes.
7. Score evidence.
8. Promote only if no-floating, no-clipping, shadow, support, and continuity checks pass.
