# Wave 09 AI Project Manager Tasks

## Wave name
Environment, world, lighting, props.

## Goal
Add room/environment logic, furniture, surfaces, lighting, scale, material behavior, environmental continuity, and the video/audio proof-bound clarification that prevents the system from confusing an image-only canvas with the final image/video/audio runtime.

## Required work
1. Create the Environment Bible and environment registry contract.
2. Create room, world, lighting, prop, surface, material, scale, and continuity schemas.
3. Bind the LLM Scene Director to environment IDs the same way Wave 08 bound it to character IDs.
4. Define how environments are reused across image passes, inpaint passes, upscales, video keyframes, video shots, audio ambience, Foley, and spatial/acoustic simulation.
5. Clarify that video/audio are absolutely in scope, but they must be promoted through their own workflow/runtime proof gates.
6. Add local validation scripts that can check environment packs, prop manifests, lighting rigs, material profiles, and video/audio runtime-boundary claims.
7. Add QA gates for room scale, shadows, reflections, surface continuity, prop consistency, environmental continuity, and scene-to-scene reuse.

## Important correction
The phrase `video/audio remain proof-bound` does **not** mean video/audio are excluded. It means the current uploaded Main Flow is an image-generation canvas and should not be falsely labeled as the fully proven video/audio runtime. The system must build video and audio workflows as first-class modules, then promote them only after evidence exists.

## Output
A cumulative Wave 09 ZIP that includes all prior waves plus Wave 09 architecture, schemas, examples, registries, implementation manuals, scripts, and validation reports.
