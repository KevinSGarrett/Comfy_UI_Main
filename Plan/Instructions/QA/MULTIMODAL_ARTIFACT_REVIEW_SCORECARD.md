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
