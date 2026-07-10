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

## Evaluator Contract

- Evaluator: `Plan/07_IMPLEMENTATION/scripts/benchmark_wave70_facial_gold_evaluator.py`
- Originals-only producer: `Plan/07_IMPLEMENTATION/scripts/produce_wave70_facial_original_predictions.py`
- Metric gate and visual panel: `Plan/07_IMPLEMENTATION/scripts/gate_wave70_facial_originals_benchmark.py`
- Prediction manifest schema: `Plan/08_SCHEMAS/facial_gold_prediction_manifest.schema.json`
- LaPa taxonomy schema: `Plan/08_SCHEMAS/lapa_taxonomy_binding.schema.json`
- Disposable regression: `Plan/Instructions/QA/Scripts/test_wave70_facial_gold_evaluator.py`

The evaluator never invokes a model. A separate producer must first write a
hash-bound prediction manifest from originals only. LaPa semantic evaluation
requires a separately supplied, hashed, authoritative taxonomy binding;
landmark-only evaluation still requires authoritative interocular
normalization metadata. Legacy split-specific benchmark scripts are historical
diagnostics and fail closed before execution because they predate this contract.

### Celeb Gate Rules

The bounded route gate requires at least three eligible originals per class,
aggregate IoU of at least `0.85`, aggregate false-positive pixels divided by
gold pixels no greater than `0.15`, and aggregate false-negative pixels divided
by gold pixels no greater than `0.15`. A class that is gold-empty across every
selected sample is exempt from ratio math but passes only when its aggregate
false-positive count is zero. Counts are summed before ratios are computed.

Celeb binary masks intentionally overlap for nested anatomy and accessories.
The producer therefore records an explicit reviewed protected-neighbor list for
every class instead of treating all other classes as protected. Skin overlap
with brows, eyes, nose, mouth, lips, neck, and hair is not automatically
leakage; `neck_l`, `ear_r`, and `eye_g` likewise remain separate overlays rather
than replacements for their underlying anatomy.

The first production run on eligible original IDs `0`, `1`, and `2` passed the
evaluator contract but failed the quality gate. Only `hair`, `mouth`, `nose`,
and correctly empty `eye_g` passed; fourteen classes remain blocked. This is a
route-repair result, not promotion or certification evidence.

### Native Parser Scale Repair

The packaged `face_parsing.segment` implementation documents a `512x512`
input/parsing contract. Production preprocessing must therefore resize the
original RGB image to `512x512` with bilinear sampling before inference, retain
the original source hash, hash the isolated route input separately, and record
the source-to-route resize for nearest-neighbor inversion of predicted masks.
Raw output filenames must match the fixed `01_skin` through `18_hat` index/name
binding; an unknown or mismatched index/name pair fails closed.

A controlled comparison on identical original IDs `0`, `1`, and `2` improved
the gate from four passing classes to nine with no previously passing class
regression. `l_brow`, `r_brow`, `l_eye`, `r_eye`, and `l_lip` newly pass; right
eye IoU increased from `0.257` to `0.879` and left eye from `0.529` to `0.864`.
The route still fails overall on `cloth`, `ear_r`, `hat`, `l_ear`, `neck`,
`neck_l`, `r_ear`, `skin`, and `u_lip`, so this repair remains candidate route
evidence only.

### Rejected Horizontal-Flip TTA Experiment

The optional `hflip_logit_mean` experiment runs original and horizontally
flipped inputs, spatially unflips the second logits tensor, swaps left/right
brow, eye, and ear channels, averages logits, and performs argmax only after
fusion. It is an experimental diagnostic mode; `single_pass` remains the
production default.

On controlled IDs `0`, `1`, and `2`, flip TTA reduced passing classes from nine
to five and regressed both eyes and both brows. It therefore failed the
no-regression acceptance rule, was not run on fresh held-out images, and must
not be selected for production, promotion, or certification. Repeating or
tuning this candidate against the same gold samples is prohibited without a
new implementation hypothesis.

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
