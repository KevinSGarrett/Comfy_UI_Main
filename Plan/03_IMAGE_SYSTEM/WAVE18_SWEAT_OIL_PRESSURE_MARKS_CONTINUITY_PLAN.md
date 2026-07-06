# Wave 18 Sweat, Oil, and Pressure-Marks Continuity Plan

## Sweat/oil
- Bind to lighting direction and body curvature.
- Strongest specular response appears on convex, lit surfaces.
- Keep moisture-state transitions believable.

## Pressure marks
- Must be contact-bound.
- Use contact source + target region + intensity profile.
- If no contact ownership exists, block autonomous pressure-mark generation.

## Continuity
Every pass must output:
- target region id
- surface profile applied
- before/after crop pair
- continuity score
- drift flags
