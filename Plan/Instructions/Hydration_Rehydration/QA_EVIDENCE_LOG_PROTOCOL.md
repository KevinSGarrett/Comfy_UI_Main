# QA Evidence Log Protocol

## Purpose

This protocol defines how Codex logs QA evidence for generated artifacts, workflows, scripts, models, prompts, and cumulative packs.

## QA evidence index location

```text
C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\QA_EVIDENCE_INDEX.md
```

## Evidence storage options

Preferred:

```text
C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence
```

Acceptable when artifact-specific:

```text
C:\Comfy_UI_Main\Plan\Instructions\Operations\Run_Records
C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts
C:\Comfy_UI_Main\Plan\Instructions\Reports
C:\Comfy_UI_Main\Plan\Instructions\Waves
```

## Required evidence index fields

- evidence_id
- artifact_id
- artifact_type
- tracker_id
- QA protocol used
- result
- evidence path
- known issues
- next action
- timestamp

## Result values

- pass
- pass_with_notes
- fail
- blocked
- pending_runtime_validation
- needs_retest

## Evidence completeness rule

Every completed item must point to at least one evidence record. A completed artifact without evidence must be downgraded to `pending_validation`.

## Visual / audio / video review rule

Image, video, and audio outputs must have explicit modality review records. A successful generation is not automatically a QA pass.
