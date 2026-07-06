# Wave 08 — Character Continuity QA Gates

## Gate 1 — Character Bible Validation

Pass only if:

- `character_id` exists
- `character_version` exists
- status is valid
- locked traits are declared
- reference pack ID is declared
- visual/audio support flags are consistent
- schema validation passes

## Gate 2 — Reference Pack Validation

Pass only if:

- manifest exists
- approved references exist
- hashes exist
- raw/approved/rejected references are separated
- required reference categories are present
- no conflicting identity anchors exist

## Gate 3 — Scene Binding Validation

Pass only if:

- every scene character resolves to a Character Bible
- every visible character has a scene instance ID
- every multi-character scene has separate masks planned
- no character-specific model is routed globally by accident

## Gate 4 — Runtime Continuity QA

Pass only if generated output preserves:

- face identity
- body silhouette
- hair profile
- skin markers
- outfit/accessory continuity
- person count
- person separation
- voice profile if audio exists

## Gate 5 — Promotion Gate

Promotion is blocked if:

- runtime output is missing
- identity score is below threshold
- reference pack hash mismatch exists
- model stack used wrong engine
- masks are missing for character-specific passes
- character was modified without revision record
- multi-character identity bleed is detected
