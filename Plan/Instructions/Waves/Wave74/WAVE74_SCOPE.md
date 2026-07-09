# Wave74 Autonomous Simulation Backend Adapters Scope

Status: Deferred_Required_Not_Complete.

Purpose: Define the adapter layer that can call Blender first, then optional Houdini, Unreal, DAZ, Marvelous/CLO, or ComfyUI-only approximation routes without manual work or drift.

Activation gate: Deferred. Adapter implementation starts only after the schema and production-base requirements are stable and the current ComfyUI work is not blocked by this future layer.

This wave is part of the future autonomous body-physics/deformation system. It must not become the next implementation target unless the active project direction explicitly activates it.

Authoritative files:

1. `C:\Comfy_UI_Main\Plan\07_IMPLEMENTATION\physics_deformation_system\WAVE74_AUTONOMOUS_SIMULATION_BACKEND_ADAPTERS.md`
2. `C:\Comfy_UI_Main\Plan\07_IMPLEMENTATION\physics_deformation_system\WAVE74_AUTONOMOUS_SIMULATION_BACKEND_ADAPTERS_MATRIX.csv`
3. `C:\Comfy_UI_Main\Plan\Items\wave74_autonomous_simulation_backend_adapters_itemized_list.csv`
4. `C:\Comfy_UI_Main\Plan\Tracker\wave74_autonomous_simulation_backend_adapters_tracker.csv`

Strict execution rules:

- Do not mark rows complete from planning coverage alone.
- Do not start backend/tool installation or EC2 work just because this wave exists.
- Prefer local validation, schemas, adapter stubs, and future-proof planning until activation.
- When activated, every row needs contract, artifact or adapter route, validation evidence, preview/overlay evidence, generated-output evidence when applicable, and strict whole-artifact QA.
- For video, review the full duration plus frame grids.
- For audio, review full-duration playback, event timing, foley/contact alignment, clipping/noise, mix, and AV sync.
- If blocked, write a precise blocker and return to the nearest active source-cited project task.
