# Wave 12 Implementation Manual

## Step 1 — Compile frame composition contract

Use the Scene Director output, Character Bible IDs, Camera Plan, and Pose Plan to compile `frame_composition_contract.json`.

## Step 2 — Run image/video generation

Run the selected workflow module through ComfyUI.

## Step 3 — Collect evidence

Run detector/skeleton/segmentation tools and write `frame_composition_evidence.json`.

## Step 4 — Score evidence

Use `score_frame_composition_evidence.py` to produce a score report.

## Step 5 — Decide

- Promote if score passes and no hard fail exists.
- Review if score is borderline.
- Repair if crop/body count/visibility can be fixed.
- Reject and rerun if merged bodies or wrong character count are severe.

## Important implementation rule

Do not use prompt wording alone as proof of frame integrity. The output must be checked.
