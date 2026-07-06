# Wave 20 Hard Anatomy Scene Director Binding

The Scene Director must turn user requests into explicit repair contracts.

## Examples
- "fix the hands" -> regions: hands/fingers; detect both hands; create crop repair contracts.
- "eyes look off" -> regions: eyes; check gaze, iris, pupil, catchlight symmetry.
- "fix the teeth" -> regions: mouth/teeth; local crop; identity and expression preservation.
- "feet are wrong" -> regions: feet/toes/ankles; verify contact support and perspective.
- "nails need detail" -> regions: nails only; micro/detail pass; no hand-shape change.

## Required output
- hard_anatomy_repair_contract
- crop_detail_repair_pass_plan
- local QA goals
- global preservation gates
