# Wave 04 — Main Flow Deconstruction Report

Generated: `2026-07-05T20:04:41Z`

## Purpose

Wave 04 deconstructs the current Wave42 Main Flow into clear operational categories so future waves can safely extract it into production modules, subgraphs, API workflow templates, and App Mode controls.

This wave does **not** promote the current flow as final production architecture. It separates:

1. Active runtime/save lanes.
2. Preview-only UI lanes.
3. Note-only planning/promotion boundaries.
4. Disabled/disconnected LoRA catalog nodes.
5. Staged identity/control/inpaint/refine lanes.
6. Future module extraction targets.
7. Required fixes before runtime promotion.

The current main flow should now be treated as a **source/staging canvas**, not the final full hyper-realism system.

## Source file reviewed

- Source: `Wave42_Runtime_Bound__UI__WAVE42_MAIN_FLOW_20260702(4).json`
- Flow ID: `c1eb5a64-4997-472d-a6f5-93cc273d6a72`
- Revision: `0`
- SHA256: `13297484923fa1ca7525fa913792b19999f395e05118e50eb269e48e4d1bc8bb`

## Main counts

| Item | Count |
|---|---:|
| Total nodes | 356 |
| Links | 91 |
| Enabled / non-disabled nodes, mode 0 | 82 |
| Disabled / bypassed/catalog nodes, mode 2 | 274 |
| SaveImage terminal lanes | 8 |
| PreviewImage nodes | 8 |
| Note nodes | 13 |
| Ordinary LoRA catalog nodes | 274 |

## High-level verdict

The flow is structurally useful, but it is still not the final autonomous system.

The active runtime section can generate images through several SaveImage lanes, but many things that sound like production capabilities are currently boundaries, staged smoke tests, fixed-input test lanes, or disabled model catalog entries.

The AI project manager must not interpret a node's existence as proof that the capability is complete.

## Active SaveImage lanes

| Save prefix | Stage | Wave 04 status |
|---|---|---|
| `Main_Flow/SDXL_RealVisXL_LoRA` | base or primary | Deconstruct; verify engine/model alignment before promotion. |
| `Main_Flow/Flux_Family_ZImage` | base Z-Image | Deconstruct; eligible for module extraction. |
| `Main_Flow/SDXL_RealVisXL_LoRA_Upscaled` | upscale | Deconstruct; extract as final upscale/polish module. |
| `Main_Flow/SDXL_Inpaint_Detail` | masked detail staged | Must be rebuilt as pass-planner-fed image + mask input. |
| `Main_Flow/Flux_to_SDXL_Refine` | bridge/refine | Naming/source relationship must be corrected and formalized. |
| `Main_Flow/True_Flux_Schnell_Reference_Smoke` | smoke test | Keep as smoke/test only, not production primary. |
| `Main_Flow/IPAdapter_Face_Reference` | identity reference staged | Rebuild as per-character masked identity module. |
| `Main_Flow/ControlNet_Canny_Edge` | control reference staged | Rebuild with control-map generation, manifesting, and QA. |

Machine-readable details are stored in:

- `10_REGISTRIES/main_flow_wave04_runtime_lanes.json`
- `10_REGISTRIES/main_flow_wave04_runtime_lanes.csv`

## Note-only boundaries

The flow contains 13 Note nodes. These are important, but they are not runtime implementation proof.

Key note boundary groups:

| Boundary group | Meaning |
|---|---|
| Main flow intro | Establishes the Wave42 image-generation canvas. |
| Reference/IPAdapter/ControlNet staging | Identity, pose/depth/edge/mask control, and regional inpaint are planned/staged. |
| Video/audio handoff boundary | Image outputs are ready for future video lanes, but WAN/Hunyuan/LTXV/audio remain separate until proven. |
| True Flux image-reference conditioning boundary | Actual image-reference conditioning is not fully wired/proven. |
| Inpaint/upscale/QA/release boundary | Basic image lanes exist, but promotion and full creative QA still require proof. |
| IG-09/IG-10 QA and promotion boundary | Runtime files and passing evidence are required before promotion. |
| Wave42 LoRA library boundary | Deployed LoRAs are manifest-wired as disabled/disconnected references. |

Machine-readable note boundary inventory is stored in:

- `10_REGISTRIES/main_flow_wave04_note_boundaries.json`
- `10_REGISTRIES/main_flow_wave04_note_boundaries.csv`

## Disabled LoRA catalog deconstruction

The flow contains 274 ordinary `LoraLoader` nodes. All are mode `2`, disabled/disconnected, and tagged as `wave42_lora_library_node`.

This means:

- They are useful as a historical/catalog reference.
- They are **not** active production graph logic.
- They should be migrated to registry files and profile stacks.
- They should not remain embedded in the production runtime canvas.
- The AI project manager must never enable all of them at once.

Catalog engine counts:

| Engine/category marker | Count |
|---|---:|
| SDXL | 128 |
| Flux | 125 |
| Pony | 3 |
| SD1.5 | 3 |
| Disabled review / unresolved | 15 |

Catalog status counts:

| Status | Count |
|---|---:|
| Installed | 138 |
| Path verified | 79 |
| Rejected or superseded | 45 |
| Disabled review | 12 |

Raw machine inventory is stored in:

- `10_REGISTRIES/main_flow_wave04_lora_catalog_inventory_raw.json`
- `10_REGISTRIES/main_flow_wave04_lora_catalog_inventory_raw.csv`

Some source asset labels contain body-part or descriptive terminology because they come from the user-provided model library. Human-facing reports should summarize them by engine, category, scene role, status, and hash rather than expanding explicit names.

## Critical architecture findings

1. **Current graph is a staging canvas, not final architecture.**  
   It has active image lanes, but future production must be modular and orchestrated.

2. **The disabled LoRA library must leave the production canvas.**  
   It belongs in a model registry, Civitai metadata registry, engine compatibility registry, and profile stack registry.

3. **The active stack requires compatibility verification.**  
   The active stack is shared by multiple lanes. It must be checked against the loaded checkpoint before any promotion.

4. **Some lane names do not fully match the actual upstream model/source path.**  
   Wave 04 marks these for correction instead of silently accepting the naming.

5. **Fixed LoadImage/LoadImageMask inputs must be replaced.**  
   The autonomous system needs pass-planner-fed images, masks, and control maps.

6. **Note nodes must be converted into real workflows, scripts, schemas, and QA gates.**  
   Notes are useful design intent, not runtime proof.

7. **Creative QA is still separate from file QA.**  
   Decodable image files are not enough. Future waves must validate identity, frame, pose, mask, body/hand integrity, interaction/contact, and temporal consistency.

## Required output of Wave 04

Wave 04 produces:

- Deconstruction inventory.
- Node classification registry.
- Lane extraction plan.
- Note-boundary inventory.
- Disabled catalog inventory.
- Fix/update/connect/improve list.
- AI PM checklist.
- QA gates for future module extraction.

Wave 04 does not produce final ComfyUI runtime workflows yet. That begins in later waves after module boundaries are defined.
