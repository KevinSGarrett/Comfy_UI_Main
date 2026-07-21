# Image Generation Visual Review Protocol

## Purpose

This protocol defines strict autonomous inspection for still-image artifacts.

## Required inputs

- generated image path
- generating workflow / prompt reference
- model / LoRA / checkpoint context
- target use case
- prior baseline or expected appearance if applicable

## Review flow

1. Confirm the image loaded successfully.
2. Confirm resolution, file integrity, and readability.
3. Perform global composition review.
4. Perform subject-specific review.
5. Perform anatomy / realism review.
6. Perform rendering artifact review.
7. Perform prompt-compliance review.
8. Score, classify, and record issues.

## Mandatory checklist

Codex must review all applicable dimensions below.

### A. Subject fidelity and realism
- face realism
- eye quality
- skin texture
- hair realism
- teeth / mouth quality
- body proportions
- anatomy consistency
- pose accuracy

### B. Limbs and extremities
- hands / fingers
- feet / toes when visible
- distorted limbs
- joint plausibility

### C. Surface and contact detail
- clothing / fabric
- contact points
- object/body collisions
- deformation realism
- soft-body cues
- texture detail

### D. Cinematic and environmental quality
- lighting
- shadows
- reflections
- background coherence
- camera / lens realism

### E. Failure / artifact detection
- generation artifacts
- identity drift
- over-smoothing
- plastic skin
- waxy faces
- unwanted style contamination

### F. Instruction compliance
- prompt compliance
- negative prompt compliance if applicable
- scene completeness
- intended emotional / stylistic tone

## Scoring model

Score each major category 0–5.

- 5 = excellent / no visible issue
- 4 = strong / minor issue only
- 3 = acceptable but noticeably imperfect
- 2 = weak / requires revision
- 1 = poor / major defect
- 0 = failed / unusable

Recommended decision thresholds:

- **Pass**: no category below 3 and average >= 4.0
- **Pass with issues**: no blocking defect, average >= 3.3
- **Fail**: any blocking defect, or average < 3.3

## Blocking defects

Immediate fail examples:

- severely malformed face or eyes
- broken hands or fused fingers in a focal subject
- implausible anatomy
- severe lighting inconsistency
- obvious object penetration / collision error
- obvious prompt miss
- corrupt or incomplete image file

## Evidence to save

- artifact review record
- issue list
- score summary
- decision
- references to the specific output path and workflow used

## Row016 machine certification contract

Every promoted image or explicitly bounded image set must bind these literal fields in
one scope-matched record:

- `technical_image_qa`
- `visual_review_scorecard`
- `prompt_alignment`
- `artifact_hash_manifest`
- `promotion_decision`

Promotion is fail-closed. It requires passing technical QA, no visual category below 3,
an average score of at least 4.0, no blocking defect, an explicit prompt-alignment pass,
verified SHA256 identities for every promoted artifact, a nonempty promoted-output list,
and complete upstream quality authority for the claimed scope. Lane or matrix
certification does not silently become per-image promotion or full-project certification.

## Row017 global review contract

A localized visual change must be reviewed in this order:

1. inspect the whole source frame before the localized change
2. inspect the required target region at useful zoom
3. inspect every visible non-target region for drift or damage
4. inspect the whole output frame again after the localized change
5. reject the localized result when any global defect is present

The machine record must contain `whole_frame_visual_scan`,
`required_target_region_check`, `required_non_target_region_scan`,
`hands_face_body_background_contact_lighting_check`, and
`reject_on_any_global_defect`. A category outside the frame may be marked
`not_applicable` only when it was explicitly inspected and a reason is recorded. A local
target pass never overrides a defect elsewhere in the visible frame.

## RunPod strict self-hosted LLM visual QA (binding)

For autonomous product / Class A / Proof_Landed / identity GATE CLEARED paths, visual
approval authority is the **high-end self-hosted Ollama vision model on RunPod**, not
weak `qwen2.5vl:7b` / `llava:13b` rubber-stamps and not generation receipts.

- Strategy: `Plan/Instructions/POD_STRICT_SELF_HOSTED_LLM_VISUAL_QA_STRATEGY.md`
- Receipt schema: `Plan/08_SCHEMAS/pod_strict_self_hosted_llm_visual_qa_receipt.schema.json`
- Executable: `Plan/07_IMPLEMENTATION/scripts/wave64_pod_strict_visual_qa.py`
- Default model: `WAVE64_STRICT_VLM_MODEL=qwen2.5vl:32b` (fail closed if missing)
- Dual gate: generation receipt ≠ visual approval; retain `human_frame_read` where already required
- Smoke may use weaker models only when explicitly labeled `lane=SMOKE`
