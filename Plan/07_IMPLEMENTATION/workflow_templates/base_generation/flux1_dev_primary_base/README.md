# Flux1 Dev primary template

This directory contains the API workflow and patch/runtime contracts for the
`flux1_dev_primary_base` lane. The graph is extracted from the native Flux
Schnell branch in the authoritative Main Flow and retargeted to the declared
Flux1 Dev checkpoint with higher-quality static settings.

## Current blocker

The workflow is statically implemented, but the exact checkpoint SHA256 and a
matching local model file are not available. `runtime_requirements.json` keeps
the lane fail-closed until both are recorded and verified.

Both checked-in mirrors intentionally use the canonical Plan workflow path in
their metadata. `Workflows/base_generation/ACTIVE_LANES.json` exposes the
runtime mirror, while contract validation requires the four mirrored files to
remain byte-identical.

## Promotion rule

This template is not promoted until object_info, model path/hash, model-loading,
output, technical QA, and visual QA evidence pass.
