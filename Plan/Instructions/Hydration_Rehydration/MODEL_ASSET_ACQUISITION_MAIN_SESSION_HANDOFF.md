# Main Session Model Asset Acquisition Handoff

Status: active durable steering

The main session must read and follow:

- `Plan/Instructions/Operations/UNIFIED_MODEL_ASSET_ACQUISITION_AND_WIRING_PROTOCOL.md`
- `Plan/10_REGISTRIES/model_acquisition_control_registry.json`
- `Plan/08_SCHEMAS/model_asset_acquisition_request.schema.json`
- `Plan/07_IMPLEMENTATION/scripts/manage_model_asset_acquisition.py`

## Required posture

Asset acquisition and wiring are part of implementation. For every concrete image, video, audio, control, preprocessing, or QA lane that needs a missing model/resource, complete the exact acquisition chain in the same delivery batch or record one exact external blocker. Do not leave a generic end-of-project download/wiring backlog.

Use existing exact-hash bytes first. Otherwise prefer a pinned official/creator Hugging Face source or an exact Civitai model version/file. Use the `.env` Civitai credential without printing it. When API download is blocked, create a browser request, use the signed-in Chrome session, and ingest the browser file through the same hash/placement/registry/wiring path. Do not export browser cookies or save tokens in URLs.

`content_based_suppression` remains `false`; adult or NSFW labels are metadata, not filters. License, paid access, gated access, and compatibility still must be recorded and respected.

Downloaded is not done. Correct folder placement, registry and queue updates, workflow/runtime-requirements bindings, `/object_info` visibility, bounded runtime execution, and modality QA remain required before promotion.

This handoff does not authorize EC2 start, S3 mutation, mask promotion, Wave70 hard-gate reruns, Wave71+ activation, Jira mutation, or reopening completed runtime proof.
