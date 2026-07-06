# Wave 13 — Mask Factory QA Gates

## Gate 1 — Contract validity

The mask contract must parse and include required mask scales, person instances, and promotion gates.

## Gate 2 — Mask ownership

Every body-part, fabric, and contact mask must belong to a person instance, prop, object, or environment zone.

## Gate 3 — Coverage

Mask area must be plausible for the requested target and not exceed configured bounds.

## Gate 4 — Edge quality

Edges must not create halos, hard cutouts, or obvious seams unless intentionally used for debug.

## Gate 5 — No cross-character bleed

Masks must not bleed across person instances unless the mask is explicitly a contact or boundary mask.

## Gate 6 — Runtime evidence

Promotion requires actual mask files and output evidence.

## Gate 7 — Final promotion

The output is blocked if required mask evidence is missing, score is below threshold, or automatic blockers are present.
