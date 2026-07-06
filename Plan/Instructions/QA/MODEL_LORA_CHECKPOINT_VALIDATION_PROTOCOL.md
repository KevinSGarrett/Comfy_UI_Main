# Model / LoRA / Checkpoint Validation Protocol

## Purpose

This protocol validates checkpoints, LoRAs, VAEs, ControlNet assets, and related model artifacts before they are considered usable.

## Review stages

### Stage 1 — Identity and metadata
Record:
- model name
- model type
- base model / family
- version
- file name
- file hash if available
- source URL
- local path
- intended use
- workflow lane

### Stage 2 — File integrity
- verify file exists
- verify non-zero reasonable size
- verify hash if available
- verify extension and expected format

### Stage 3 — Compatibility
- Flux / SDXL / Pony compatibility where relevant
- expected loader compatibility
- VAE / CLIP / text-encoder dependencies if known
- control or refinement lane compatibility if used

### Stage 4 — Load validation
- attempt load in the relevant workflow context
- confirm no immediate loader failure
- confirm no obvious corruption

### Stage 5 — Sample output validation
- run a minimal representative generation or use-case test
- inspect outputs using the relevant modality QA protocol

## Status values

- registered_not_tested
- integrity_verified
- load_verified
- qa_verified
- rejected
- duplicate_or_superseded

## Rejection examples

- corrupt file
- incompatible base family
- loader failure
- repeated runtime crash
- no useful output
- severe quality regression
