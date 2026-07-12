# Multimodal Artifact Review Scorecard

## Purpose

This scorecard standardizes how Codex rates artifacts across image, video, audio, workflow, script, and model classes.

## Master categories

### Universal categories
- specification compliance
- technical integrity
- quality level
- usability / deployability
- evidence completeness

### Modality-specific categories
Add only the categories relevant to the artifact:

- image realism and anatomy
- video temporal consistency and motion realism
- audio clarity and content accuracy
- workflow reliability and reproducibility
- model compatibility and load success
- prompt control and contamination resistance

## Score scale

- 5 = excellent
- 4 = strong
- 3 = acceptable
- 2 = weak
- 1 = poor
- 0 = failed

## Recommended artifact scorecard template

| Category | Score (0-5) | Notes |
|---|---:|---|
| Spec compliance |  |  |
| Technical integrity |  |  |
| Quality level |  |  |
| Usability / deployability |  |  |
| Evidence completeness |  |  |
| Modality category 1 |  |  |
| Modality category 2 |  |  |
| Modality category 3 |  |  |

## Decision logic

- **Approved**: no blocking defects, no category below 3, evidence complete.
- **Conditionally approved**: minor non-blocking issues, explicitly documented.
- **Rejected**: blocking defect present, evidence incomplete, or low average quality.
- **Blocked**: required test or dependency missing.

## Mandatory note fields

Every scorecard record must include:

- artifact ID
- reviewer role = Codex Desktop autonomous QA
- artifact type
- generation/test method
- defects summary
- approval decision
- next action

## Row018 multi-sample image certification

Final portfolio image quality requires one lane-scoped record binding
`multi_seed_sample_set`, `aggregate_score`, `defect_rate_limit`, and
`portfolio_certification_record`. A certifying set must contain at least three distinct
seeds and at least two distinct prompt references, hash-bind every artifact, pass
technical and visual review for every sample, meet the declared aggregate and minimum
score thresholds, remain within the declared defect-rate limit, and cover every sample
on the target runtime. A local robustness set or a multi-prompt matrix may remain valid
for its bounded purpose without becoming portfolio certification.
