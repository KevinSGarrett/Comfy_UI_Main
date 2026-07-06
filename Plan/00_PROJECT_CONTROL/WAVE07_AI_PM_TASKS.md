# Wave 07 AI Project Manager Tasks

## Mission

Build the planning intelligence that turns a user request into a concrete, auditable, QA-gated plan before any workflow runs.

## Required tasks

1. Parse raw user request into normalized intent.
2. Classify the target output: image, image series, GIF, video, audio, AV sync, or model-selection task.
3. Select the correct director profile.
4. Resolve ambiguity using project defaults where possible.
5. Create a scene graph containing characters, environment, props, actions, relationships, depth order, and negative constraints.
6. Create a camera plan with shot type, lens look, body crop, subject count, camera height/distance/angle, depth of field, and occlusion warnings.
7. Create a model-selection plan that reads the Wave02 Civitai metadata registry, Wave06 engine registry, model storage status, and QA status.
8. Create a mask plan using macro, major, minor, micro, nano, contact, and protect mask categories.
9. Create an ordered pass plan that targets Wave05 modules and Wave06 engines.
10. Create QA goals before generation.
11. Declare promotion blockers before generation.
12. Write required evidence outputs.

## Non-negotiable AI PM rules

- Do not run ComfyUI from the Scene Director.
- Do not promote from notes, unstaged branches, or unrelated smoke outputs.
- Do not select models that are rejected, wrong-engine, missing metadata, or lacking required proof.
- Do not direct-mix Flux, Flux2, SDXL, Pony, SD1.5, Z-Image, video, or audio model objects.
- Cross-engine transfer must be image-file based.
- If the request is under-specified but usable, make a best-effort plan and record assumptions.
- Ask for clarification only if a blocking missing file/reference or contradiction prevents a usable plan.
