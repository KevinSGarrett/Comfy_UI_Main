# Wave 13 — Mask Routing and Pass Binding

## Routing principle

A mask does not automatically mean an edit is allowed. The router decides which pass may use a mask.

## Allowed route examples

```text
person instance mask → identity protection / no-merge QA
face mask → low-denoise identity-preserving correction
hand mask → anatomy repair or detail pass
fabric mask → garment material detail pass
contact mask → contact shadow / occlusion repair
macro environment mask → lighting or environment continuity pass
```

## Blocked route examples

```text
face mask → unrestricted identity rewrite
person mask → wrong-engine LoRA stack
fabric mask → body-shape override
contact mask → high-denoise full-scene rewrite
nano mask → large pose or character change
```

## Router authority

The mask router must be enforced before ComfyUI workflow patching.
