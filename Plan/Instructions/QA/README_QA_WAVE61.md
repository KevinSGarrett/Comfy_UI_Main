# README — Wave 61 QA and Review System

Wave 61 adds the strict autonomous QA, testing, visual review, audio review, video review, workflow validation, failure classification, and done-certification framework.

## Purpose

Codex Desktop must **not** declare work complete merely because files exist. It must prove that work was implemented, executed, inspected, verified, recorded, and certified.

This QA layer is the enforcement system for that rule.

## Start here

Read these in order:

1. `Plan/Instructions/QA/STRICT_AUTONOMOUS_QA_MASTER_PROTOCOL.md`
2. `Plan/Instructions/QA/COMFYUI_WORKFLOW_TESTING_PROTOCOL.md`
3. `Plan/Instructions/QA/MULTIMODAL_ARTIFACT_REVIEW_SCORECARD.md`
4. `Plan/Instructions/QA/WAVE70_MASK_ALIGNMENT_QA_PROTOCOL.md` when reviewing any Wave70 mask or overlay
5. `Plan/Instructions/QA/DONE_CERTIFICATION_EVIDENCE_PROTOCOL.md`
6. Then open the modality-specific protocol for the artifact under review.

## Core rule

No item may be marked complete unless the following are all true:

- implementation is complete
- a test run occurred
- QA inspection occurred
- evidence exists
- tracker and itemized list were updated
- known issues were reviewed
- done certification was created

## Packaging status

Wave 61 provides the framework, templates, and dry-run helper scripts. It does **not** mean live image/video/audio review has already been executed for every artifact in the broader project.
