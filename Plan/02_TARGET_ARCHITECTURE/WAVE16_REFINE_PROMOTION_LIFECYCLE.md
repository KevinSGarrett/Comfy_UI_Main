# Wave 16 — Refine Promotion Lifecycle

A refined image moves through the following states.

```text
planned
→ patched
→ dry_run_validated
→ executed
→ evidence_collected
→ scored
→ rerun_or_fallback_or_blocked
→ promoted
```

## Planned

The Scene Director and Orchestrator decide whether a refine pass is needed.

## Patched

The workflow template is patched with:

- source image;
- target engine/checkpoint profile;
- prompt/negative;
- denoise;
- mask/control maps;
- output prefix.

## Dry-run validated

Before execution, the pass is validated against:

- engine compatibility;
- denoise policy;
- mask presence;
- source image hash;
- target workflow requirements;
- forbidden cross-engine object use.

## Executed

The pass is submitted to ComfyUI only after validation.

## Evidence collected

The evidence collector records:

- output files;
- dimensions;
- hashes;
- workflow template id;
- engine family;
- patch manifest;
- prompt manifest;
- mask/control artifacts.

## Scored

QA scores the output against the base image.

## Rerun, fallback, or blocked

If QA fails, the Orchestrator chooses:

- rerun with lower denoise;
- tighten mask;
- switch engine target;
- fallback to same-family SDXL;
- block and return to Scene Director.

## Promoted

Promotion requires passing evidence, not just a generated file.
