# Wave 36 Registry and Search Metadata System

Search should work across the whole system.

## Search targets

- docs
- schemas
- registries
- scripts
- workflows
- models
- LoRAs
- references
- QA evidence
- generated outputs
- release packets

## Search fields

```text
artifact_id
artifact_type
path
owner_domain
engine_family
workflow_type
wave
status
tags
proof_status
qa_status
promotion_decision
archive_status
```

## Rule

A search result should show whether an artifact is canonical, experimental, archived, blocked, or proof-ready.
