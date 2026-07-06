# Character Identity and Multi-Character Specification

## Single-character identity

Use a Character Bible:
- character_id
- face references
- body-shape references
- hair references
- outfit references
- skin detail references
- voice profile if audio
- locked traits
- allowed variation
- disallowed drift

## Multi-character identity

Every character must have:
- unique character_id
- separate references
- separate region/bounding box
- separate person mask
- separate prompt block
- separate pose/control maps
- separate QA crops

## Multi-character generation rules

1. Do not rely on one giant prompt.
2. Use scene graph layout before detail generation.
3. Use per-character masks and reference isolation.
4. Use depth/occlusion order.
5. If characters merge, rerun layout/base.
6. Fix identity and detail only after character separation passes.

## Required QA

- correct number of people
- each character in expected region
- references isolated
- no merged torsos/limbs/faces
- no cross-character LoRA/detail bleed
- pose and gaze match plan
- interactions occur between correct entities
