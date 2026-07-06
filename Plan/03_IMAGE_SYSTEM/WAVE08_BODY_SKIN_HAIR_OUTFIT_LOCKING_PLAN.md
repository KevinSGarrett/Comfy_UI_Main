# Wave 08 — Body, Skin, Hair, and Outfit Locking Plan

## Body Locking

Body profile fields:

- height class
- build/silhouette
- shoulder/waist/hip ratio
- limb proportions
- posture tendencies
- body marks
- soft-body material profile placeholder
- body region map

Body locks should be QA-checked at full-frame and crop levels. Body-shape LoRAs should usually be used in base/refine passes, while local body surface details belong in masked detail passes.

## Skin Locking

Skin profile fields:

- base skin tone
- undertone
- texture level
- pore/blemish detail level
- freckles/moles/scars/tattoos
- makeup state
- temporary surface state
- marker preservation list

Temporary skin states such as sweat, dirt, pressure marks, or makeup changes do not require a new character version unless intended permanent.

## Hair Locking

Hair profile fields:

- base color
- root color
- length
- style
- bangs/fringe
- hairline
- texture/curl pattern
- accessories
- approved variants

Hair changes often cause identity drift. Hair changes should be explicitly categorized as temporary styling, outfit variant, or new character version.

## Outfit Locking

Outfit profile fields:

- default outfit set
- allowed wardrobe variants
- accessories
- jewelry
- fabric type
- fit/silhouette
- color palette
- continuity-critical items

Outfit references must be separated from body identity references. Clothing should not accidentally become part of the permanent character identity unless explicitly locked.
