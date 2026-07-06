# Wave 12 Runtime Promotion Lifecycle

Frame composition promotion has four states.

## 1. Planned

The Scene Director and Camera Plan define the desired composition.

## 2. Generated

ComfyUI produces an image or video frame.

## 3. Evidence collected

Detector, skeleton, segmentation, and crop evidence are written to a frame evidence report.

## 4. Promoted or repaired

The QA system either promotes the frame, sends it for review, or produces a repair plan.

## Promotion blockers

- Wrong character count.
- Merged bodies.
- Full-body shot missing feet.
- Primary face cut by crop.
- Unassigned body fragment.
- Duplicate skeleton or duplicated primary character.
- Severe body merge in contact areas.
