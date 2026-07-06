# Wave 01 GitHub Issue / Project Import Strategy

## Goal

The tracker CSV is too large to manually manage inside the blueprint. It should eventually become structured GitHub issues or project-board items.

## Import principle

Do not import all tracker rows at once without grouping. Start by grouping rows into epics.

## Recommended epics

```text
EPIC-01 Repo and local bootstrap
EPIC-02 Source inventory and tracker reconciliation
EPIC-03 Model asset registry and S3 hydration
EPIC-04 Workflow JSON validation
EPIC-05 Engine router and LoRA compatibility
EPIC-06 Mask factory
EPIC-07 Pass planner and orchestrator
EPIC-08 Image base/refine/detail workflows
EPIC-09 Multi-character workflows
EPIC-10 Video/GIF workflows
EPIC-11 Audio/AV sync workflows
EPIC-12 EC2 runtime proof and deployment
EPIC-13 QA and release gates
```

## Tracker row to issue fields

Map:

```text
Task_ID → issue external_id
Task_Name → issue title
Detailed_Action → issue body
Completion_Criteria → acceptance criteria
Validation_Method → testing section
Output_Artifact → deliverables
Evidence_Path → evidence path
Priority → priority label
Risk_Level → risk label
Requires_GPU → gpu label
Requires_ComfyUI → comfyui label
Requires_Model_Download → model-assets label
Requires_Video_Runtime → video-runtime label
Requires_Audio_Runtime → audio-runtime label
```

## Import safety

Before creating issues, generate a dry-run import file:

```text
manifests/github_issue_import/waveXX_issue_import_dry_run.json
```

The AI system must not mass-create thousands of GitHub issues without a filtered import plan.
