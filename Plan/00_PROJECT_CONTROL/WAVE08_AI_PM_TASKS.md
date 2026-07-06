# Wave 08 AI Project Manager Tasks

## P0 — Character System Foundation

- Create the canonical Character Bible schema.
- Create the identity registry schema.
- Define one stable `character_id` per reusable character.
- Define `character_version` and revision rules.
- Define which fields are locked, editable, generated, or scene-specific.
- Define reference-pack folder layout.
- Define reference asset manifest fields.
- Define continuity QA evidence requirements.

## P0 — Scene Director Binding

- Scene Director must resolve each character by `character_id` before compiling a pass plan.
- Scene Director must not invent identity-critical fields when a character ID exists.
- Scene Director must treat user-requested changes as proposed revisions, not direct overrides.
- Scene Director must fail closed when two characters conflict or merge.

## P1 — Reference Pack Work

- Build one reference pack per character and version.
- Separate raw references, approved references, masked references, embeddings, masks, and QA evidence.
- Generate face, body, hair, outfit, and voice manifests.
- Hash every reference file.
- Do not store private/raw reference files in Git.

## P1 — QA Work

- Add character continuity checks to every image pass.
- Add per-character masks for multi-character scenes.
- Add outfit continuity checks.
- Add hair/skin/body markers to QA goal catalogs.
- Add per-character identity failure reasons and rerun actions.

## P2 — Future-Wave Handoffs

- Wave 09 receives environment-aware character placement rules.
- Wave 10 receives camera/framing character visibility rules.
- Wave 11 receives pose/body-blocking target contracts.
- Wave 13 receives body-part mask ownership from Character Bible regions.
- Wave 21–23 receive soft-body profile and contact profile fields.
- Wave 24–25 receive multi-character instance separation contracts.
- Wave 30–31 receive voice/audio continuity fields.
