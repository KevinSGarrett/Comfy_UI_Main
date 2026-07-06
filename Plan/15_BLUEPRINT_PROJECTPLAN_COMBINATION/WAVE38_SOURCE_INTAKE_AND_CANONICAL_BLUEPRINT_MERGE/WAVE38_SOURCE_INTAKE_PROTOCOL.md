# Wave 38 Source Intake Protocol

## Inputs
- current cumulative Wave37 system
- uploaded Plans package
- uploaded docs package
- working tracker CSV
- corrected reality-status CSV

## Intake result
All inputs are treated as source layers:

1. **Implementation baseline** — existing cumulative system.
2. **Instruction baseline** — blueprint/manual/technical project plan docs.
3. **Tracker baseline** — detailed task rows and acceptance evidence.
4. **Reality baseline** — corrected status and proof boundaries.

## Rule
When the instruction baseline and implementation baseline disagree, create a crosswalk entry and classify the gap instead of overwriting either side.
