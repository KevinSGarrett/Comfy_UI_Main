# Wave 10 Multi-Character Framing and Depth Rules

## Problem

Multi-character scenes fail when the system does not know who is who, where each character belongs, what can overlap, and which body/face/hand/contact points must stay visible.

## Required Subject Slot Fields

Each character or subject must have:

- `subject_id`
- `character_id`
- `screen_position`
- `depth_order`
- `identity_priority`
- `crop_policy`
- `occlusion_allowed`
- `must_show`
- `must_not_merge_with`
- `scale_anchor`

## Example Layout

```text
char_A:
  screen_position: left
  depth_order: 1
  identity_priority: primary
  must_show: face, hands, outfit, contact_points

char_B:
  screen_position: right
  depth_order: 1
  identity_priority: primary
  must_show: face, hands, outfit, contact_points
```

## Depth Rules

- Two-shot and group shots default to `layered_depth` or `deep_focus`.
- Strong bokeh is blocked unless one character is intentionally secondary.
- Foreground objects cannot hide required identity or contact evidence unless declared.
- Background props must remain scale-consistent with the environment profile.

## QA Rules

A multi-character output cannot be promoted if:

- subject count is wrong
- identities merge
- required faces/hands/contact points are hidden
- scale is inconsistent
- depth order contradicts the plan
- camera crop cuts required subjects unintentionally
