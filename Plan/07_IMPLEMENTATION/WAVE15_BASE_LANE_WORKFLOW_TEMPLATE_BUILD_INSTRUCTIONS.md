# Wave 15 — Base Lane Workflow Template Build Instructions

Each base lane template must be split into a clean workflow JSON that can be patched and submitted through ComfyUI API.

## Template requirements

- Clear lane ID in metadata.
- One primary SaveImage output prefix.
- Named patch targets for positive prompt, negative prompt, seed, resolution, sampler, scheduler, checkpoint/model asset, LoRA stack profile, and output prefix.
- No API secrets or absolute private model binary paths in Git.
- Model and LoRA references must resolve through registries/manifests.

## Template minimum files

```text
workflow_templates/base_generation/<lane_id>/README.md
workflow_templates/base_generation/<lane_id>/patch_points.example.json
workflow_templates/base_generation/<lane_id>/runtime_requirements.example.json
```

## Runtime proof

A template is not promoted until:

- `/object_info` confirms all nodes.
- Model paths resolve.
- Run completes.
- Output is decoded.
- QA report passes.
