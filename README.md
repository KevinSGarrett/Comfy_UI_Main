# Comfy_UI_Main

This is the main local project root for the autonomous ComfyUI hyperrealism system.

## Working Directories

```text
C:\Comfy_UI_Main\
  Plan\                 Source-of-truth project plan, tracker, instructions, QA evidence
  Workflows\            Exported ComfyUI workflow files ready for runtime use
  models\               Local model placement guide; model binaries are git-ignored
  runtime_artifacts\    Pullbacks, run outputs, and review material; large outputs stay out of git
  configs\              Local runtime/config handoff files that are safe to commit
```

## Active Workflows

The first runtime lane is:

```text
Workflows\base_generation\sdxl_low_risk_fallback_lane\workflow.api.json
```

The second queued lane is:

```text
Workflows\base_generation\sdxl_realvisxl_base_lane\workflow.api.json
```

The authoritative planning copies remain under:

```text
Plan\07_IMPLEMENTATION\workflow_templates\base_generation
```

## Current Runtime Gate

GitHub and Civitai keys are loaded from `.env`, but they do not prove AWS access. EC2 work remains blocked until AWS browser/SSO auth is refreshed and the auth gate reports the expected account `029530099913`.

Do not commit `.env`, model binaries, private keys, or generated media outputs.

## Root Tools

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\Sync-WorkflowExports.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\Test-RootProjectPreflight.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-WorkflowRunPackage.ps1 -LaneId sdxl_low_risk_fallback_lane
powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-WorkflowRunPackage.ps1 -LaneId sdxl_low_risk_fallback_lane -PromptProfileFile PromptProfiles\base_generation\hyperreal_editorial_portrait.json -RunId sdxl_low_risk_fallback_lane_hyperreal_editorial_portrait_v1
```
