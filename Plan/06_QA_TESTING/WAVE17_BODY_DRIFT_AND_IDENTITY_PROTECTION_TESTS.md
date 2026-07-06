# Wave 17 — Body Drift and Identity Protection Tests

## Identity protection
Body correction must not alter:
- face,
- hair identity,
- character age/style,
- outfit identity,
- unique marks,
- scene role,
- camera framing.

## Pose protection
Body correction must not alter:
- skeleton,
- stance,
- shoulder line,
- pelvis/knee alignment,
- hand placement,
- interaction/contact relationship.

## Drift tests
- Compare base and candidate body keypoints.
- Compare silhouette delta against allowed profile.
- Compare face/identity crop.
- Compare frame crop and visible body ratio.
- Compare clothing surface continuity.
- Compare protected-region pixel/mask change.

## Blocking rule
If identity or pose protection fails, the output cannot promote even if the requested stomach/waist/hips/thigh correction looks better.
