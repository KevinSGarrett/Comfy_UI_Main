# Wave 12 Main Flow Frame Composition Review

The uploaded Main Flow is an image-generation canvas with multiple SaveImage outputs. It does not yet contain a complete detector-based visual QA lane for character counting, crop safety, body visibility, or no-merged-body verification.

## Main Flow facts observed

- Nodes: 356
- Links: 91
- SaveImage lanes: 8
- Latent size nodes: 5
- Note boundaries: 13
- Disabled/catalog LoRA nodes: 274

## Relevant output lanes

- `Main_Flow/SDXL_RealVisXL_LoRA`
- `Main_Flow/Flux_Family_ZImage`
- `Main_Flow/SDXL_RealVisXL_LoRA_Upscaled`
- `Main_Flow/SDXL_Inpaint_Detail`
- `Main_Flow/Flux_to_SDXL_Refine`
- `Main_Flow/True_Flux_Schnell_Reference_Smoke`
- `Main_Flow/ControlNet_Canny_Edge`
- `Main_Flow/IPAdapter_Face_Reference`

## Wave 12 interpretation

Frame composition QA should run after each selected output lane produces concrete image files. The QA system should never infer that a frame is compositionally correct just because the workflow graph contains a note, prompt, LoRA category, or control-map branch.

The correct pattern is:

```text
Scene plan
→ camera/framing plan
→ pose/control plan
→ ComfyUI output
→ detector/skeleton/segmentation evidence
→ frame-integrity score
→ promotion or repair plan
```
