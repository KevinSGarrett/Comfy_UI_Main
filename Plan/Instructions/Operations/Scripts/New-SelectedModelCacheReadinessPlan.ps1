<#
.SYNOPSIS
Creates a local-only selected-lane model-cache readiness plan.

.DESCRIPTION
Reads selected package readiness, S3 runtime-transfer readiness, and local
object_info/model hash evidence, then records the required checkpoint model,
expected S3 model-cache URI, Publish-ModelToS3.ps1 commands, and
Install-EC2ModelFromS3.ps1 commands. This helper writes evidence only; it does
not upload models, contact AWS, start EC2, post prompts, run generation, stage,
commit, push, or promote masks.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$SelectedPackageReadinessFile = "",
  [string]$S3RuntimeTransferReadinessFile = "",
  [string]$ModelCacheS3BaseUri = "",
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
      $map[$matches[1]] = ([string]$matches[2]).Trim().Trim('"').Trim("'")
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

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
Set-Location -LiteralPath $ProjectRoot

$runtimeDir = Resolve-ProjectPath -Path "Plan\Instructions\QA\Evidence\Runtime_Readiness"
if ([string]::IsNullOrWhiteSpace($SelectedPackageReadinessFile)) {
  $SelectedPackageReadinessFile = Find-LatestFile -Directory $runtimeDir -Filter "W66_SELECTED_TARGET_RUNTIME_LANE_PACKAGE_READINESS_*.json"
}
if ([string]::IsNullOrWhiteSpace($S3RuntimeTransferReadinessFile)) {
  $S3RuntimeTransferReadinessFile = Find-LatestFile -Directory $runtimeDir -Filter "W66_S3_RUNTIME_TRANSFER_READINESS_*.json"
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_SELECTED_MODEL_CACHE_READINESS_PLAN_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$selectedReadinessResolved = Resolve-ProjectPath -Path $SelectedPackageReadinessFile
$s3ReadinessResolved = Resolve-ProjectPath -Path $S3RuntimeTransferReadinessFile
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile
if ([string]::IsNullOrWhiteSpace($selectedReadinessResolved) -or -not (Test-Path -LiteralPath $selectedReadinessResolved -PathType Leaf)) {
  throw "Selected package readiness evidence missing."
}

$selectedReadiness = Read-JsonFile -Path $selectedReadinessResolved
$runtimeRequirementsPath = Resolve-ProjectPath -Path $selectedReadiness.runtime_requirements
$objectInfoPath = Resolve-ProjectPath -Path $selectedReadiness.local_object_info_evidence
if ([string]::IsNullOrWhiteSpace($runtimeRequirementsPath) -or -not (Test-Path -LiteralPath $runtimeRequirementsPath -PathType Leaf)) {
  throw "Runtime requirements file missing from selected package readiness."
}
if ([string]::IsNullOrWhiteSpace($objectInfoPath) -or -not (Test-Path -LiteralPath $objectInfoPath -PathType Leaf)) {
  throw "Local object_info/model hash evidence missing from selected package readiness."
}
$runtimeRequirements = Read-JsonFile -Path $runtimeRequirementsPath
$objectInfo = Read-JsonFile -Path $objectInfoPath
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
if ([string]::IsNullOrWhiteSpace($ModelCacheS3BaseUri)) {
  $bucket = Get-EnvValue -Map $envMap -Name "S3_MODEL_BUCKET"
  $prefix = (Get-EnvValue -Map $envMap -Name "S3_MODEL_PREFIX").Trim("/")
  if (![string]::IsNullOrWhiteSpace($bucket) -and ![string]::IsNullOrWhiteSpace($prefix)) {
    $ModelCacheS3BaseUri = "s3://$bucket/$prefix"
  }
}

$s3ReadinessReady = ($s3ReadinessExists -and [string]$s3Readiness.result -eq "ready_local_only")
$s3BaseUriValid = Test-S3BaseUriShape -Uri $ModelCacheS3BaseUri
$modelPlans = @()
$modelFailures = @()

foreach ($model in @($runtimeRequirements.required_models)) {
  $fileName = [string]$model.filename
  $expectedSha = ([string]$model.sha256).ToLowerInvariant()
  $objectInfoModel = @($objectInfo.required_models | Where-Object { [string]$_.local_path -like "*$fileName" } | Select-Object -First 1)
  $localPath = if ($objectInfoModel.Count -gt 0) { [string]$objectInfoModel[0].local_path } else { "models/checkpoints/$fileName" }
  $modelPath = Resolve-ProjectPath -Path $localPath
  $exists = (![string]::IsNullOrWhiteSpace($modelPath) -and (Test-Path -LiteralPath $modelPath -PathType Leaf))
  $observedSha = if ($objectInfoModel.Count -gt 0) { ([string]$objectInfoModel[0].sha256).ToLowerInvariant() } else { $null }
  $hashMatches = ($exists -and $observedSha -eq $expectedSha -and [bool]$objectInfoModel[0].sha256_match)
  $sourceS3Uri = if ($s3BaseUriValid -and ![string]::IsNullOrWhiteSpace($fileName)) { "$($ModelCacheS3BaseUri.TrimEnd('/'))/$fileName" } else { $null }
  $publishOut = "C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Model_Registry\W66_SELECTED_MODEL_S3_PUBLISH_DRY_RUN_$($fileName)_<timestamp>.json"
  $publishDryRunCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Publish-ModelToS3.ps1 -ModelFile C:\Comfy_UI_Main\$((ConvertTo-ProjectRelativePath -Path $modelPath).Replace('/', '\')) -S3Uri $sourceS3Uri -ExpectedSha256 $expectedSha -Region $Region -OutFile $publishOut"
  $publishExecuteCommand = "$publishDryRunCommand -Execute"
  $installOut = "C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Model_Registry\W66_SELECTED_MODEL_EC2_INSTALL_DRY_RUN_$($fileName)_<timestamp>.json"
  $installDryRunCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Install-EC2ModelFromS3.ps1 -SourceS3Uri $sourceS3Uri -ModelSubdir $([string]$model.comfyui_model_subdir) -ModelFileName $fileName -ExpectedSha256 $expectedSha -Region $Region -OutFile $installOut"
  $installExecuteCommand = "$installDryRunCommand -Execute"

  $modelPlans += [ordered]@{
    role = [string]$model.role
    filename = $fileName
    model_type = [string]$model.model_type
    comfyui_model_subdir = [string]$model.comfyui_model_subdir
    local_model_file = ConvertTo-ProjectRelativePath -Path $modelPath
    local_model_exists = $exists
    expected_sha256 = $expectedSha
    observed_sha256 = $observedSha
    local_hash_match_from_object_info = $hashMatches
    source_s3_uri = $sourceS3Uri
    publish_dry_run_command = $publishDryRunCommand
    publish_execute_command_requires_explicit_user_intent = $publishExecuteCommand
    install_dry_run_command = $installDryRunCommand
    install_execute_command_requires_explicit_user_intent = $installExecuteCommand
  }
  if (-not $exists) { $modelFailures += "missing_local_model:$fileName" }
  if ($exists -and -not $hashMatches) { $modelFailures += "model_hash_not_proven_by_object_info:$fileName" }
}

$blockers = @(
  if (-not [bool]$selectedReadiness.package_readiness_pass) { "selected_package_readiness_not_passed" }
  if (-not [bool]$selectedReadiness.source_git_clean_in_bundle) { "deploy_bundle_source_git_dirty_rebuild_required_before_ec2" }
  if ([bool]$selectedReadiness.explicit_user_selection_required) { "explicit_user_target_runtime_selection_required" }
  if (-not [bool]$selectedReadiness.git_checkpoint_passes_for_ec2) { "git_checkpoint_gate_not_clean_for_ec2_execute" }
  if (-not $s3ReadinessExists) { "s3_runtime_transfer_readiness_not_available" }
  elseif (-not $s3ReadinessReady) { "s3_runtime_transfer_readiness_not_ready" }
  if (-not $s3BaseUriValid) { "approved_model_cache_s3_base_uri_required" }
  if (@($modelFailures).Count -gt 0) { "model_local_source_or_hash_gap" }
  "model_not_yet_published_to_s3_for_selected_lane"
  "ec2_model_install_execute_requires_explicit_intent"
) | Select-Object -Unique

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "selected_model_cache_readiness_plan"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  result = "blocked_selected_model_cache_readiness_waiting_for_s3_publish_and_live_gates"
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
  s3_upload_attempted = $false
  model_install_attempted = $false
  git_lfs_used = $false
  masks_consumed_as_truth = $false
  masks_promoted = $false
  wave70_hard_gate_rerun = $false
  wave71_plus_activated = $false
  full_project_certification_allowed = $false
  selected_lane_id = [string]$selectedReadiness.lane_id
  selected_work_order_id = [string]$selectedReadiness.selected_work_order_id
  selected_package_readiness = ConvertTo-ProjectRelativePath -Path $selectedReadinessResolved
  selected_package_ready_local_only = [bool]$selectedReadiness.package_readiness_pass
  runtime_requirements = ConvertTo-ProjectRelativePath -Path $runtimeRequirementsPath
  local_object_info_evidence = ConvertTo-ProjectRelativePath -Path $objectInfoPath
  required_model_count = @($modelPlans).Count
  model_cache_plans = $modelPlans
  model_local_hash_all_pass_from_object_info = (@($modelPlans | Where-Object { -not [bool]$_.local_hash_match_from_object_info }).Count -eq 0)
  s3_runtime_transfer_readiness = $(if ($s3ReadinessExists) { ConvertTo-ProjectRelativePath -Path $s3ReadinessResolved } else { $null })
  s3_runtime_transfer_readiness_result = $(if ($s3ReadinessExists) { [string]$s3Readiness.result } else { "missing" })
  s3_runtime_transfer_ready_local_only = $s3ReadinessReady
  model_cache_s3_base_uri_present = $s3BaseUriValid
  model_cache_s3_base_uri_source = $(if ($s3BaseUriValid) { if (![string]::IsNullOrWhiteSpace((Get-EnvValue -Map $envMap -Name "S3_MODEL_BUCKET"))) { ".env:S3_MODEL_BUCKET/S3_MODEL_PREFIX" } else { "parameter" } } else { $null })
  region = $Region
  ready_for_model_cache_publish = ($s3ReadinessReady -and $s3BaseUriValid -and @($modelFailures).Count -eq 0)
  ready_for_ec2_model_install_execute = $false
  exact_blockers = $blockers
  required_before_ec2_model_install = @(
    "model uploaded to source_s3_uri value",
    "Publish-ModelToS3.ps1 dry-run plan passes",
    "selected deploy bundle rebuilt or revalidated from clean checkpoint",
    "clean Git checkpoint gate passes for EC2",
    "explicit target-runtime selection exists",
    "S3 runtime transfer readiness remains ready_local_only",
    "Install-EC2ModelFromS3.ps1 dry-run plan passes"
  )
  command_sequence = @(
    [ordered]@{ name = "model_cache_publish_dry_run"; command = "Run publish_dry_run_command from model_cache_plans."; external_contact = $false; mutates_git = $false }
    [ordered]@{ name = "publish_model_to_s3_after_explicit_intent"; command = "Run publish_execute_command_requires_explicit_user_intent only after explicit publish intent and approved AWS auth."; external_contact = $true; mutates_git = $false }
    [ordered]@{ name = "model_install_dry_run"; command = "Run install_dry_run_command from model_cache_plans."; external_contact = $false; mutates_git = $false }
    [ordered]@{ name = "model_install_execute_after_live_gates"; command = "Run install_execute_command_requires_explicit_user_intent only after clean Git, explicit selection, S3 proof, and EC2 static proof gates pass."; external_contact = $true; mutates_git = $false }
    [ordered]@{ name = "target_runtime_workflow_smoke_still_blocked"; command = "Remain blocked until model install hash verification, input asset install hash verification, deploy bundle proof, and EC2 static proof all pass."; external_contact = $false; mutates_git = $false }
  )
  boundary = "Selected model-cache readiness plan only. This artifact does not upload models, contact AWS/S3, start EC2, post prompts, run generation, stage, commit, push, reset, checkout, rebuild deploy bundles, consume or promote masks, rerun Wave70 gates, switch to Jira bookkeeping, or activate Wave71+."
  next_action = "When live gates are later selected and clean, run model publish dry-run, publish the model to the recorded S3 URI after explicit intent, run model install dry-run, then run Install-EC2ModelFromS3.ps1 -Execute before bounded EC2 static proof."
}

[System.IO.Directory]::CreateDirectory((Split-Path -Path $outFileResolved -Parent)) | Out-Null
[System.IO.Directory]::CreateDirectory((Split-Path -Path $markdownResolved -Parent)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 50) + [Environment]::NewLine, $utf8NoBom)

$modelLines = @($modelPlans | ForEach-Object {
  "- $($_.role): $($_.filename), local_hash_match_from_object_info=$($_.local_hash_match_from_object_info), source_s3_uri=$($_.source_s3_uri)"
}) -join [Environment]::NewLine
$markdown = @"
# Selected Model Cache Readiness Plan

- created_at: $($record.created_at)
- result: $($record.result)
- selected_lane_id: $($record.selected_lane_id)
- required_model_count: $($record.required_model_count)
- model_local_hash_all_pass_from_object_info: $($record.model_local_hash_all_pass_from_object_info)
- s3_runtime_transfer_readiness_result: $($record.s3_runtime_transfer_readiness_result)
- model_cache_s3_base_uri_present: $($record.model_cache_s3_base_uri_present)
- ready_for_model_cache_publish: $($record.ready_for_model_cache_publish)
- ready_for_ec2_model_install_execute: $($record.ready_for_ec2_model_install_execute)
- exact_blockers: $(@($record.exact_blockers) -join ", ")

## Models

$modelLines

## Boundary

$($record.boundary)

## Next Action

$($record.next_action)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

Write-Host "Wrote selected model-cache readiness plan: $outFileResolved"
$record | ConvertTo-Json -Depth 50
