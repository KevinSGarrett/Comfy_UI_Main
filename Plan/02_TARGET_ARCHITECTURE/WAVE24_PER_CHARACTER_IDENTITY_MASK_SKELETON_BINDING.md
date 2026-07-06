# Wave 24 Per-Character Identity, Mask, and Skeleton Binding

## Binding contract
Every visible character needs a triad:

1. **Identity binding** — which character bible / reference pack owns the face, hair, body traits, wardrobe, and continuity target.
2. **Mask binding** — which person-instance mask and region masks belong to that character.
3. **Skeleton binding** — which pose/skeleton/control map belongs to that character.

## Hard failure
If identity, mask, and skeleton are not all assigned to the same instance id, the orchestrator must block promotion or reroute to instance-layout repair.
