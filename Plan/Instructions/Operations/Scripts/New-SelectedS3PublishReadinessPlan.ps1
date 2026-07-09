<#
.SYNOPSIS
Creates a local-only selected-lane S3 publish readiness plan.

.DESCRIPTION
Consumes the selected deploy-bundle rebuild plan and optional S3 runtime
transfer readiness evidence, then records the exact publish path that becomes
valid only after the manifest-scoped checkpoint and selected deploy-bundle
rebuild complete. This helper writes evidence only; it does not rebuild deploy
bundles, upload to S3, contact AWS, start EC2, stage, commit, push, or generate.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$SelectedDeployBundleRebuildPlanFile = "",
  [string]$S3RuntimeTransferReadinessFile = "",
  [string]$S3BaseUri = "",
  [string]$Region = "",
  [string]$OutFile = "",
  [string]$MarkdownOutFile = ""
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectPath {
  param([AllowNull()][object]$Path)
  if ($null -eq $Path) { return $null }
  $text = [string]$Path
  if ([string]::IsNullOrWhiteSpace($text)) { return $null }
  if ([System.IO.Path]::IsPathRooted($text)) { return [System.IO.Path]::GetFullPath($text) }
  return [System.IO.Path]::GetFullPath((Join-Path -Path $ProjectRoot -ChildPath $text))
}

function ConvertTo-ProjectRelativePath {
  param([AllowNull()][object]$Path)
  $resolved = Resolve-ProjectPath -Path $Path
  if ($null -eq $resolved) { return $null }
  $rootFull = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/") + [System.IO.Path]::DirectorySeparatorChar
  $targetFull = [System.IO.Path]::GetFullPath($resolved)
  if ($targetFull.StartsWith($rootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    return $targetFull.Substring($rootFull.Length).Replace("\", "/")
  }
  return $targetFull
}

function Read-JsonFile {
  param([Parameter(Mandatory = $true)][string]$Path)
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Find-LatestFile {
  param([string]$Directory, [string]$Filter)
  if (-not (Test-Path -LiteralPath $Directory -PathType Container)) { return $null }
  $item = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File |
    Sort-Object LastWriteTimeUtc, Name -Descending |
    Select-Object -First 1
  if ($null -eq $item) { return $null }
  return $item.FullName
}

function Read-EnvSummary {
  param([string]$Path)
  $map = @{}
  if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $map }
  foreach ($line in Get-Content -LiteralPath $Path) {
    if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
      $name = $matches[1]
      $value = [string]$matches[2]
      $map[$name] = $value.Trim().Trim('"').Trim("'")
    }
  }
  return $map
}

function Get-EnvValue {
  param([hashtable]$Map, [string]$Name)
  if ($Map.ContainsKey($Name)) { return [string]$Map[$Name] }
  return ""
}

function Test-S3BaseUriShape {
  param([string]$Uri)
  return (![string]::IsNullOrWhiteSpace($Uri) -and $Uri -match '^s3://[^/]+/.+')
}

function Convert-PlaceholderProjectPathToAbsoluteText {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return "" }
  if ($Path -match '^[A-Za-z]:[\\/]' -or $Path -match '^[\\/]{2}') { return $Path }
  return ("C:\Comfy_UI_Main\" + $Path.TrimStart("\", "/").Replace("/", "\"))
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
Set-Location -LiteralPath $ProjectRoot

$runtimeDir = Resolve-ProjectPath -Path "Plan\Instructions\QA\Evidence\Runtime_Readiness"
if ([string]::IsNullOrWhiteSpace($SelectedDeployBundleRebuildPlanFile)) {
  $SelectedDeployBundleRebuildPlanFile = Find-LatestFile -Directory $runtimeDir -Filter "W66_SELECTED_DEPLOY_BUNDLE_REBUILD_PLAN_*.json"
}
if ([string]::IsNullOrWhiteSpace($S3RuntimeTransferReadinessFile)) {
  $S3RuntimeTransferReadinessFile = Find-LatestFile -Directory $runtimeDir -Filter "W66_S3_RUNTIME_TRANSFER_READINESS_*.json"
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_SELECTED_S3_PUBLISH_READINESS_PLAN_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$selectedRebuildResolved = Resolve-ProjectPath -Path $SelectedDeployBundleRebuildPlanFile
$s3ReadinessResolved = Resolve-ProjectPath -Path $S3RuntimeTransferReadinessFile
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile

if ([string]::IsNullOrWhiteSpace($selectedRebuildResolved) -or -not (Test-Path -LiteralPath $selectedRebuildResolved -PathType Leaf)) {
  throw "Selected deploy-bundle rebuild plan missing."
}

$selectedRebuild = Read-JsonFile -Path $selectedRebuildResolved
$s3ReadinessExists = (![string]::IsNullOrWhiteSpace($s3ReadinessResolved) -and (Test-Path -LiteralPath $s3ReadinessResolved -PathType Leaf))
$s3Readiness = if ($s3ReadinessExists) { Read-JsonFile -Path $s3ReadinessResolved } else { $null }

$envMap = Read-EnvSummary -Path (Join-Path $ProjectRoot ".env")
if ([string]::IsNullOrWhiteSpace($Region)) {
  $Region = Get-EnvValue -Map $envMap -Name "AWS_REGION"
}
if ([string]::IsNullOrWhiteSpace($Region)) {
  $Region = Get-EnvValue -Map $envMap -Name "EC2_REGION"
}
if ([string]::IsNullOrWhiteSpace($Region)) {
  $Region = "us-east-1"
}
if ([string]::IsNullOrWhiteSpace($S3BaseUri)) {
  $S3BaseUri = Get-EnvValue -Map $envMap -Name "COMFY_DEPLOY_BUNDLE_S3_URI"
}

$selectedLaneId = [string]$selectedRebuild.selected_lane_id
$expectedManifestRel = [string]$selectedRebuild.expected_manifest_after_rebuild
$expectedZipRel = [string]$selectedRebuild.expected_zip_after_rebuild
$expectedManifestPath = Convert-PlaceholderProjectPathToAbsoluteText -Path $expectedManifestRel
$expectedZipPath = Convert-PlaceholderProjectPathToAbsoluteText -Path $expectedZipRel
$expectedManifestConcrete = ($expectedManifestPath -notmatch '<timestamp>')
$expectedZipConcrete = ($expectedZipPath -notmatch '<timestamp>')
$expectedManifestExists = ($expectedManifestConcrete -and (Test-Path -LiteralPath $expectedManifestPath -PathType Leaf))
$expectedZipExists = ($expectedZipConcrete -and (Test-Path -LiteralPath $expectedZipPath -PathType Leaf))

$s3ReadinessResult = if ($s3ReadinessExists) { [string]$s3Readiness.result } else { "missing" }
$s3ReadinessReady = ($s3ReadinessExists -and [string]$s3Readiness.result -eq "ready_local_only")
$s3BaseUriValid = Test-S3BaseUriShape -Uri $S3BaseUri

$blockers = @(
  if ([string]$selectedRebuild.result -ne "selected_deploy_bundle_rebuild_plan_ready_after_clean_checkpoint") { "selected_deploy_bundle_rebuild_plan_not_ready" }
  if (-not [bool]$selectedRebuild.current_git_clean) { "manifest_scoped_checkpoint_not_yet_executed_clean" }
  if (-not [bool]$selectedRebuild.deploy_bundle_rebuilt) { "selected_deploy_bundle_rebuild_not_completed" }
  if (-not $expectedManifestExists) { "selected_deploy_bundle_manifest_missing_until_rebuild" }
  if (-not $expectedZipExists) { "selected_deploy_bundle_zip_missing_until_rebuild" }
  if ("explicit_user_target_runtime_selection_required" -in @($selectedRebuild.blockers_before_rebuild)) { "explicit_user_target_runtime_selection_required" }
  if (-not $s3ReadinessExists) { "s3_runtime_transfer_readiness_not_available" }
  elseif (-not $s3ReadinessReady) { "s3_runtime_transfer_readiness_not_ready" }
  if (-not $s3BaseUriValid) { "approved_s3_base_uri_required" }
) | Select-Object -Unique

$publishManifestArg = if ($expectedManifestConcrete) { $expectedManifestPath } else { "C:\Comfy_UI_Main\$expectedManifestRel" }
$publishOutFile = "C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_SELECTED_DEPLOY_BUNDLE_S3_PUBLISH_DRY_RUN_<timestamp>.json"
$publishS3BaseArg = if ($s3BaseUriValid) { $S3BaseUri } else { "<approved-s3-base-uri>" }
$publishDryRunCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Publish-DeployBundleToS3.ps1 -BundleManifestFile $publishManifestArg -S3BaseUri $publishS3BaseArg -Region $Region -OutFile $publishOutFile"
$publishExecuteCommand = "$publishDryRunCommand -Execute"

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "selected_s3_publish_readiness_plan"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  result = "blocked_selected_s3_publish_readiness_waiting_for_clean_rebuild"
  local_only = $true
  github_api_contacted = $false
  aws_contacted = $false
  civitai_contacted = $false
  s3_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  prompt_posted = $false
  active_runtime_marker_written = $false
  stage_attempted = $false
  commit_attempted = $false
  push_attempted = $false
  reset_attempted = $false
  checkout_attempted = $false
  deploy_bundle_rebuilt = $false
  s3_publish_attempted = $false
  s3_upload_execute_allowed = $false
  masks_consumed_as_truth = $false
  masks_promoted = $false
  wave70_hard_gate_rerun = $false
  wave71_plus_activated = $false
  full_project_certification_allowed = $false
  selected_lane_id = $selectedLaneId
  selected_deploy_bundle_rebuild_plan = ConvertTo-ProjectRelativePath -Path $selectedRebuildResolved
  selected_rebuild_result = [string]$selectedRebuild.result
  selected_rebuild_ready_after_clean_checkpoint = [bool]$selectedRebuild.ready_to_rebuild_after_clean_checkpoint
  selected_rebuild_current_git_clean = [bool]$selectedRebuild.current_git_clean
  selected_rebuild_command = [string]$selectedRebuild.rebuild_command
  run_package_manifest = [string]$selectedRebuild.run_package_manifest
  expected_manifest_after_rebuild = $expectedManifestRel
  expected_zip_after_rebuild = $expectedZipRel
  expected_manifest_exists_now = $expectedManifestExists
  expected_zip_exists_now = $expectedZipExists
  s3_runtime_transfer_readiness = $(if ($s3ReadinessExists) { ConvertTo-ProjectRelativePath -Path $s3ReadinessResolved } else { $null })
  s3_runtime_transfer_readiness_result = $s3ReadinessResult
  s3_runtime_transfer_ready_local_only = $s3ReadinessReady
  s3_runtime_transfer_missing_config = $(if ($s3ReadinessExists -and $null -ne $s3Readiness.missing_config) { @($s3Readiness.missing_config) } else { @() })
  region = $Region
  s3_base_uri_present = $s3BaseUriValid
  s3_base_uri_source = $(if ($s3BaseUriValid) { if (![string]::IsNullOrWhiteSpace($envMap["COMFY_DEPLOY_BUNDLE_S3_URI"]) -and $S3BaseUri -eq [string]$envMap["COMFY_DEPLOY_BUNDLE_S3_URI"]) { ".env:COMFY_DEPLOY_BUNDLE_S3_URI" } else { "parameter" } } else { $null })
  ready_for_s3_publish_after_rebuild = $false
  publish_dry_run_command = $publishDryRunCommand
  publish_execute_command_requires_explicit_user_intent = $publishExecuteCommand
  required_pre_publish_checks = @(
    "manifest_scoped_checkpoint_execute completed with clean_worktree=true",
    "selected deploy-bundle rebuild completed",
    "DEPLOY_BUNDLE_MANIFEST.json result=pass_local_only",
    "source_git_clean=true",
    "source_git_status_count=0",
    "bundle_zip exists",
    "bundle_zip_sha256 matches actual zip hash",
    "s3_runtime_transfer_readiness result=ready_local_only",
    "Publish-DeployBundleToS3.ps1 dry-run result=dry_run_ready_to_upload"
  )
  blockers_before_publish = $blockers
  command_sequence = @(
    [ordered]@{ name = "manifest_scoped_checkpoint_execute"; command = "Requires explicit user checkpoint intent before staging/commit/push."; mutates_git = $true; external_contact = $true }
    [ordered]@{ name = "selected_deploy_bundle_rebuild"; command = [string]$selectedRebuild.rebuild_command; mutates_git = $false; external_contact = $false }
    [ordered]@{ name = "package_deploy_matrix_recheck"; command = "Rerun active runtime queue package/deploy matrix after rebuild."; mutates_git = $false; external_contact = $false }
    [ordered]@{ name = "s3_runtime_transfer_readiness_recheck"; command = "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-S3RuntimeTransferReadiness.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_S3_RUNTIME_TRANSFER_READINESS_<timestamp>.json"; mutates_git = $false; external_contact = $false }
    [ordered]@{ name = "selected_s3_publish_dry_run"; command = $publishDryRunCommand; mutates_git = $false; external_contact = $false }
    [ordered]@{ name = "selected_s3_publish_execute_after_explicit_intent"; command = $publishExecuteCommand; mutates_git = $false; external_contact = $true }
    [ordered]@{ name = "ec2_static_proof_execute_still_blocked"; command = "Remain blocked until S3 publish proof and runtime lane gates pass."; mutates_git = $false; external_contact = $false }
  )
  checkpoint_boundary = "Selected S3 publish readiness plan only. This artifact does not stage, commit, push, reset, checkout, rebuild deploy bundles, upload to S3, contact AWS, start EC2, post prompts, generate, write runtime markers, promote masks, rerun Wave70 gates, switch to Jira bookkeeping, or activate Wave71+."
  next_action = "After explicit manifest-scoped checkpoint and selected deploy-bundle rebuild, rerun S3 runtime transfer readiness and then run Publish-DeployBundleToS3.ps1 dry-run against the concrete rebuilt manifest before any upload execute or EC2 proof."
}

[System.IO.Directory]::CreateDirectory((Split-Path -Path $outFileResolved -Parent)) | Out-Null
[System.IO.Directory]::CreateDirectory((Split-Path -Path $markdownResolved -Parent)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 50) + [Environment]::NewLine, $utf8NoBom)

$markdown = @"
# Selected S3 Publish Readiness Plan

- created_at: $($record.created_at)
- result: $($record.result)
- selected_lane_id: $selectedLaneId
- selected_rebuild_ready_after_clean_checkpoint: $($record.selected_rebuild_ready_after_clean_checkpoint)
- expected_manifest_exists_now: $expectedManifestExists
- expected_zip_exists_now: $expectedZipExists
- s3_runtime_transfer_readiness_result: $s3ReadinessResult
- s3_base_uri_present: $s3BaseUriValid
- ready_for_s3_publish_after_rebuild: $($record.ready_for_s3_publish_after_rebuild)

## Publish Dry Run Command

```powershell
$publishDryRunCommand
```

## Boundary

$($record.checkpoint_boundary)

## Next Action

$($record.next_action)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

Write-Host "Wrote selected S3 publish readiness plan: $outFileResolved"
$record | ConvertTo-Json -Depth 50
