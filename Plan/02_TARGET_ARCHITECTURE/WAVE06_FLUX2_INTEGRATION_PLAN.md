# Wave 06 Flux2 Integration Plan

## Decision
Flux2 is now included as a first-class planned engine family in the system.

## Flux2 roles
Flux2 should be evaluated for:

- high-quality photoreal base image generation
- stronger structured prompt following
- multi-reference consistency
- identity/reference edits
- image editing
- complex camera/environment/framing prompts
- possible reduction of some SDXL specialty passes when Flux2 handles the task better

## Flux2 variants

### `flux2_dev_local`
Planned high-quality local/EC2 candidate.

Use for:
- final or near-final image base candidates
- reference-driven generation
- complex prompt adherence tests
- identity consistency tests
- high-quality image editing tests

Do not use for:
- cheap local previews before proving speed/cost
- SDXL/Pony/SD1.5 LoRA stacks
- production before runtime proof

### `flux2_klein_preview`
Planned fast local preview/edit candidate.

Use for:
- low-cost previews
- quick composition tests
- interactive image-editing experiments
- proxy render before expensive Flux2 dev or video runs

Do not use for:
- automatic final hero output
- LoRA-heavy Civitai stacks unless proven compatible

### Flux2 API variants
Optional, not core local architecture.

Potential roles:
- comparison benchmark
- typography/text-heavy outputs
- high-quality fallback if local/EC2 setup cannot run a Flux2 variant efficiently
- external reference for QA comparison

Requirement:
- must be behind API key, cost limit, logging, and approval gates
- must never be a hidden dependency for local/offline builds

## Required local model slots
The registry must not rely on filenames alone. For each Flux2 variant, record:

- model family
- model variant
- diffusion model filename
- text encoder filename
- VAE filename
- hash
- source URL or local source note
- S3 URI
- local cache path
- EC2 cache path
- required ComfyUI version
- required node classes
- expected VRAM profile
- allowed pass types
- compatible LoRA family
- promotion status

## Runtime proof checklist
Flux2 cannot be promoted until all are true:

1. Local or EC2 ComfyUI starts.
2. `/object_info` shows the required Flux2 node classes.
3. Required model files resolve from configured model folders.
4. A text-to-image Flux2 workflow runs.
5. An image-edit/reference Flux2 workflow runs.
6. Output files are saved and hashed.
7. Model hash, prompt, seed, dimensions, runtime logs, and workflow hash are recorded.
8. Visual QA compares Flux2 against Flux1 and SDXL/RealVisXL baselines.
9. Router marks Flux2 route as `production_candidate` or keeps it blocked.

## Compatibility with current system
Flux2 should not replace SDXL/RealVisXL immediately. Your current model library is heavily Civitai-driven, and many of those LoRAs are SDXL, Flux1, Pony, or SD1.5 specific. Flux2 adds a new family. It does not make older assets compatible by default.

## Best initial integration sequence
1. Add Flux2 registry entries.
2. Add Flux2 asset manifest placeholders.
3. Add Flux2 workflow template placeholders.
4. Add Flux2 `.env`/path variables.
5. Validate local paths without EC2.
6. Capture `/object_info`.
7. Run a tiny Flux2 smoke workflow.
8. Compare Flux2 output against current SDXL/Flux1 baseline prompts.
9. Add Flux2 to router only for the exact pass types it proves.
