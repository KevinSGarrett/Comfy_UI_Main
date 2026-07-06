# Wave 07 Delivery Report — LLM Scene Director

Generated: 2026-07-05T22:15:56Z

## Delivered

Wave 07 adds the LLM Scene Director planning layer to the cumulative system blueprint.

## New capability

The system can now define how to convert a plain request into a structured plan containing:

- intent classification
- normalized request
- assumptions and ambiguity handling
- scene graph
- character/environment/action/contact graph
- camera and framing plan
- mask plan
- model-selection plan
- engine route
- ordered pass plan
- QA goal plan
- promotion blockers
- evidence requirements

## Important result

The Scene Director is the **planner**, not the executor.

Execution remains the job of:

- Wave05 workflow modules/subgraphs
- Wave06 engine router
- ComfyUI API orchestrator
- local validation harness
- EC2 runtime proof gate
- QA/promotion system

## Files added

See `00_PROJECT_CONTROL/WAVE07_FILE_INDEX.md`.

## Validation

Wave07 static validation checks JSON parse, schema/example presence, director profile presence, pass compiler rules, QA catalog, scripts compile, and example plan contract.

Runtime proof remains required later.
