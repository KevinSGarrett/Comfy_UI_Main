# FACIAL_NECK_HAIR_GOLD_STANDARD_BENCHMARK_PROTOCOL

## Purpose

Use the supplied CelebAMask-HQ and LaPa originals and annotations as paired
gold-standard evaluation data for facial masks, supported neck masks, hair, and
LaPa facial landmarks. This protocol does not provide or imply body/body-part
gold truth.

## Required Evaluation Flow

1. Select an eligible original image from the registry without exposing its
   gold annotation to the production masking route.
2. Run the same production face-parsing/masking route intended for real inputs.
3. Preserve the source image ID, source dimensions, route/model identity,
   configuration, and prediction hash.
4. Convert the prediction to source-image coordinates with nearest-neighbor
   resizing for discrete masks. Record every crop, pad, resize, or transform.
5. Load the paired gold annotation only in the evaluator.
6. Compare prediction and gold per class. Record IoU, Dice, precision, recall,
   boundary F-score, protected-neighbor leakage, and empty-class handling.
7. For LaPa, evaluate landmarks separately and preserve train/val/test split
   discipline. Test data is reporting-only, not tuning data.
8. Fail closed on missing pairs, unknown label taxonomy, dimension ambiguity,
   transforms that cannot be inverted, or prediction/gold leakage.

## CelebAMask-HQ Pairing

- Originals: `C:\Comfy_UI_Main\MaskedWarehouse\CelebAMask-HQ\CelebA-HQ-img`
- Gold shard: `C:\Comfy_UI_Main\MaskedWarehouse\CelebAMask-HQ\CelebAMask-HQ-mask-anno\0`
- Shard `0` covers annotated integer IDs `0` through `1999`; it does not make
  all 30,000 originals eligible.
- Pair `<zero-padded-id>_<class>.png` with `<integer-id>.jpg`.
- The class files are separate binary masks, not composited preview images.
- `neck` is anatomical neck. `neck_l` is necklace/accessory and must remain a
  separate class.
- A class file absent for an eligible ID may be evaluated as an empty mask only
  under the dataset convention. Never infer annotations for IDs outside the
  supplied shard.

## LaPa Pairing

- Pair `images`, `labels`, and `landmarks` by exact stem within `train`, `val`,
  or `test`.
- Label PNGs are indexed segmentation maps, not overlays.
- Landmark TXT files are a separate geometric gold source.
- Observed label values are `0` through `10`. Before publishing per-class
  semantic results, bind those values to an authoritative LaPa taxonomy record;
  do not guess class meanings from color or position.
- Use train for development, validation for threshold/configuration selection,
  and test for held-out reporting.

## Scope Boundary

These datasets may support facial feature, face skin, ear, neck, hair, facial
accessory, and landmark evaluation according to their actual labels. They do
not supply torso, arm, hand, finger, breast, abdomen, pelvis, glute, thigh,
calf, foot, toe, clothing-contact, or whole-body gold masks.

Therefore:

- facial/neck/hair benchmark work no longer uses
  `Blocked_Gold_Mask_Dependency_Missing` merely because manual body masks are
  unfinished;
- a facial route still cannot be promoted until its exact benchmark intake,
  leakage controls, metric thresholds, failure review, and promotion evidence
  pass;
- the manual body/body-part dependency remains active and unchanged;
- no result from these face datasets authorizes body geometry authority,
  contact authority, Wave71+ activation, or full Mask Factory certification.

## Dataset Rights

The supplied CelebAMask-HQ README restricts the images to non-commercial
research and educational use. No LaPa license file was found in the supplied
local root. Keep both datasets local, do not package or redistribute them, and
complete rights review before any commercial or external use.

## Authority

Machine-readable paths, counts, pairing rules, and claim boundaries are in:

`Plan/10_REGISTRIES/facial_neck_hair_gold_standard_dataset_registry.json`
