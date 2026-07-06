# Wave 07 Implementation Manual — LLM Scene Director

## Purpose

This manual explains how to implement the Scene Director inside `C:\Comfy_UI_Main`.

The Scene Director should be implemented as a plan generator and validator. It should not directly run ComfyUI.

## Recommended repo locations

```text
C:\Comfy_UI_Main\Implementation\scene_director\
C:\Comfy_UI_Main\Implementation\scene_director\schemas\
C:\Comfy_UI_Main\Implementation\scene_director\examples\
C:\Comfy_UI_Main\Implementation\scene_director\plans\
C:\Comfy_UI_Main\Implementation\scene_director\validators\
C:\Comfy_UI_Main\Implementation\scene_director\prompts\
```

## Minimal implementation components

1. `scene_director_request.schema.json`
2. `scene_director_plan.schema.json`
3. `director_profiles.json`
4. `intent_taxonomy.json`
5. `pass_compiler_rules.json`
6. `qa_goal_catalog.json`
7. `compile_scene_director_plan.py`
8. `validate_scene_director_plan.py`
9. `run_wave07_local_validation.py`

## Runtime flow

```text
user/app request
  -> create scene_director_request.json
  -> compile scene_director_plan.json
  -> validate scene_director_plan.json
  -> send pass_plan to workflow compiler
  -> workflow compiler patches workflow template JSON
  -> engine router validates selected engine/model pairs
  -> ComfyUI API runner executes
  -> evidence collector records outputs
  -> QA gate compares output to plan
```

## Minimum viable local test

1. Run the Wave07 local validation script.
2. Compile the example request into a plan.
3. Validate the example plan.
4. Confirm the pass plan contains at least one pass.
5. Confirm every pass has QA goals.
6. Confirm selected engine IDs are either in Wave06 engine registry or explicitly marked proof-gated.

## Production implementation notes

### Use structured output

The LLM should output JSON matching `scene_director_plan.schema.json`.

### Keep prompts separate from runtime

The prompt contract belongs in registry/config, not hard-coded into workflow JSON.

### Keep planning deterministic

Every plan should record:

- raw request
- normalized request
- assumptions
- selected profile
- intent
- model candidates
- engine route
- pass order
- QA goals
- blockers

### Make model selection registry-first

Do not search the file system blindly for models. Use the registry.

### Make execution proof-gated

A plan is not proof. Runtime proof needs actual output files and evidence manifests.

## CLI examples

```powershell
python .\07_IMPLEMENTATION\scripts\compile_scene_director_plan.py `
  --request .\09_EXAMPLES\wave07_scene_director_request.example.json `
  --out .\tmp\scene_director_plan.json

python .\07_IMPLEMENTATION\scripts\validate_scene_director_plan.py `
  --plan .\tmp\scene_director_plan.json

python .\07_IMPLEMENTATION\scripts\run_wave07_local_validation.py `
  --root .
```

## Next integration step

Wave08 should take the plan and bind it to character/identity registries. Wave14 later should compile it into actual workflow API JSON and orchestrate pass execution.
