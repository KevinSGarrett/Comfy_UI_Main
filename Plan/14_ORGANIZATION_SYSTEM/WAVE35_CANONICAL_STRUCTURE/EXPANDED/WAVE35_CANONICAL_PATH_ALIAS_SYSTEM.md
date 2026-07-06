# Wave 35 Canonical Path Alias System

Path aliases prevent hardcoded path chaos.

## Recommended aliases

```text
$SYSTEM_ROOT
$REPO_ROOT
$COMFYUI_ROOT
$MODELS_ROOT
$LORAS_ROOT
$WORKFLOWS_ROOT
$REFERENCE_ASSETS_ROOT
$OUTPUTS_ROOT
$QA_EVIDENCE_ROOT
$MANIFESTS_ROOT
$EC2_SYNC_ROOT
$APP_MODE_ROOT
$RELEASES_ROOT
```

## Rule

Scripts should use aliases or config values, not random hardcoded paths.
