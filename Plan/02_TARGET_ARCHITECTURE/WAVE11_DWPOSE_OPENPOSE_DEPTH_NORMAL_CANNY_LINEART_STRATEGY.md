# Wave 11 DWPose / OpenPose / Depth / Normal / Canny / Lineart Strategy

## DWPose

Use DWPose as the preferred whole-body pose extractor for complex character action, hands, faces, body direction, and multi-character blocking.

Required proof:

- node exists in object_info;
- generated pose map exists;
- optional keypoint JSON exists when available;
- required body regions are visible;
- per-character mask assignment is correct.

## OpenPose

Use OpenPose for simpler body skeleton transfer and pose-library templates.

Required proof:

- body skeleton generated;
- limb order valid;
- no left/right swap;
- map aligns to camera/framing plan.

## Depth

Use depth for foreground/background order, room perspective, camera distance, and video keyframe continuity.

Required proof:

- map file generated;
- foreground/background order is coherent;
- no inverted or flat map;
- dimensions match target output plan.

## Normal

Use normal maps for surface orientation and geometry hints.

Required proof:

- normal map generated;
- color channels are plausible;
- surface form matches reference;
- strength stays low enough to avoid plastic/waxy results.

## Canny

Use Canny for hard edges, prop contours, furniture lines, and room geometry. The current Main Flow already contains a wired Canny branch that needs runtime evidence.

Required proof:

- source Canny image exists;
- ControlNet branch runs;
- output saved under the expected prefix;
- edge density is not too sparse or too noisy.

## Lineart

Use lineart for cleaner contour retention where Canny is too noisy.

Required proof:

- lineart map generated;
- contours match reference;
- final output does not become flattened/stylized unless intended.
