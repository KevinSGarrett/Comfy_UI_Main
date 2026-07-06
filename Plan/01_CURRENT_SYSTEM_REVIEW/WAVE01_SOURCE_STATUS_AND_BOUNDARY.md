# Wave 01 Source Status and Boundary

## Current uploaded sources reviewed

| Source | Role | Wave 01 handling |
|---|---|---|
| Previous Wave 00 35-wave ZIP | Baseline cumulative pack | Extended into Wave 01 cumulative pack |
| Tracker CSV | Ongoing project tracker | Mutable upstream source, not frozen |
| Plans ZIP | Ongoing build/plans source | Mutable upstream source, not frozen |
| Advanced additions ZIP | Advanced feature requirements | Already mapped into 35-wave plan; must remain traceable |
| Assistant replies ZIP | Conversation requirement source | Used as requirement context |
| Current main flow JSON | Current runtime-bound ComfyUI source | Reviewed as current graph input, not final repo architecture |

## Tracker summary

The tracker CSV was read with `12887` rows and `73` columns.

Current status distribution:

```json
{
  "Not Started": 12870,
  "Package Marked Complete; Verify Local": 16,
  "Package Received": 1
}
```

Interpretation:

- The tracker is mostly not started.
- Existing completed/verify-local entries must be treated as evidence candidates, not automatic final proof.
- Wave 01 does not override tracker IDs. It adds repo/bootstrap structure that the tracker can later adopt.

## Plans ZIP summary

The Plans ZIP contains `6307` entries and about `37528138` uncompressed bytes.

Interpretation:

- The Plans ZIP is a large ongoing planning corpus.
- It contains historical schedules, delivery reports, manifests, and implementation planning.
- Wave 01 does not replace it. Wave 01 creates a cleaner 35-wave AI-PM-facing structure and maps future useful pieces into that structure.

## Main flow summary

The current runtime-bound main flow contains:

```json
{
  "node_count": 356,
  "link_count": 91,
  "last_node_id": 411,
  "last_link_id": 109,
  "mode_counts": {
    "0": 82,
    "2": 274
  },
  "lora_node_count": 275,
  "disabled_lora_node_count": 274,
  "save_image_prefixes": [
    "Main_Flow/SDXL_RealVisXL_LoRA",
    "Main_Flow/Flux_Family_ZImage",
    "Main_Flow/SDXL_RealVisXL_LoRA_Upscaled",
    "Main_Flow/SDXL_Inpaint_Detail",
    "Main_Flow/Flux_to_SDXL_Refine",
    "Main_Flow/True_Flux_Schnell_Reference_Smoke",
    "Main_Flow/ControlNet_Canny_Edge",
    "Main_Flow/IPAdapter_Face_Reference"
  ]
}
```

Interpretation:

- The graph is useful as a current source canvas.
- It should not become the Git repo architecture.
- It should be stored under `workflows/ui/current/` and later decomposed into workflow modules.
- The large disabled LoRA library should remain metadata/catalog until the engine router and mask factory can prove correct use.

## Wave 01 boundary

Wave 01 is repo, source, and cost-control infrastructure. It does not modify the actual main flow graph, and it does not run GPU generation.
