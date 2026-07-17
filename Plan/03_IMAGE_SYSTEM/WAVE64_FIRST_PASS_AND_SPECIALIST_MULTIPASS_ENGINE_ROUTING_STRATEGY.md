# Wave64 First-Pass and Specialist Multipass Engine Routing Strategy

## First pass

The first pass is a capability route for `global_composition`, not a hardcoded FLUX node graph. Its request describes participant count, Character Package revisions, references, framing, pose/control needs, environment, text requirements, output resolution, hardware, quality/cost budget, and downstream editability.

The router may choose a FLUX, Qwen Image, SDXL, or another certified stack. It may also choose to generate composition separately from identity binding or pose enforcement when no single stack is proven for the combined task.

## Later passes

Each later pass re-enters the router. It does not inherit the base engine automatically. Common intents include:

- `identity_bind`, `view_consistency`, `count_and_layout`, `pose_enforce`, `depth_occlusion`;
- `body_morphology`, `hard_anatomy`, `contact_deformation`, `support_pressure`;
- `skin_microtexture`, `hair_strands`, `makeup`, `fabric_material`, `accessory_detail`;
- `face_detail`, `eye_teeth`, `hand_finger`, `foot_toe_nail`;
- `lighting_shadow_reflection`, `seam_cleanup`, `upscale_export`.

## Cross-engine example

```text
FLUX.2 global composition parent
  -> decoded image bridge
  -> Qwen Image Edit multi-reference identity/view candidate
  -> accepted parent
  -> trusted MaskFactory left-hand crop
  -> SDXL-only hand specialist at certified low denoise
  -> inverse transform and composite
  -> target hand QA
  -> owning character identity/morphology QA
  -> other character/protected-region QA
  -> whole-frame regression QA
```

The example is architectural. Exact stacks are selected only from current runtime and benchmark evidence.

## Causal rerouting

- Texture/detail failure -> retry specialist only with a material hypothesis.
- Seam/boundary failure -> adjust crop/feather/composite, not the accepted base.
- Identity drift -> return to identity binding or use a different eligible edit stack.
- Wrong anatomy/silhouette -> return to morphology/pose/mask, not more surface texture.
- Fused person/person or hand/object contact -> return to ownership/contact/pose.
- Persistent global composition error -> invalidate downstream children and route a new base hypothesis.

## Required QA

Every localized pass checks target improvement, non-target preservation, character identity/morphology, mask transform/boundary, seam/color/light coherence, and the entire frame. Multiple passes are not valuable if cumulative drift makes the whole image worse.
