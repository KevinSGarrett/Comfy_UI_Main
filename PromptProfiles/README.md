# PromptProfiles

Prompt profiles provide named local prompt overrides for exported workflow lanes.

They do not change the authoritative lane templates. `tools\New-WorkflowRunPackage.ps1` applies a profile to the packaged copy of `smoke_test_request.json`, then builds a patched ComfyUI `/prompt` request body inside `runtime_artifacts\run_packages`.
