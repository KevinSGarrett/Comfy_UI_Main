<#
.SYNOPSIS
Validates explicit single-reference-edit run-package selection locally.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$encoding = New-Object System.Text.UTF8Encoding($false)
$tempRoot = Join-Path $ProjectRoot "runtime_artifacts\regression\workflow_capability_$([guid]::NewGuid().ToString('N'))"
$checks = New-Object System.Collections.ArrayList

function Write-JsonNoBom([object]$Value, [string]$Path, [int]$Depth = 20) {
  $directory = Split-Path -Parent $Path
  $null = New-Item -ItemType Directory -Force -Path $directory
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

function Add-Check([string]$Name, [bool]$Passed, [object]$Observed, [object]$Expected) {
  [void]$checks.Add([ordered]@{ name=$Name; result=$(if($Passed){"pass"}else{"fail"}); observed=$Observed; expected=$Expected })
}

try {
  $sourcePath = Join-Path $tempRoot "source.png"
  $null = New-Item -ItemType Directory -Force -Path $tempRoot
  Add-Type -AssemblyName System.Drawing
  $bitmap = New-Object System.Drawing.Bitmap 8,8
  try {
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    try { $graphics.Clear([System.Drawing.Color]::CornflowerBlue) } finally { $graphics.Dispose() }
    $bitmap.Save($sourcePath, [System.Drawing.Imaging.ImageFormat]::Png)
  } finally { $bitmap.Dispose() }

  $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath).Hash.ToLowerInvariant()
  $sourceSize = (Get-Item -LiteralPath $sourcePath).Length
  $sourceRelative = $sourcePath.Substring($ProjectRoot.TrimEnd("\", "/").Length).TrimStart("\", "/").Replace("\", "/")
  $profilePath = Join-Path $tempRoot "edit_profile.json"
  $profile = [ordered]@{
    profile_id = "flux2_dev_edit_capability_regression"
    target_lane_id = "flux2_dev_primary_base"
    source_binding = [ordered]@{
      project_path = $sourceRelative
      staged_filename = "flux2_dev_reference_source.png"
      size_bytes = $sourceSize
      sha256 = $sourceHash
    }
    request_patch_values = [ordered]@{
      source_image = "flux2_dev_reference_source.png"
    }
    expected_outputs = [ordered]@{
      artifact_type = "image"
      minimum_output_count = 1
      output_prefix = "flux2_dev_primary_base/capability_regression_edit"
    }
  }
  Write-JsonNoBom -Value $profile -Path $profilePath

  $packageRoot = Join-Path $tempRoot "packages"
  $builder = Join-Path $ProjectRoot "tools\New-WorkflowRunPackage.ps1"
  $output = @(& $builder -ProjectRoot $ProjectRoot -WorkflowGroup base_generation -LaneId flux2_dev_primary_base -WorkflowCapability single_reference_edit -PromptProfileFile $profilePath -PackageRoot $packageRoot -RunId flux2_dev_edit_capability_regression -AllowNonFirstLane 2>&1)
  $builderExitCode = $LASTEXITCODE
  $packageDir = Join-Path $packageRoot "flux2_dev_edit_capability_regression"
  $manifest = Get-Content -LiteralPath (Join-Path $packageDir "RUN_PACKAGE_MANIFEST.json") -Raw | ConvertFrom-Json
  $request = Get-Content -LiteralPath (Join-Path $packageDir "prompt_request.json") -Raw | ConvertFrom-Json
  $smoke = Get-Content -LiteralPath (Join-Path $packageDir "lane_files\smoke_test_request.json") -Raw | ConvertFrom-Json
  $packagedWorkflow = Join-Path $packageDir "lane_files\workflow.api.json"
  $sourceWorkflow = Join-Path $ProjectRoot "Workflows\base_generation\flux2_dev_primary_base\single_reference_edit.api.json"

  Add-Check "builder_passes" ($builderExitCode -eq 0 -and [string]$manifest.result -eq "pass_local_only") $builderExitCode 0
  Add-Check "capability_recorded" ([string]$manifest.workflow_capability -eq "single_reference_edit") $manifest.workflow_capability "single_reference_edit"
  Add-Check "edit_workflow_selected" ([string]$manifest.selected_workflow -eq "Workflows/base_generation/flux2_dev_primary_base/single_reference_edit.api.json") $manifest.selected_workflow "single_reference_edit.api.json"
  Add-Check "workflow_hash_matches_edit_export" ((Get-FileHash -Algorithm SHA256 -LiteralPath $packagedWorkflow).Hash -eq (Get-FileHash -Algorithm SHA256 -LiteralPath $sourceWorkflow).Hash) $true $true
  Add-Check "source_binding_hash_verified" ([bool]$manifest.prompt_profile.source_binding.valid -and [string]$manifest.prompt_profile.source_binding.sha256 -eq $sourceHash) $manifest.prompt_profile.source_binding.sha256 $sourceHash
  Add-Check "source_image_patched" ([string]$request.prompt."4".inputs.image -eq "flux2_dev_reference_source.png") $request.prompt."4".inputs.image "flux2_dev_reference_source.png"
  $canonicalEditPrompt = "Preserve the subject identity, anatomy, pose, camera, studio, workbench, tools, glass objects, lighting, texture, and composition. Change only the tailored charcoal clothing to deep cobalt blue wool with the same cut and fabric weave."
  Add-Check "canonical_edit_prompt_preserved" ([string]$request.prompt."7".inputs.text -eq $canonicalEditPrompt) $request.prompt."7".inputs.text $canonicalEditPrompt
  Add-Check "smoke_capability_selected" ([string]$smoke.capability -eq "single_reference_edit" -and [string]$smoke.workflow_path_policy -eq "explicit_run_package_capability_selection") $smoke.capability "single_reference_edit"
  Add-Check "local_only_boundary" ([bool]$manifest.local_only -and !$manifest.aws_contacted -and !$manifest.github_api_contacted -and !$manifest.civitai_contacted -and !$manifest.comfyui_contacted -and !$manifest.ec2_started -and !$manifest.generation_executed) $true $true
} finally {
  if (Test-Path -LiteralPath $tempRoot -PathType Container) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
}

$failures = @($checks | Where-Object result -ne "pass")
$record = [ordered]@{
  schema_version="1.0"; created_at=[datetimeoffset]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
  result=$(if($failures.Count -eq 0){"pass_local_only"}else{"fail"}); local_only=$true
  aws_contacted=$false; comfyui_contacted=$false; ec2_started=$false; generation_executed=$false
  check_count=$checks.Count; failed_check_count=$failures.Count; checks=@($checks); failures=@($failures)
}
if ([string]::IsNullOrWhiteSpace($OutFile)) { $OutFile = Join-Path $ProjectRoot "runtime_artifacts\validation\WORKFLOW_RUN_PACKAGE_CAPABILITY_SELECTION.json" }
Write-JsonNoBom -Value $record -Path $OutFile -Depth 30
$record | ConvertTo-Json -Depth 30
if ($failures.Count -gt 0) { exit 2 }
