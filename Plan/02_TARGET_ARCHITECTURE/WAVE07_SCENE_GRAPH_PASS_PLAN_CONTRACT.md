# Wave 07 Scene Graph and Pass Plan Contract

## Contract purpose

The Scene Director outputs must be strict enough that a separate system can compile them into workflow modules without guessing.

This file defines the contract between:

- LLM Scene Director
- workflow compiler
- engine router
- ComfyUI API runner
- QA/promotion gate

## Scene graph contract

A scene graph must answer:

1. Who or what is in the scene?
2. Where is it happening?
3. What is each subject doing?
4. What is the camera supposed to show?
5. What surfaces/materials/props matter?
6. What relationships/contact/occlusion exist?
7. What must not change?
8. What must QA verify?

## Required scene graph objects

### Character object

```json
{
  "character_id": "char_001",
  "role": "primary_subject",
  "description": "implementation-friendly character description",
  "identity_reference_ids": [],
  "body_targets": [],
  "wardrobe": [],
  "pose": "pose description",
  "depth_order": 1
}
```

### Environment object

```json
{
  "environment_id": "env_001",
  "description": "room/world description",
  "location_type": "interior_room",
  "lighting": "natural light",
  "materials": ["wood floor", "fabric", "painted wall"],
  "scale_constraints": ["subject scale must match furniture scale"]
}
```

### Contact relationship object

```json
{
  "contact_id": "contact_001",
  "source_entity_id": "char_001",
  "source_region": "hand",
  "target_entity_id": "char_001",
  "target_region": "fabric or body region",
  "contact_zone": "specific contact area",
  "pressure_level": "light|medium|firm",
  "required_visual_effects": ["shadow", "small indentation", "no fused fingers"],
  "qa_goal_ids": ["qa_contact_graph", "qa_mask_no_bleed"]
}
```

## Pass plan contract

A pass is a planned operation, not a runtime result.

Each pass must define:

- pass ID
- pass type
- engine ID
- workflow module ID
- model IDs
- mask IDs
- inputs
- outputs
- QA goal IDs
- promotion gate
- runtime proof requirement

## Pass ordering rules

### Base first

Major composition, camera, pose, and environment must be solved in the base generation or layout pass. Do not try to fix a fundamentally wrong camera crop through a microdetail pass.

### Shape before texture

Body/silhouette/proportion changes happen before micro texture.

### Contact before final polish

Interaction/contact/occlusion/deformation passes happen before final skin/fabric/nano polish.

### Detail last

Skin, fabric, pores, hair, small highlights, and final polish come after the geometry and interaction are approved.

### Upscale near end

Upscale only after major creative defects are fixed.

### QA after every required pass

Each pass declares QA before runtime. Failed QA determines whether the system reruns base, reruns a regional pass, or blocks promotion.

## Cross-engine rules

Cross-engine bridging is allowed only through approved image files.

Allowed:

```text
Flux2 base image -> Save image -> SDXL image load -> low-denoise inpaint/detail
SDXL keyframe -> Save image -> video engine keyframe input
```

Not allowed:

```text
Flux2 model object -> SDXL LoRA stack
SDXL latent -> Flux sampler
Pony LoRA -> Flux checkpoint
SD1.5 ControlNet -> SDXL latent without compatibility adapter
```

## Promotion contract

An output cannot be promoted unless:

- scene plan exists
- pass plan exists
- required runtime outputs exist
- output files are decoded and hashed
- required masks/evidence exist
- selected models match engine family
- QA goals pass
- no unresolved blockers remain
