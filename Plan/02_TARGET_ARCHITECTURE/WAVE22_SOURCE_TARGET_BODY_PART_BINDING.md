# Wave 22 Source/Target Body-Part Binding

## Required binding fields
Every contact edge must define:

- `source_owner_id`
- `source_region_id`
- `source_region_type`
- `target_owner_id`
- `target_region_id`
- `target_region_type`
- `contact_edge_type`
- `ownership_confidence`
- `mask_ids`

## Ownership rules
1. Source and target must be distinguishable.
2. Multi-character contact must not merge bodies.
3. A hand, limb, object, or fabric region cannot affect a target unless its mask or detector evidence exists.
4. Source and target regions cannot be guessed from text alone.
5. If source and target are ambiguous, block promotion and request rerun/evidence.

## Body-part examples
- hand to shoulder
- hand to fabric
- arm to torso
- body to seat
- foot to floor
- prop to hand
- fabric to skin
- hair to face
