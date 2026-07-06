# Wave 24 Implementation Manual

## Build objective
Implement a deterministic multi-character instance layout layer before multi-character scenes reach downstream passes.

## Required outputs
- instance layout contract
- per-character mask/skeleton/region plan
- depth order plan
- QA report
- rerun decision

## ComfyUI integration notes
The current Main Flow should be treated as the image canvas. Wave 24 does not require adding all instance logic directly into the UI graph first. The orchestrator should compile instance plans and patch the appropriate mask, prompt, ControlNet, IPAdapter, and inpaint/refine lanes.
