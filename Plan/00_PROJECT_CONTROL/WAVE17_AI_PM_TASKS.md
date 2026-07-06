# Wave 17 AI PM Tasks — Body Shape and Proportion Correction

## Wave objective
Build the body-shape correction layer for stomach, waist, hips, thighs, silhouette, and body proportions using large owned masks, low-denoise correction passes, and QA gates.

## Why this wave exists
Earlier waves created the Scene Director, Character Bible, Camera/Framing system, Control Maps, Mask Factory, Orchestrator, Base Lanes, and Refine Bridge. Wave 17 connects those pieces into a specific body-correction subsystem so the system can correct body proportions without corrupting the base image.

## Required outcome
A body correction request must compile into:

1. character_id and instance ownership,
2. source approved base image,
3. body target profile,
4. large region masks,
5. pass plan,
6. low-denoise settings,
7. same-engine model/LoRA selection rules,
8. QA goals,
9. rerun/fallback policy,
10. promotion decision.

## Locked implementation principles
- Never use full-image redraw for body correction unless the base image is rejected and regenerated.
- Never correct body shape without a person-instance mask.
- Never include face identity in a large body mask unless a separate face-protection pass exists.
- Never enable every body-related LoRA from the library.
- Never promote a body-corrected result without character count, frame, silhouette, identity, pose, mask edge, and clothing continuity evidence.

## Current source evidence
The current Main Flow has a real inpaint mask slot, an optional IPAdapter attention mask slot, SDXL inpaint/detail at denoise 0.28, Flux-to-SDXL refine at denoise 0.22, and body-shape/body-proportion candidate LoRAs that remain disabled/catalog entries until selected through a compatible pass profile.

## Wave 17 deliverables
- Body region taxonomy.
- Body target profiles.
- Body correction contract schema.
- Large-mask rules.
- Body correction pass profiles.
- QA scoring rules.
- Rerun policy.
- Main Flow inventory.
- Local validation scripts.
