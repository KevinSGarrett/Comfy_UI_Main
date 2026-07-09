# Wave75 ComfyUI Physics Conditioning Package Scope

Status: Deferred_Required_Not_Complete.

Purpose: Convert production physics/simulation outputs into ComfyUI-ready pose, depth, normal, segmentation, contact, deformation, optical-flow, temporal, and audio-linked conditioning packages.

Activation gate: Deferred. Activate after at least one production simulation package can be generated or approximated and the current ComfyUI runtime lanes are stable.

This wave is part of the future autonomous body-physics/deformation system. It must not become the next implementation target unless the active project direction explicitly activates it.

Authoritative files:

1. `C:\Comfy_UI_Main\Plan\07_IMPLEMENTATION\physics_deformation_system\WAVE75_COMFYUI_PHYSICS_CONDITIONING_PACKAGE.md`
2. `C:\Comfy_UI_Main\Plan\07_IMPLEMENTATION\physics_deformation_system\WAVE75_COMFYUI_PHYSICS_CONDITIONING_PACKAGE_MATRIX.csv`
3. `C:\Comfy_UI_Main\Plan\Items\wave75_comfyui_physics_conditioning_package_itemized_list.csv`
4. `C:\Comfy_UI_Main\Plan\Tracker\wave75_comfyui_physics_conditioning_package_tracker.csv`

Strict execution rules:

- Do not mark rows complete from planning coverage alone.
- Do not start backend/tool installation or EC2 work just because this wave exists.
- Prefer local validation, schemas, adapter stubs, and future-proof planning until activation.
- When activated, every row needs contract, artifact or adapter route, validation evidence, preview/overlay evidence, generated-output evidence when applicable, and strict whole-artifact QA.
- For video, review the full duration plus frame grids.
- For audio, review full-duration playback, event timing, foley/contact alignment, clipping/noise, mix, and AV sync.
- If blocked, write a precise blocker and return to the nearest active source-cited project task.
