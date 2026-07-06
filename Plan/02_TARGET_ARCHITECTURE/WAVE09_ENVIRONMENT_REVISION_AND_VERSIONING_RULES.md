# Wave 09 Environment Revision and Versioning Rules

## Rule
Do not mutate an approved environment silently. Create a new environment version.

## Versioned changes
A new `environment_version` is required when changing:
- room layout,
- camera anchors,
- window/door/mirror placement,
- lighting rig,
- major furniture,
- scale anchors,
- material set,
- background style,
- video camera path,
- audio acoustic profile.

## Non-versioned changes
Minor temporary changes may be scene-local:
- small movable prop,
- temporary clutter,
- small fabric wrinkle,
- minor lighting intensity variation,
- temporary shadow adjustment,
- reversible contact mark.

## Environment lifecycle
```text
draft
→ reference_pack_created
→ locally_validated
→ image_runtime_proven
→ video_runtime_proven
→ audio_runtime_proven
→ promoted
→ deprecated_or_superseded
```

## Revision request format
Every revision should state:
- current environment ID/version,
- change requested,
- reason,
- affected assets,
- expected visual/audio impact,
- whether continuity should be preserved,
- whether old scenes should still use the previous version.

## QA requirement
Any environment revision must be compared against the previous version to detect accidental drift.
