# AI Project Manager Operating Manual

## Mission

Build the ultimate modular hyper-realism generation system for images, GIFs/video, and audio using ComfyUI as the execution layer and an external controller as the autonomous planning/QA layer.

## Non-negotiable architecture rules

1. Use modular workflows or subgraphs. Do not continue expanding one giant untestable graph.
2. Keep catalog/library nodes out of active production paths.
3. Use an external pass planner/orchestrator for autonomy.
4. Use ComfyUI App Mode only as the simplified user interface, not as the reasoning brain.
5. Use decoded images as engine boundaries unless latent compatibility is proven.
6. Use masks for every local body/skin/fabric/contact edit.
7. Use per-character instance IDs and masks for multi-character work.
8. Use QA gates as blockers, not suggestions.
9. Never promote outputs from notes, placeholders, smoke tests, or unrelated files.
10. Every result must be reproducible from manifests.

## Required AI behavior

For every task, the AI project manager must:

1. Read the current cumulative manifest.
2. Identify the wave, scope, and dependencies.
3. Inspect affected files before editing.
4. Make the smallest safe change that advances the wave.
5. Validate syntax, paths, schemas, and workflow graph structure.
6. Produce a delivery report.
7. Produce a validation report.
8. Add unresolved issues to a known-issues log.
9. Do not claim runtime proof unless actual outputs exist and QA evidence is attached.
10. Record all assumptions.

## Required proof levels

- **Static proof:** files exist, parse, and schemas validate.
- **Graph proof:** workflow nodes, links, models, and node classes are valid.
- **Runtime proof:** ComfyUI executes the workflow and creates output files.
- **Visual proof:** crop/contact/mask QA confirms the target visual change happened.
- **Temporal proof:** frame-by-frame video/GIF QA confirms consistency.
- **Audio proof:** audio manifests, timing, mix, and sync QA pass.
- **Promotion proof:** all required proof levels pass for the requested lane.

## AI project manager must never

- Treat disabled library nodes as active.
- Treat notes as wired runtime evidence.
- Activate all LoRAs in a category at once.
- Use body-part LoRAs globally when a masked pass is required.
- Fix character count failures with small inpaint; rerun layout/base instead.
- Upscale failed anatomy, contact, or multi-character outputs.
- Merge characters into one prompt without instance masks.
