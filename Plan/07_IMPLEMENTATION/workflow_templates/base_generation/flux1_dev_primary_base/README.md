# Flux1 Dev primary template

This directory contains the API workflow and patch/runtime contracts for the
`flux1_dev_primary_base` lane. The graph is extracted from the native Flux
Schnell branch in the authoritative Main Flow and retargeted to the declared
Flux1 Dev checkpoint with higher-quality static settings.

## Current blocker

The workflow is statically implemented. The immutable Comfy-Org revision,
licensed source, byte count, and checkpoint SHA256 are recorded, but a matching
local model file is not present. `runtime_requirements.json` keeps the lane
fail-closed until license-authorized installation and observed-hash validation.
The local installer is dry-run by default, resumes through a `.partial` file,
requires a hash-bound noncommercial acceptance record before network contact,
and atomically installs only after exact byte-count and SHA256 verification.
The checked-in acceptance template is deliberately `accepted: false`; changing
it is a legal-use assertion, not an automation or Codex approval prompt.

Both checked-in mirrors intentionally use the canonical Plan workflow path in
their metadata. `Workflows/base_generation/ACTIVE_LANES.json` exposes the
runtime mirror, while contract validation requires the four mirrored files to
remain byte-identical.

## Promotion rule

This template is not promoted until object_info, model path/hash, model-loading,
output, technical QA, and visual QA evidence pass.
