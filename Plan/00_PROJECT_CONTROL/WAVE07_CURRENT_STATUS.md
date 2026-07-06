# Wave 07 Current Status — LLM Scene Director

Generated: 2026-07-05T22:15:56Z

## Wave focus

**Wave 07 — LLM Scene Director**

Goal: convert user requests into structured scene plans, pass plans, masks, camera plans, engine routes, model-selection plans, and QA goals.

## Current decision

The Scene Director is the front-end intelligence layer for creative/technical requests. It does **not** directly run ComfyUI, modify workflows, promote assets, or decide that outputs are production-ready.

The Scene Director produces structured JSON for downstream systems:

1. Scene graph.
2. Character/environment/action/contact graph.
3. Camera/framing plan.
4. Mask plan.
5. Model-selection plan.
6. Engine route.
7. Ordered pass plan.
8. QA goal plan.
9. Promotion blockers and evidence requirements.

## Relationship to prior waves

- Wave 02 defined model storage, Civitai metadata, S3/local/EC2 cache behavior, and registry depth.
- Wave 03 defined local validation.
- Wave 04 deconstructed the current Main Flow into active lanes, staged lanes, notes, and catalog nodes.
- Wave 05 defined modules, subgraphs, App Mode, and the orchestrator boundary.
- Wave 06 defined engine registry/router behavior, including Flux2 as planned/proof-gated.
- Wave 07 now converts human requests into the structured contracts that Waves 05–06 can execute.

## Source status

The current Main Flow is still treated as a runtime-bound source canvas. It has 356 nodes, 91 links, 8 SaveImage lanes, and 274 LoRA catalog nodes. The disabled LoRA library remains registry/catalog input only and must not be globally enabled.

The tracker CSV has 12887 rows and 73 columns and remains an ongoing mutable upstream source.

## Wave 07 status

Static package status: **created and validated**

Runtime status: **not runtime-proven yet**

The next runtime layer must capture local ComfyUI `/object_info`, load selected model candidates, run a small scene-director-generated prompt plan, and prove output/evidence manifests.
