# ComfyUI Workflow Testing Protocol

## Purpose

This protocol governs QA for ComfyUI workflows, workflow JSON files, node graphs, and associated runtime execution.

## Required review areas

Codex must review:

- missing model files
- broken paths
- broken node references
- incompatible engine/model usage
- Flux / SDXL / Pony compatibility
- ControlNet compatibility
- LoRA loading
- sampler / scheduler correctness
- seed reproducibility
- output path correctness
- metadata capture
- failed nodes
- VRAM failure
- bad fallback behavior
- incomplete outputs
- missing logs

## Workflow QA process

### Stage 1 — Static inspection
- open workflow JSON or project representation
- validate required nodes exist
- validate referenced files and model paths
- verify engine-family compatibility
- verify expected outputs and save paths

### Stage 2 — Dependency resolution
- determine whether all required models, LoRAs, VAEs, and preprocessors are present locally or need retrieval
- verify naming consistency
- verify version expectations where known

### Stage 3 — Runtime execution
- run a representative test prompt or fixture
- capture stdout/stderr or application logs
- capture output files
- note runtime performance and failures

### Stage 4 — Output verification
- confirm files were produced
- confirm metadata capture where expected
- confirm outputs are complete and not partial / corrupt
- hand off outputs to image/video/audio QA if applicable

### Stage 5 — Reproducibility
- if reproducibility matters, re-run same seed and compare for expected stability

## Failure classes

- static schema/path failure
- dependency missing
- compatibility mismatch
- runtime crash
- VRAM / memory exhaustion
- output incomplete or corrupt
- output low quality despite successful execution
- logging / observability failure

## Minimum evidence

- workflow file path
- dependency check result
- runtime command or invocation method
- log path
- output artifact path(s)
- QA status
- next action
