# Ultimate Mask Taxonomy: Macro, Major, Minor, Micro, and Nano

## Goal

The Mask Factory must know when to use small vs large masks and must support single- and multi-character scenes without chopped-body artifacts.

## Mask levels

| Level | Scope | Examples | Use case | Typical denoise |
|---|---|---|---|---|
| Macro | whole scene/person/environment | person A, person B, background, bed | layout, instance separation, full-character correction | 0.25–0.55 |
| Major | large body/material areas | torso, hips, legs, arms, clothing item | body shape, silhouette, clothing/fabric correction | 0.28–0.50 |
| Minor | specific sub-regions | stomach, waist, thigh, cheek, hand, hair section | part-specific detail/correction | 0.18–0.38 |
| Micro | texture patches | cellulite patch, pores, blemish, pressure mark, wrinkle cluster | realism/detail only | 0.10–0.28 |
| Nano | tiny detail overlays | pore clusters, nail edge, eyelash, small scar/freckle | final crop detail | 0.05–0.18 |

## Decision rule

```text
If geometry/shape is wrong → large/major mask or rerun base.
If surface/detail is wrong → minor/micro/nano mask.
If pose/camera/character count is wrong → rerun base/control; do not try to fix with tiny masks.
If contact is wrong → combine source mask + target mask + contact-zone falloff mask.
```

## Anti-chop rules

A body-edit mask must include enough surrounding anatomy to preserve continuity. For example, a stomach reduction mask should include stomach, waist, side torso, clothing seam, and a small falloff margin. A thigh cellulite mask should not include face, arms, background, or clothing unless intentionally editing fabric.

## Required mask QA outputs

- binary mask preview,
- feathered mask preview,
- mask overlay on source image,
- crop around target area,
- before/after target crop,
- no-bleed crop outside target area.
