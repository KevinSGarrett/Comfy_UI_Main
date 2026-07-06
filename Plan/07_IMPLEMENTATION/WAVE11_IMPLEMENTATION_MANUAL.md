# Wave 11 Implementation Manual

## Local-First Workflow

1. Copy `.env.example` to `.env`.
2. Confirm `COMFYUI_API_URL` points to local ComfyUI.
3. Run object_info capture.
4. Run Wave 11 static validation.
5. Generate test control maps.
6. Validate generated control maps.
7. Run one minimal Canny branch proof.
8. Add DWPose/OpenPose/depth/normal/lineart modules only after object_info shows required nodes.
9. Keep EC2 off until local proof passes.

## Recommended Folder Layout

```text
C:\Comfy_UI_Main\control_maps\
  characters\<character_id>\pose\
  characters\<character_id>\depth\
  scenes\<scene_id>\depth\
  scenes\<scene_id>\canny\
  scenes\<scene_id>\lineart\
  scenes\<scene_id>\normal\
  manifests\
```

## Promotion

No output is promoted unless its evidence manifest links:

- Scene Director plan;
- character bible;
- camera plan;
- control map plan;
- generated control maps;
- ComfyUI workflow/module;
- output files;
- QA decision.
