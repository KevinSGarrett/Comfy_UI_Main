# Wave 18 Pressure Marks, Oil, Sweat, and Cellulite Strategy

## Cellulite
- Use medium masks on thighs, butt, or other approved target zones.
- Prefer low-denoise regional passes.
- Cellulite should respect body lighting and body curvature.
- Reject if it turns into random noise or affects non-target regions.

## Pressure marks / compression
- Must be geometry-aware and tied to contact.
- Require contact ownership from Wave 13 masks or Wave 14 pass plan.
- Use when the body is compressed by a hand, surface, garment, or another body.
- Pressure intensity should scale with force level and softness profile.

## Sweat / oil / wetness
- Wetness must follow the scene lighting model.
- Oil adds controlled specular highlights; sweat adds beads/streaks where plausible.
- Never turn the entire image glossy if only a local moisture state was requested.

## Surface-state ordering
If multiple surface states are requested, the default order is:
1. baseline skin texture
2. cellulite / stretch marks / macro skin detail
3. pressure marks / compression
4. sweat / oil / wetness
5. cleanup / continuity rebalance
