# Current Main Flow Review Findings

## Source reviewed

- File: `Wave42_Runtime_Bound__UI__WAVE42_MAIN_FLOW_20260702.json`
- SHA256: `13297484923fa1ca7525fa913792b19999f395e05118e50eb269e48e4d1bc8bb`
- Nodes: 356
- Links: 91
- SaveImage outputs: 8
- Active upstream nodes feeding SaveImage outputs: 61
- Disabled/library LoRA loader nodes: 274

## Active SaveImage outputs

- Node 19: `Main_Flow/SDXL_RealVisXL_LoRA`
- Node 39: `Main_Flow/Flux_Family_ZImage`
- Node 62: `Main_Flow/SDXL_RealVisXL_LoRA_Upscaled`
- Node 87: `Main_Flow/SDXL_Inpaint_Detail`
- Node 95: `Main_Flow/Flux_to_SDXL_Refine`
- Node 107: `Main_Flow/True_Flux_Schnell_Reference_Smoke`
- Node 128: `Main_Flow/ControlNet_Canny_Edge`
- Node 118: `Main_Flow/IPAdapter_Face_Reference`

## Metadata-wired lanes

- SDXL/RealVisXL + organized Wave42 SDXL LoRA image generation
- Flux-family/Z-Image executable image generation
- SDXL RealESRGAN shared upscale lane staged as ready_to_verify
- SDXL inpaint/detail lane staged as ready_to_verify with explicit base/mask inputs
- Flux-family image into SDXL light img2img refinement staged as ready_to_verify
- True Flux Schnell reference-smoke/base lane staged as ready_to_verify
- SDXL IPAdapter face-reference lane staged as ready_to_verify
- SDXL ControlNet Canny edge-map lane staged as ready_to_verify
- Main Flow image QA/evidence export staged as ready_to_verify
- Main Flow promotion gate staged; verifies only after exact runtime proof exists

## Metadata note-only lanes

- True Flux image-reference conditioning branch
- Additional reference-slot routes beyond face_reference
- ControlNet pose/depth/openpose/tile variants beyond the Canny edge lane
- Video handoff
- Audio/AV sync

## Major findings

### 1. The graph is a runtime-bound image canvas, not a complete hyper-realism system

The metadata says the flow wires evidenced image-generation lanes and that unverified branches are notes. The flow must therefore be treated as a source artifact and staging canvas, not the final autonomous pipeline.

### 2. Most LoRA library nodes are disabled/catalog-only

The LoRA library exists for selection, not global activation. Future work must move LoRA selection out of the active graph into a registry and pass planner.

### 3. Pose/depth/openpose/tile variants are not proven runtime lanes

The current Canny lane exists, but deeper pose/depth/openpose control remains note-only. This directly explains poor pose/camera accuracy.

### 4. Video and audio are handoff boundaries

The main flow produces image outputs ready for downstream video lanes, but video and audio/AV sync are not merged/proven inside this main flow.

### 5. QA is not yet visual-truth QA

The current QA evidence notes cover file existence, decode, dimensions, and basic manifests. Creative QA, visual crop proof, mask proof, and runtime prompt proof still need separate gates.

## Required fixes

1. Split the current graph into modular workflows/subgraphs.
2. Convert disabled LoRA library nodes into registry entries.
3. Add pass planner and engine router outside the graph.
4. Add Mask Factory workflows.
5. Add pose/depth/normal/openpose preprocessing workflows.
6. Add per-character instance masks and scene graph.
7. Add strict visual crop QA.
8. Add video/GIF temporal lanes.
9. Add audio planning, generation, and sync lanes.
10. Add promotion gate that blocks anything without runtime and visual evidence.
