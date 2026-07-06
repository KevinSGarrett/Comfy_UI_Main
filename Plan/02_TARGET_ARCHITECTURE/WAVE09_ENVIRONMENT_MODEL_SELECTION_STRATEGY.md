# Wave 09 Environment Model Selection Strategy

## Purpose
Environment assets can be checkpoints, LoRAs, ControlNets, IPAdapter references, depth maps, edge maps, material references, HDRI-like references, or prompt-only constraints. Wave 09 defines how those assets should be selected without corrupting character identity or engine compatibility.

## Selection hierarchy
1. Use the engine router from Wave 06.
2. Use the environment registry to identify required scene role.
3. Prefer same-engine assets for direct model/LoRA use.
4. Use image-based bridge when crossing engines.
5. Preserve character identity and locked environment fields.
6. Require local validation before EC2.

## Environment scene roles
- global_environment
- architecture_room
- background_detail
- lighting
- material_surface
- furniture_prop
- scale_reference
- reflection_mirror
- window_exterior
- final_polish

## Compatibility rules
- SDXL environment LoRA → SDXL image or inpaint pass.
- Flux environment LoRA → Flux pass.
- Pony/SD1.5 environment assets → specialty only unless explicitly routed.
- Flux/SDXL bridging → image output only, not latent/model/LoRA mixing.
- Video engines consume approved keyframes and environment manifests.
- Audio engines consume environment acoustic profiles, not image LoRAs.

## Promotion rule
A model asset may support an environment only after:
- it has a registry entry,
- source/hash/path are recorded,
- engine family is known,
- recommended role is defined,
- negative conflicts are recorded,
- a smoke output exists,
- QA says it improves environment realism without breaking identity/scale.
