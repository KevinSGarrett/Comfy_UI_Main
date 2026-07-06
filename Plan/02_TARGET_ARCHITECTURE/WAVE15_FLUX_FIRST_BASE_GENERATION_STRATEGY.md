# Wave 15 — Flux-First Base Generation Strategy

Flux-first means the router should prefer the best proven Flux-family base lane for general photoreal image starts.

It does **not** mean every pass must be Flux. It means:

1. Start with Flux2 once it is locally proven.
2. Otherwise start with Flux1 Dev once its workflow is proven.
3. Use SDXL/RealVisXL when an SDXL LoRA stack, inpaint/detail pass, or RealVisXL-specific checkpoint is required.
4. Use Z-Image as a separate fast alternative/fallback branch.
5. Use Pony only when a Pony-family checkpoint/profile is explicitly required.
6. Use SD1.5 only as legacy last resort.

## Flux2 inclusion

Flux2 is included as a first-class lane family. It is not promoted by default until:

- The required Flux2 nodes/loaders are visible in `/object_info`.
- The exact model assets are registry-backed with hashes and paths.
- A base workflow template has been exported to API format.
- A smoke output is generated and passes decode/composition QA.
- Reference-image behavior is separately proven before reference-heavy scenes use it.

## Flux1 current role

Flux1 Dev remains the current Flux-first target while Flux2 is being proven. Flux1 Schnell is treated as a smoke or fallback lane, not as the final quality default.

## Why SDXL remains critical

SDXL/RealVisXL remains critical because your model library and the current Main Flow include SDXL-compatible LoRA/detail/refine behavior. The router must preserve that ecosystem without mixing it into Flux model objects.

## Locked rule

```text
Flux-first is a routing preference, not a promotion shortcut.
```
