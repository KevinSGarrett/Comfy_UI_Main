# Wave 17 Implementation Manual

## Local-only setup
Wave 17 does not require EC2. Run local validation first.

## Step 1 — Confirm source files
Confirm:
- current Main Flow JSON,
- Wave 16 cumulative pack,
- tracker CSV,
- body region registry,
- body correction schemas.

## Step 2 — Generate masks
Create:
- person-instance mask,
- abdomen/stomach mask,
- waist masks,
- hip mask,
- thigh masks,
- silhouette mask,
- protected face/hands/background masks.

## Step 3 — Compile contract
Use `compile_body_shape_correction_contract.py` or create JSON matching `body_shape_correction_contract.schema.json`.

## Step 4 — Validate contract
Use `validate_body_shape_correction_contract.py`.

## Step 5 — Patch/run workflow
Patch the selected inpaint/refine workflow with:
- input image,
- target mask,
- positive/negative prompt segments,
- low denoise,
- matching engine family,
- selected same-engine LoRA stack if needed.

## Step 6 — Score evidence
Use `score_body_shape_evidence.py` with a body_shape_evidence JSON.

## Step 7 — Promote or rerun
Promote only if QA passes. Otherwise rerun based on `wave17_body_correction_rerun_policy.json`.
