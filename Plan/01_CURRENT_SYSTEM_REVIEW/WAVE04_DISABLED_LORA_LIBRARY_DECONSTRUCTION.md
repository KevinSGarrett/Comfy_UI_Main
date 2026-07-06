# Wave 04 — Disabled LoRA Library Deconstruction

## Purpose

The current Main Flow contains a large manifest-wired LoRA library region. This is useful for history and inventory, but it is not how the final production system should operate.

## Current facts

| Item | Count |
|---|---:|
| Ordinary `LoraLoader` catalog nodes | 274 |
| Disabled / mode 2 catalog nodes | 274 |
| Nodes already marked active copy in metadata | 3 |
| Installed status | 138 |
| Path verified status | 79 |
| Rejected/superseded status | 45 |

## Required future handling

The final production system must not keep hundreds of catalog LoRA nodes in the main runtime graph.

Move this information into:

1. Civitai model metadata registry.
2. Local/S3/EC2 model asset manifest.
3. Engine compatibility registry.
4. Pass-role registry.
5. Model profile stack registry.
6. QA/promotion status registry.

## Registry-first behavior

The autonomous pass planner should select LoRAs like this:

1. Read the user scene request.
2. Convert it into a pass plan.
3. Identify the target engine for that pass.
4. Query the model registry for compatible assets.
5. Select only approved assets for the exact pass role.
6. Patch the ComfyUI API workflow with selected LoRA paths/weights.
7. Run validation.
8. Block promotion if compatibility fails.

## Human-facing naming policy

Some source model filenames contain adult/sensitive labels. For human-facing summaries, use:

- engine
- category
- scene role
- status
- verification tier
- hash
- safe internal ID

Do not expand explicit model names in ordinary reports unless required for internal machine validation.
