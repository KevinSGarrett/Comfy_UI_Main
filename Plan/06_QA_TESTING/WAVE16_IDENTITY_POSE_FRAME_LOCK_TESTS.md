# Wave 16 — Identity, Pose, and Frame Lock Tests

Image refinement must respect the earlier system layers:

- Character Bible;
- camera/framing plan;
- pose/control map contracts;
- frame composition integrity;
- mask factory ownership.

## Identity lock

Identity lock requires:

- same character id;
- same reference pack version;
- face/body identity comparison;
- no unauthorized hair/skin/outfit changes.

## Pose lock

Pose lock requires:

- skeleton/control-map comparison where available;
- hand/body position tolerance;
- no merged bodies;
- no new limbs/fragments.

## Frame lock

Frame lock requires:

- correct character count;
- correct shot size;
- correct body visibility;
- crop margins preserved;
- camera angle preserved.

## Combined fail

Any high-severity failure in identity, pose, or frame lock blocks promotion even if the image appears visually improved.
