# Wave 04 — Main Flow Deconstruction QA Gates

## Purpose

Wave 04 QA ensures the AI project manager does not confuse staged graph content with production-ready capability.

## QA Gate W04-01 — Source file readable

Pass criteria:

- Main Flow JSON is readable.
- JSON parses without errors.
- Flow has nodes and links.

## QA Gate W04-02 — Static graph inventory complete

Pass criteria:

- Node count captured.
- Link count captured.
- Node type counts captured.
- Mode counts captured.
- SaveImage lanes captured.
- PreviewImage nodes captured.
- Note nodes captured.
- LoRA catalog nodes captured.

## QA Gate W04-03 — Runtime lane extraction complete

Pass criteria:

- Every SaveImage terminal has a lane record.
- Each lane record includes upstream node count.
- Each lane record includes sampler settings where available.
- Each lane record includes model/loader summary.
- Each lane record includes required fixes or promotion blockers.

## QA Gate W04-04 — Note boundaries classified

Pass criteria:

- Every Note node is listed.
- Boundary type is assigned.
- Note-only status is explicit.
- No note is treated as runtime proof.

## QA Gate W04-05 — LoRA catalog deconstructed

Pass criteria:

- Every disabled LoRA catalog node is listed.
- Engine counts generated.
- Status counts generated.
- Rejected/superseded records remain disabled.
- All catalog nodes are marked as registry candidates, not active runtime nodes.

## QA Gate W04-06 — Fix list generated

Pass criteria:

- Engine compatibility verification is listed.
- Hardcoded prompt replacement is listed.
- Fixed LoadImage/LoadImageMask replacement is listed.
- Static control-map replacement is listed.
- File QA vs creative QA separation is listed.
- Module extraction targets are listed.

## QA Gate W04-07 — Cumulative pack integrity

Pass criteria:

- Previous Wave 00–03 files are preserved.
- Wave 04 files are added without deleting prior content.
- JSON files parse.
- CSV files are non-empty where expected.
- Release validation report is generated.

## Promotion result

Wave 04 itself is **not** a production runtime promotion wave.

Allowed result:

- `wave04_deconstruction_complete`

Blocked results:

- `production_runtime_promoted`
- `main_flow_finalized`
- `all_lora_catalog_nodes_active`
- `note_only_boundary_treated_as_runtime_proof`
