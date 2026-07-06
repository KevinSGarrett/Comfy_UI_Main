# Wave 13 — Mask to ComfyUI Patching Notes

## Current hooks

The current Main Flow has a VAEEncodeForInpaint mask input and an optional IPAdapter attention mask input.

## Future patching strategy

- Patch regional inpaint modules with validated mask paths.
- Patch attention/reference modules only with masks that match the target person or region.
- Record every patched node ID, input name, mask ID, and workflow output path.
- Do not patch masks directly into production lanes until validation passes.

## Required manifest

Every workflow patch should generate a manifest row:

```text
workflow_id, node_id, input_name, mask_id, mask_path, pass_id, output_prefix
```
