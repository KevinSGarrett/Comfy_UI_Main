# Wave 15 — Base Generation Prompt and Negative Contracts

Base generation prompts must be compiled from the structured Scene Director plan, not handwritten as one loose prompt blob.

## Positive prompt sections

- Subject and action summary
- Character identity bindings
- Environment and room binding
- Camera/framing plan
- Pose and blocking summary
- Lighting/material summary
- Realism/style intent
- Engine-specific syntax only when appropriate

## Negative prompt sections

- Quality failures
- Anatomy failures
- Composition failures
- Identity drift
- Background/environment drift
- Text/watermark failures
- Engine-specific negatives

## Engine differences

Flux-family prompts should stay cleaner and more natural-language structured. SDXL can accept controlled tag-weighting when the checkpoint requires it. Pony-family prompts need their own profile and should not be pushed through the Flux/SDXL default path. Z-Image requires its own prompt profile and sampler expectations.

## Prompt patching

The orchestrator patches prompt nodes using named patch targets. It must preserve the original workflow file and write a new patched execution copy for each run.
