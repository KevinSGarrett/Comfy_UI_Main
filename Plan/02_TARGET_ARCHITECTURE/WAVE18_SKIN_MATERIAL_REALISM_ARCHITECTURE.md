# Wave 18 Skin/Material Realism Architecture

Wave 18 is responsible for **localized surface realism** after the system already has an approved base image, approved body proportions, and approved frame integrity.

## Scope
- skin microdetail: pores, fine roughness, freckles, moles, blemishes, uneven tone
- skin macro surface state: cellulite, stretch marks, compression, pressure marks
- moisture state: matte, natural, dewy, sweaty, oiled, wet
- material response: fabric weave, elastic compression, sheen, wrinkles at contact edges
- continuity: the same surface logic must remain coherent across later passes and across adjacent video frames

## Non-scope
Wave 18 is not responsible for generating the first valid composition, fixing character count, solving the base pose, or performing large-shape body corrections. Those are handled in earlier waves.

## Default sequencing
1. approved base image
2. approved body/proportion pass if needed
3. Wave 18 surface realism passes
4. face/hands/contact repair as needed
5. final QA and promotion

## Surface pass philosophy
- **Small mask**: pores, freckles, isolated blemish cleanup, gloss tuning.
- **Medium mask**: thigh cellulite, stomach skin texture, pressure mark zones, upper-back texture.
- **Large mask**: region-wide continuity such as full thigh skin-state balancing or torso fabric sheen balancing.
- **Never globalize specialty surface LoRAs** when the request is region-specific.
