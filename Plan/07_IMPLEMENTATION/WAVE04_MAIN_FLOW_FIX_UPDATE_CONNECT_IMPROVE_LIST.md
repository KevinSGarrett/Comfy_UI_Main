# Wave 04 — Main Flow Fix / Update / Connect / Improve List

## Purpose

This is the technical repair list that future waves must use when converting the current Main Flow into the final ultra-hyper-realism system.

## P0 — Must fix before any production promotion

### 1. Separate production graph from catalog graph

Current issue:

- The Main Flow contains a large disabled LoRA library inside the graph.
- Those nodes are useful metadata, but they are not production runtime logic.

Required fix:

- Move LoRA catalog data into:
  - `engine_compatibility_registry.json`
  - `civitai_model_registry`
  - `profile_stack_registry`
  - `model_asset_manifest`
- Keep only selected runtime LoRA stack nodes in production workflow templates.
- Block any automation from enabling all catalog nodes.

### 2. Verify active stack engine compatibility

Current issue:

- The active stack is shared across multiple lanes.
- Some stack labels and lane names require compatibility verification against the actually loaded checkpoint/model family.

Required fix:

- Every runtime pass must declare:
  - `engine_family`
  - `base_model`
  - `checkpoint_path`
  - `lora_paths`
  - `lora_engine_family`
  - `compatibility_status`
- A pass must fail validation if it mixes incompatible model/LoRA families.

### 3. Replace hardcoded prompt blocks

Current issue:

- The same long prompt is embedded in multiple CLIP encoders.
- The system cannot autonomously modify pass scope, frame, environment, pose, or character details cleanly.

Required fix:

- Prompt text must be generated from:
  - Scene Plan
  - Character Bible
  - Camera/Frame Plan
  - Environment Plan
  - Pass Plan
  - Mask Plan
- Each pass must receive only the prompt components relevant to that pass.

### 4. Replace fixed image/mask inputs

Current issue:

- Inpaint and control lanes use fixed filenames.
- This blocks autonomous pass chaining.

Required fix:

- Every module must accept:
  - source image path
  - source image hash
  - mask path
  - mask hash
  - optional control map path
  - previous pass output path
- Fixed `LoadImage` nodes may exist in UI templates only, not in API production templates.

### 5. Separate file QA from creative QA

Current issue:

- Existing notes describe basic file decode QA and promotion boundaries.
- File decode proof does not prove realism or correctness.

Required fix:

- Add creative QA gates for:
  - identity
  - pose
  - camera/framing
  - hand/face/body quality
  - mask bleed
  - body-part integrity
  - multi-character instance separation
  - interaction/contact plausibility
  - video temporal consistency
  - audio/AV sync

## P1 — Required for modular extraction

### 6. Extract base-generation module

Create separate workflow templates for:

- Flux base
- Z-Image base
- SDXL/RealVisXL base if retained
- Pony specialty only if deliberately selected
- smoke/test lanes

### 7. Extract refine/bridge module

Rules:

- Bridge through decoded image only.
- Re-encode with the target model/VAE.
- Log denoise and source/target hashes.

### 8. Extract inpaint/detail module

Rules:

- Always require mask.
- Always create mask overlay.
- Always save before/after crop.
- Never run with unknown mask coverage.

### 9. Extract identity module

Rules:

- Per character.
- Masked or cropped.
- Multi-character isolation required.

### 10. Extract control-map module

Rules:

- Generate control maps, do not rely only on static images.
- Save Canny/depth/normal/pose maps.
- Validate map dimensions and alignment.

## P2 — Cleanup and maintainability

### 11. Remove misleading lane names

A lane name must not claim an engine family or source path that does not match the actual upstream model/graph path.

### 12. Replace note-only boundaries with explicit tasks

Every note should become one of:

- workflow module
- registry
- schema
- QA gate
- orchestrator rule
- promotion blocker
- future-wave backlog item

### 13. Add module manifests

Every extracted module needs:

- module name
- workflow API JSON path
- required input files
- required model files
- required custom nodes
- output prefix
- QA gates
- promotion rules

### 14. Add deconstruction regression test

Any future change to the current Main Flow must regenerate:

- node classification
- lane inventory
- note boundary inventory
- catalog inventory
- fix list delta
