# Pass Planner Specification

## Purpose

The pass planner decides the first pass, second pass, third pass, and repair passes. It must not guess from prompts alone; it must classify requested targets into required workflow modules.

## Inputs

- scene_request.json
- character_bible.json
- model_registry.json
- engine_registry.json
- available workflow templates
- available references
- previous QA results
- output type

## Output

pass_plan.json containing ordered passes.

## Pass classification rules

```text
Character count / layout / camera / pose failure
→ base generation or layout rerun

Wrong body silhouette / stomach / waist / hips
→ large-mask body-shape correction pass

Skin detail / cellulite / blemish / fabric detail
→ small or medium masked detail pass

Hands/fingers/face failures
→ crop/detail/inpaint pass

Touch/contact/grab/indentation
→ combined hand + target body + contact-zone pass

Multi-character merge
→ rerun multi-character layout/base, not small inpaint

Low-res but otherwise correct
→ upscale/final detail pass

Video/GIF request
→ approved keyframe plan + temporal QA + frame repair

Audio request
→ audio scene plan + audio generation + AV sync QA
```

## Required pass fields

- pass_id
- pass_type
- target_entity_id
- target_region
- engine_family
- workflow_template
- checkpoint
- vae
- text_encoder
- loras
- masks
- control_maps
- denoise
- sampler
- cfg/guidance
- seed policy
- expected outputs
- QA gates
- rerun policy

## Required QA before next pass

Each pass must emit a QA result. If a required QA gate fails, the planner must either rerun the pass, run a repair pass, or abort with a blocker.
