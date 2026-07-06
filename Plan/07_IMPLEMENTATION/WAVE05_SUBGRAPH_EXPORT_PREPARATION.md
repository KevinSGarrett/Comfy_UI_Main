# Wave 05 — Subgraph Export Preparation

## Purpose

This document prepares the future conversion of module contracts into actual ComfyUI subgraphs.

## Required preparation before exporting a subgraph

1. Confirm module scope.
2. Confirm required inputs and outputs.
3. Confirm required node classes through `/object_info`.
4. Confirm model and LoRA references resolve through registries.
5. Confirm no disabled catalog nodes are included.
6. Confirm patch points are named.
7. Confirm output prefix is safe.
8. Confirm evidence manifest path exists.
9. Confirm runtime proof is available or explicitly deferred.

## Suggested folder layout

```text
workflows/
  source/
    Wave42_Runtime_Bound__UI__WAVE42_MAIN_FLOW_20260702.json
  templates/
    MOD-10-SDXL-BASE-LANE/
    MOD-11-ZIMAGE-BASE-LANE/
    MOD-13-SDXL-INPAINT-DETAIL-LANE/
  subgraphs/
    mask_factory/
    control_map_factory/
    upscale_export/
    evidence_manifest/
```

## Subgraph export procedure

1. Open the source workflow.
2. Select only the nodes for the module.
3. Convert to subgraph.
4. Promote required widgets only.
5. Name inputs and outputs cleanly.
6. Save subgraph JSON to versioned folder.
7. Run static validation.
8. Run object_info validation.
9. Run minimal runtime proof.
10. Record SHA256 of exported subgraph.

## Rollback

Every subgraph export must preserve the prior version. Never overwrite a known-good subgraph without retaining the previous file.
