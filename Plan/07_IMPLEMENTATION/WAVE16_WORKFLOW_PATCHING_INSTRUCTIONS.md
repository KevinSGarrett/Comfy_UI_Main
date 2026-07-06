# Wave 16 — Workflow Patching Instructions

## Patchable fields

A refine workflow template must expose patch targets for:

- source image path;
- mask path;
- control-map path;
- positive prompt;
- negative prompt;
- target checkpoint/profile;
- LoRA/profile stack;
- sampler steps;
- CFG;
- sampler;
- scheduler;
- denoise;
- output prefix.

## KSampler policy

Before patching a KSampler:

1. identify pass type;
2. check allowed denoise band;
3. block if denoise exceeds policy;
4. record old value and new value;
5. record why the change was made.

## Source image policy

Source image must be an approved image artifact with a hash. A file path alone is not enough.

## Output policy

Output prefix should include:

```text
Wave16/<source_engine>_to_<target_engine>/<pass_id>/
```

## Forbidden patches

Do not patch:

- a Flux LoRA into SDXL;
- an SDXL LoRA into Flux;
- a Pony stack into Flux;
- a full-frame Pony pass without a mask;
- a high-denoise pass labelled as refinement;
- a source-engine latent directly into a target-engine sampler.

## Dry-run requirement

Every patch manifest must be validated before runtime execution.
