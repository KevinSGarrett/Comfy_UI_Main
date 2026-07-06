# Wave 13 — Mask Naming Conventions

## Pattern

```text
{scene_id}__{owner_id}__{target_id}__{scale}.png
```

## Examples

```text
scene_001__person_001__whole_person__major.png
scene_001__person_001__face__minor.png
scene_001__person_001__fabric_full_garment__major.png
scene_001__contact_001__person_person_boundary__minor.png
scene_001__background__wall_zone__macro.png
scene_001__person_001__edge_halo_cleanup__nano.png
```

## Rule

Mask names must be deterministic so QA, reruns, and promotion can compare evidence reliably.
