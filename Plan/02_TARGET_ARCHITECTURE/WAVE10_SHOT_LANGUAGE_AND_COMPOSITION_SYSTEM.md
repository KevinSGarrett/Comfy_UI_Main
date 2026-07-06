# Wave 10 Shot Language and Composition System

## Goal

Convert natural language shot requests into consistent camera decisions.

## Examples

```text
“full body”
→ shot_size=full_body
→ lens=classic_35mm
→ aspect_ratio=4:5
→ crop_policy=blocked_unintentional_crop
→ must_not_crop=head,hands,feet,outfit_edges

“close-up face”
→ shot_size=close_up
→ lens=portrait_85mm
→ focus_targets=eyes,face_identity
→ crop_policy=intentional_crop
→ qa=identity_preserved,eyes_sharp

“two people in a room”
→ shot_size=two_shot
→ lens=classic_35mm
→ depth=layered_depth
→ subject slots=left/right
→ qa=no_identity_blending,subject_count_correct
```

## Composition Presets

- `centered_reference`
- `rule_of_thirds_portrait`
- `full_body_catalog`
- `two_subject_balanced`
- `foreground_depth_stack`
- `detail_insert_context`

## Negative Prompt Guard Concepts

Camera plans should add negative prompt guards for:

- accidental crop
- cut off feet
- cut off hands
- missing head
- warped perspective
- extra people
- merged bodies
- distorted limbs
- face identity drift
- blurred focus target

These guards do not replace QA. They only reduce common failure modes.
