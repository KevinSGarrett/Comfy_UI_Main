# Wave 15 — Base Output QA and Promotion Plan

A base image output is not promoted because ComfyUI produced a file. It must pass evidence and QA gates.

## Required QA groups

- Decode/file QA
- Engine family compatibility QA
- Prompt-plan alignment QA
- Composition/frame integrity QA
- Identity/environment preservation QA
- Artifact/watermark/text QA
- Fallback reason QA when fallback was used

## Promotion outcomes

| Outcome | Meaning |
|---|---|
| `base_candidate_passed` | Output can feed downstream detail/refine/video workflows |
| `rerun_same_lane` | Same lane can retry with fixed seed/settings/prompt |
| `fallback_lane_required` | Next compatible lane must be selected |
| `blocked_missing_runtime_proof` | Template/model/object_info proof is missing |
| `blocked_family_mismatch` | Checkpoint/LoRA/template families are incompatible |
| `blocked_unrecoverable_quality` | Max attempts used or QA failure is not repairable |

## Downstream handoff

A passed base image can feed:

- Regional inpaint/detail
- Masked correction
- Control map extraction
- Upscale/refine
- Video keyframe generation
- Audio scene alignment planning

It still cannot bypass downstream QA.
