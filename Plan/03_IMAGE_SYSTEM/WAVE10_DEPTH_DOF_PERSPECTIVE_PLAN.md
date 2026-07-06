# Wave 10 Depth, DOF, and Perspective Plan

## Depth Layers

Each camera plan may define:

```text
foreground
midground
background
```

For multi-character scenes, each character must have a depth order.

## Depth of Field

Depth of field is selected through `depth_dof_profile`:

- deep_focus
- natural_portrait_dof
- cinematic_shallow_dof
- macro_shallow_dof
- layered_depth

## Perspective Risks

- Wide lenses near bodies can distort limbs.
- Telephoto lenses in small rooms can flatten space unrealistically.
- Strong bokeh can hide required props or identity anchors.
- Macro shots can lose context.

## QA

Depth QA should verify:

- focus target is correct
- foreground does not hide required subject details
- background blur does not break environment continuity
- subject scale remains consistent
