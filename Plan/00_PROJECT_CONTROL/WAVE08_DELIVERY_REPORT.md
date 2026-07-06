# Wave 08 Delivery Report — Character Bible and Identity Registry

## Goal

Lock character identity, body, skin, hair, outfit, voice, and continuity references so the system can reuse the same character across images, passes, videos, GIFs, and audio without prompt drift.

## Delivered

Wave 08 adds a complete character-control layer:

1. Character Bible architecture.
2. Character identity registry.
3. Per-character reference-pack folder layout.
4. Body, skin, hair, outfit, voice, and continuity contracts.
5. Scene Director binding rules.
6. Model/LoRA selection rules for characters.
7. Multi-character identity separation rules.
8. Local validation scripts.
9. Schemas and examples.
10. QA gates for continuity and promotion.

## Source Reconciliation

The following sources were re-ingested as mutable upstream sources:

| Source | Status | Use in Wave 08 |
|---|---:|---|
| Wave 07 cumulative pack | Current base | Cumulative source copied into Wave 08 root. |
| Wave42 Main Flow JSON | Runtime-bound source canvas | Used to confirm current executable lanes, reference staging, LoRA catalog, and promotion boundaries. |
| Wave42 working tracker CSV | Ongoing tracker | Used for row/column/source status and future traceability. |
| Plans ZIP | Ongoing planning source | Summarized but not treated as frozen truth. |
| Advanced Additions ZIP | Ongoing advanced source | Summarized and kept aligned with future soft-body, micro-motion, and state-continuity waves. |
| Assistant replies ZIP | Ongoing instruction source | Summarized as conversation-derived planning support. |

## Inventory Snapshot

```json
{
  "main_flow_nodes": 356,
  "main_flow_links": 91,
  "save_image_lanes": 8,
  "lora_catalog_nodes": 274,
  "tracker_rows": 12887,
  "tracker_columns": 73
}
```

## Promotion Status

Wave 08 validates blueprint files, schemas, examples, and local scripts. It does **not** claim runtime identity consistency proof. Runtime proof remains blocked until reference packs exist and generated outputs are scored against the Character Bible.
