# Wave 09 Material, Surface, and Lighting Locking Plan

## What must be locked
- wall/floor/ceiling materials,
- furniture materials,
- fabric surfaces,
- reflective surfaces,
- wet or glossy surfaces,
- window/mirror behavior,
- contact shadow direction,
- light source positions,
- exposure/mood.

## Pass behavior
A pass may improve material detail but must not change the material class unless the scene plan explicitly says so.

## Examples
- A wood table should remain wood after inpaint.
- Cotton bedding should not become plastic.
- A mirror must keep reflection behavior.
- Wet floor must keep reflections and highlights.
- Lamp light must cast compatible shadows.
- Skin and fabric should respond to the same lighting rig.

## QA signs of failure
- material class changes,
- contact shadow disappears,
- reflection becomes impossible,
- scale anchor warps,
- lighting direction changes,
- furniture moves without revision.
