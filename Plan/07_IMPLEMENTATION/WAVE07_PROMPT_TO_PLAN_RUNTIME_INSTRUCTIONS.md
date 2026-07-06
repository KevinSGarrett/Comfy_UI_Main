# Wave 07 Prompt-to-Plan Runtime Instructions

## LLM instruction template

The Scene Director LLM should receive:

1. System role.
2. Current project rules.
3. Engine registry summary.
4. Model-selection rules.
5. Mask taxonomy.
6. QA catalog.
7. User request.
8. Output JSON schema.

## Required behavior

The LLM must:

- return valid JSON only when used in automated mode
- preserve the user's core request
- normalize implementation details
- record assumptions
- not invent file paths or model IDs
- mark missing model metadata as `needs_metadata`
- mark Flux2 as `needs_runtime_proof` until proven
- create QA goals before any pass
- create promotion blockers
- avoid direct cross-engine model/LoRA mixing

## Ambiguity behavior

Use `make_best_effort` by default.

Create blocking questions only when a missing reference or contradiction prevents a usable plan.

## Example non-blocking ambiguity

User says:

```text
Make it more realistic.
```

Director may assume:

- target output image if current input is image
- hyperreal material detail
- small regional detail pass
- preserve camera/composition unless user asks to change it

## Example blocking ambiguity

User says:

```text
Use the photo I sent.
```

But no photo exists in the current job context. The Director should mark the plan blocked and request the missing reference asset.

## Prompt sections

Recommended prompt sections:

```text
ROLE
You are the Scene Director planner. Produce structured plans only.

PROJECT RULES
Models stay out of Git. Engine families cannot be mixed. Scene plan before runtime. QA before promotion.

INPUT
<scene_director_request.json>

AVAILABLE REGISTRIES
<engine registry summary>
<model registry summary>
<mask taxonomy>
<qa catalog>

OUTPUT
Return scene_director_plan JSON following schema.
```

## Validation

After LLM output:

1. Parse JSON.
2. Validate required top-level fields.
3. Validate engine IDs.
4. Validate model candidate statuses.
5. Validate pass plan has QA goals.
6. Validate promotion blockers exist.
7. Reject or repair if invalid.
