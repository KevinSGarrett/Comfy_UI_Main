<#
.SYNOPSIS
Creates a local-only selected-lane EC2 input-asset install readiness plan.

.DESCRIPTION
Reads selected package readiness and S3 runtime-transfer readiness evidence,
then records the required LoadImage/LoadImageMask assets, expected S3 cache
URIs, dry-run/execute commands for Publish-InputAssetToS3.ps1, and dry-run/
execute commands for Install-EC2InputAssetFromS3.ps1. This helper writes
evidence only; it does not upload assets, contact AWS, start EC2, post prompts,
run generation, stage, commit, push, or promote masks.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$SelectedPackageReadinessFile = "",
  [string]$S3RuntimeTransferReadinessFile = "",
  [string]$InputAssetS3BaseUri = "",
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

function Get-AssetSourceFile {
  param(
    [object]$Asset,
    [object]$Manifest
  )
  $role = [string]$Asset.role
  if ($role -eq "source_image" -and $Manifest.source_image -and $Manifest.source_image.path) {
    return [string]$Manifest.source_image.path
  }
  if ($role -eq "mask_image" -and $Manifest.mask_image -and $Manifest.mask_image.path) {
    return [string]$Manifest.mask_image.path
  }
  if ($Asset.source_path) { return [string]$Asset.source_path }
  return $null
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
  $OutFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_SELECTED_INPUT_ASSET_INSTALL_READINESS_PLAN_$stamp.json"
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
if ([string]::IsNullOrWhiteSpace($InputAssetS3BaseUri)) {
  $bucket = Get-EnvValue -Map $envMap -Name "S3_MODEL_BUCKET"
  $prefix = (Get-EnvValue -Map $envMap -Name "S3_MODEL_PREFIX").Trim("/")
  if (![string]::IsNullOrWhiteSpace($bucket) -and ![string]::IsNullOrWhiteSpace($prefix)) {
    $InputAssetS3BaseUri = "s3://$bucket/$prefix/input-assets"
  }
}

$runtimeRequirementsPath = Resolve-ProjectPath -Path $selectedReadiness.runtime_requirements
if ([string]::IsNullOrWhiteSpace($runtimeRequirementsPath) -or -not (Test-Path -LiteralPath $runtimeRequirementsPath -PathType Leaf)) {
  throw "Runtime requirements file missing from selected package readiness."
}
$runtimeRequirements = Read-JsonFile -Path $runtimeRequirementsPath

$s3ReadinessReady = ($s3ReadinessExists -and [string]$s3Readiness.result -eq "ready_local_only")
$s3BaseUriValid = Test-S3BaseUriShape -Uri $InputAssetS3BaseUri
$assetPlans = @()
$assetFailures = @()

foreach ($asset in @($runtimeRequirements.required_input_assets)) {
  $manifestPath = Resolve-ProjectPath -Path $asset.source_manifest
  $manifestExists = (![string]::IsNullOrWhiteSpace($manifestPath) -and (Test-Path -LiteralPath $manifestPath -PathType Leaf))
  $manifest = if ($manifestExists) { Read-JsonFile -Path $manifestPath } else { $null }
  $sourcePathText = if ($manifestExists) { Get-AssetSourceFile -Asset $asset -Manifest $manifest } else { $null }
  $sourcePath = Resolve-ProjectPath -Path $sourcePathText
  $sourceExists = (![string]::IsNullOrWhiteSpace($sourcePath) -and (Test-Path -LiteralPath $sourcePath -PathType Leaf))
  $expectedSha = ([string]$asset.sha256).ToLowerInvariant()
  $observedSha = $null
  $hashMatches = $false
  if ($sourceExists) {
    $observedSha = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath).Hash.ToLowerInvariant()
    $hashMatches = ($observedSha -eq $expectedSha)
  }
  $fileName = [string]$asset.filename
  if ([string]::IsNullOrWhiteSpace($fileName) -and $sourceExists) {
    $fileName = Split-Path -Leaf $sourcePath
  }
  $sourceS3Uri = if ($s3BaseUriValid -and ![string]::IsNullOrWhiteSpace($fileName)) { "$($InputAssetS3BaseUri.TrimEnd('/'))/$fileName" } else { $null }
  $publishDryRunOut = "C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_SELECTED_INPUT_ASSET_S3_PUBLISH_DRY_RUN_$($fileName)_<timestamp>.json"
  $publishDryRunCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Publish-InputAssetToS3.ps1 -AssetFile C:\Comfy_UI_Main\$((ConvertTo-ProjectRelativePath -Path $sourcePath).Replace('/', '\')) -S3Uri $sourceS3Uri -ExpectedSha256 $expectedSha -Region $Region -OutFile $publishDryRunOut"
  $publishExecuteCommand = "$publishDryRunCommand -Execute"
  $dryRunOut = "C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_SELECTED_INPUT_ASSET_INSTALL_DRY_RUN_$($fileName)_<timestamp>.json"
  $dryRunCommand = "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Install-EC2InputAssetFromS3.ps1 -SourceS3Uri $sourceS3Uri -FileName $fileName -ExpectedSha256 $expectedSha -Region $Region -OutFile $dryRunOut"
  $executeCommand = "$dryRunCommand -Execute"

  $plan = [ordered]@{
    role = [string]$asset.role
    filename = $fileName
    expected_sha256 = $expectedSha
    source_manifest = ConvertTo-ProjectRelativePath -Path $manifestPath
    source_file = ConvertTo-ProjectRelativePath -Path $sourcePath
    source_file_exists = $sourceExists
    observed_sha256 = $observedSha
    local_hash_match = $hashMatches
    comfyui_input_path = [string]$asset.comfyui_input_path
    source_s3_uri = $sourceS3Uri
    s3_source_uri_ready_after_asset_publish = $s3BaseUriValid
    publish_dry_run_command = $publishDryRunCommand
    publish_execute_command_requires_explicit_user_intent = $publishExecuteCommand
    install_dry_run_command = $dryRunCommand
    install_execute_command_requires_explicit_user_intent = $executeCommand
  }
  $assetPlans += $plan
  if (-not $manifestExists) { $assetFailures += "missing_source_manifest:$([string]$asset.role)" }
  if (-not $sourceExists) { $assetFailures += "missing_source_file:$([string]$asset.role)" }
  if ($sourceExists -and -not $hashMatches) { $assetFailures += "source_hash_mismatch:$([string]$asset.role)" }
}

$blockers = @(
  if (-not [bool]$selectedReadiness.package_readiness_pass) { "selected_package_readiness_not_passed" }
  if (-not [bool]$selectedReadiness.source_git_clean_in_bundle) { "deploy_bundle_source_git_dirty_rebuild_required_before_ec2" }
  if ([bool]$selectedReadiness.explicit_user_selection_required) { "explicit_user_target_runtime_selection_required" }
  if (-not [bool]$selectedReadiness.git_checkpoint_passes_for_ec2) { "git_checkpoint_gate_not_clean_for_ec2_execute" }
  if (-not $s3ReadinessExists) { "s3_runtime_transfer_readiness_not_available" }
  elseif (-not $s3ReadinessReady) { "s3_runtime_transfer_readiness_not_ready" }
  if (-not $s3BaseUriValid) { "approved_input_asset_s3_base_uri_required" }
  if (@($assetFailures).Count -gt 0) { "input_asset_local_source_or_hash_gap" }
  "input_assets_not_yet_published_to_s3_for_selected_lane"
  "ec2_input_asset_install_execute_requires_explicit_intent"
) | Select-Object -Unique

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "selected_input_asset_install_readiness_plan"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  result = "blocked_selected_input_asset_install_readiness_waiting_for_s3_publish_and_live_gates"
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
  input_asset_install_attempted = $false
  masks_consumed_as_truth = $false
  masks_promoted = $false
  wave70_hard_gate_rerun = $false
  wave71_plus_activated = $false
  full_project_certification_allowed = $false
  selected_lane_id = [string]$selectedReadiness.lane_id
  selected_work_order_id = [string]$selectedReadiness.selected_work_order_id
  selected_package_readiness = ConvertTo-ProjectRelativePath -Path $selectedReadinessResolved
  selected_package_readiness_result = [string]$selectedReadiness.result
  selected_package_ready_local_only = [bool]$selectedReadiness.package_readiness_pass
  selected_package_git_checkpoint_passes_for_ec2 = [bool]$selectedReadiness.git_checkpoint_passes_for_ec2
  runtime_requirements = ConvertTo-ProjectRelativePath -Path $runtimeRequirementsPath
  required_input_asset_count = @($assetPlans).Count
  input_asset_plans = $assetPlans
  input_asset_local_hash_all_pass = (@($assetPlans | Where-Object { -not [bool]$_.local_hash_match }).Count -eq 0)
  s3_runtime_transfer_readiness = $(if ($s3ReadinessExists) { ConvertTo-ProjectRelativePath -Path $s3ReadinessResolved } else { $null })
  s3_runtime_transfer_readiness_result = $(if ($s3ReadinessExists) { [string]$s3Readiness.result } else { "missing" })
  s3_runtime_transfer_ready_local_only = $s3ReadinessReady
  input_asset_s3_base_uri_present = $s3BaseUriValid
  input_asset_s3_base_uri_source = $(if ($s3BaseUriValid) { if (![string]::IsNullOrWhiteSpace((Get-EnvValue -Map $envMap -Name "S3_MODEL_BUCKET"))) { ".env:S3_MODEL_BUCKET/S3_MODEL_PREFIX/input-assets" } else { "parameter" } } else { $null })
  region = $Region
  ready_for_input_asset_publish = ($s3ReadinessReady -and $s3BaseUriValid -and @($assetFailures).Count -eq 0)
  ready_for_ec2_input_asset_install_execute = $false
  exact_blockers = $blockers
  required_before_ec2_input_install = @(
    "input assets uploaded to source_s3_uri values",
    "Publish-InputAssetToS3.ps1 dry-run plans pass for each asset",
    "selected deploy bundle rebuilt or revalidated from clean checkpoint",
    "clean Git checkpoint gate passes for EC2",
    "explicit target-runtime selection exists",
    "S3 runtime transfer readiness remains ready_local_only",
    "Install-EC2InputAssetFromS3.ps1 dry-run plans pass for each asset"
  )
  command_sequence = @(
    [ordered]@{ name = "input_asset_publish_dry_runs"; command = "Run each publish_dry_run_command from input_asset_plans."; external_contact = $false; mutates_git = $false }
    [ordered]@{ name = "publish_input_assets_to_s3_after_explicit_intent"; command = "Run each publish_execute_command_requires_explicit_user_intent only after explicit publish intent and approved AWS auth."; external_contact = $true; mutates_git = $false }
    [ordered]@{ name = "input_asset_install_dry_runs"; command = "Run each install_dry_run_command from input_asset_plans."; external_contact = $false; mutates_git = $false }
    [ordered]@{ name = "input_asset_install_execute_after_live_gates"; command = "Run each install_execute_command_requires_explicit_user_intent only after clean Git, explicit selection, S3 proof, and EC2 static proof gates pass."; external_contact = $true; mutates_git = $false }
    [ordered]@{ name = "target_runtime_workflow_smoke_still_blocked"; command = "Remain blocked until input asset install hash verification, model path/hash proof, deploy bundle proof, and EC2 static proof all pass."; external_contact = $false; mutates_git = $false }
  )
  boundary = "Selected input-asset install readiness plan only. This artifact does not upload assets, contact AWS/S3, start EC2, post prompts, run generation, stage, commit, push, reset, checkout, rebuild deploy bundles, consume or promote masks, rerun Wave70 gates, switch to Jira bookkeeping, or activate Wave71+."
  next_action = "When live gates are later selected and clean, run publish dry-runs for the listed source/mask assets, publish them to the recorded S3 URIs after explicit intent, run dry-run install plans, then run Install-EC2InputAssetFromS3.ps1 -Execute for each asset before bounded workflow smoke."
}

[System.IO.Directory]::CreateDirectory((Split-Path -Path $outFileResolved -Parent)) | Out-Null
[System.IO.Directory]::CreateDirectory((Split-Path -Path $markdownResolved -Parent)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 50) + [Environment]::NewLine, $utf8NoBom)

$assetLines = @($assetPlans | ForEach-Object {
  "- $($_.role): $($_.filename), local_hash_match=$($_.local_hash_match), source_s3_uri=$($_.source_s3_uri)"
}) -join [Environment]::NewLine
$markdown = @"
# Selected Input Asset Install Readiness Plan

- created_at: $($record.created_at)
- result: $($record.result)
- selected_lane_id: $($record.selected_lane_id)
- required_input_asset_count: $($record.required_input_asset_count)
- input_asset_local_hash_all_pass: $($record.input_asset_local_hash_all_pass)
- s3_runtime_transfer_readiness_result: $($record.s3_runtime_transfer_readiness_result)
- input_asset_s3_base_uri_present: $($record.input_asset_s3_base_uri_present)
- ready_for_input_asset_publish: $($record.ready_for_input_asset_publish)
- ready_for_ec2_input_asset_install_execute: $($record.ready_for_ec2_input_asset_install_execute)
- exact_blockers: $(@($record.exact_blockers) -join ", ")

## Assets

$assetLines

## Boundary

$($record.boundary)

## Next Action

$($record.next_action)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

Write-Host "Wrote selected input-asset install readiness plan: $outFileResolved"
$record | ConvertTo-Json -Depth 50
