# Wave 26 Pose / Depth / Mask Timeline Architecture

Wave 26 does not treat pose, depth, and masks as static assets.
They are timeline-aligned state objects.

## Pose timeline
Defines per-character skeleton or body arrangement at each keyframe.

## Depth timeline
Defines front/back ordering, local overlap, and contact occlusion.

## Mask timeline
Defines which regions are editable, protected, contact-sensitive, or continuity-critical at each keyframe.

## Rule
Every keyframe must have a synchronized pose/depth/mask trio.
If one is missing, the keyframe is invalid.
