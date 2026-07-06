# Itemized List Update Protocol

## Purpose

This protocol defines how Codex updates the itemized list so every deliverable is visible and traceable.

## Itemized list location

```text
C:\Comfy_UI_Main\Plan\Items
```

## When to update itemized lists

Update itemized list records whenever Codex creates or changes:

- instruction files
- scripts
- schemas
- templates
- trackers
- manifests
- validation reports
- QA evidence
- model registry records
- workflow files
- generated artifact records
- cumulative packs

## Required itemized-list fields

Recommended fields:

- wave
- item_id
- title
- description
- evidence_path
- implementation_status
- qa_status
- notes

## Item status values

- planned
- in_progress
- created
- updated
- implemented
- pending_validation
- qa_passed
- qa_failed
- blocked
- complete
- superseded

## Source-of-truth rule

If an itemized-list supplement exists for a wave, it must point to the concrete evidence file or folder. Do not create vague records without file paths.

## Completion rule

The itemized list can say a file was created, but it must not say an item is fully complete unless:

- tracker row agrees
- QA evidence exists
- done certification exists
