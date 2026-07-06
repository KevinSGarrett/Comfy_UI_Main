# Wave 12 Detector, Segmentation, and Skeleton QA Pipeline

Wave 12 is detector-agnostic. It defines the evidence contract so the system can plug in whichever local detector stack is selected later.

## Evidence sources

- Person bounding boxes.
- Face bounding boxes.
- Pose skeletons.
- Instance segmentation masks.
- Body-region segmentation.
- Depth ordering.
- Manual review annotations for edge cases.

## Minimum evidence for promotion

An image cannot be promoted from frame-integrity QA unless evidence contains:

- Output image path.
- Expected character count.
- Detected character/person instances.
- Body visibility per character.
- Crop boundary report.
- Merged body report.
- Final score and decision.

## Static vs runtime proof

Static pack validation only proves that the system knows how to ask for and score this evidence. Runtime promotion requires actual generated images and detector output.
