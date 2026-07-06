# Wave 08 — Character-Aware Model and LoRA Selection Strategy

## Purpose

Character identity must influence model selection without allowing model stacks to overwrite the character. Model selection must be compatibility-aware, region-aware, and QA-bound.

## Selection Inputs

The model selector receives:

- character_id
- character_version
- allowed engines
- required visual traits
- body/skin/hair/outfit locks
- scene intent
- mask plan
- pass type
- engine router constraints
- Civitai metadata tags
- installed/path_verified/promoted model status

## Selection Order

1. Pick engine route from Wave 06 rules.
2. Confirm character supports the chosen engine.
3. Pick base checkpoint compatible with character goals.
4. Pick global realism LoRAs only if allowed.
5. Pick identity/detail LoRAs only when they do not conflict with locked fields.
6. Pick region-specific LoRAs only behind masks.
7. Reject wrong-engine stacks.
8. Reject deprecated or superseded assets unless explicitly used for historical reproduction.
9. Create `model_selection_plan` with all chosen assets and reasons.
10. Attach QA goals for every identity-affecting choice.

## LoRA Stack Rule

A character-specific LoRA must be one of:

- global and safe for the whole character
- region-masked
- detail-pass-only
- candidate/test-only
- rejected/superseded

It must never be enabled just because it exists in the disabled library.

## Engine Compatibility Rule

Character packs can support multiple engines, but identity proof is per engine:

```text
char_elena_demo v001 + SDXL proof != char_elena_demo v001 + Flux proof
```

Each engine family needs its own evidence and QA confidence.

## Civitai Metadata Use

Civitai metadata from Wave 02 should help populate:

- base model family
- model type
- trigger words
- tags
- training keywords
- creator/source identifiers
- file hashes
- model version
- model status
- compatibility notes
- recommended prompt tokens
- forbidden prompt tokens
- known conflict tags

The Character Bible should never rely on file name alone for identity-critical routing.
