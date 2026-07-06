# Wave 18 Surface-State Continuity Contracts

A surface-state continuity contract binds every realism request to:
- an owned region mask
- a target surface profile
- a compatible engine family
- a denoise boundary
- a continuity acceptance threshold

## Continuity dimensions
1. **Texture continuity** — pore size, cellulite intensity, fabric weave, skin roughness.
2. **Tone continuity** — skin hue/value shifts must remain plausible.
3. **Specular continuity** — oil/sweat/wetness must follow scene lighting.
4. **Pressure continuity** — indentions/compression marks must line up with contact geometry.
5. **Temporal continuity** — video/GIF frames cannot flicker from dry to wet or from smooth to heavily textured without a declared event.

## Hard blocks
Reject the pass if it causes:
- identity drift
- pose drift
- body-shape drift
- frame/crop drift
- clothing seam corruption
- texture pasted outside the owned region
