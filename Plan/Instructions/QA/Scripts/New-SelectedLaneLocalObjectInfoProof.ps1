<#
.SYNOPSIS
Creates local-only object_info and hash proof for the selected inpaint target lane.

.DESCRIPTION
Queries a local ComfyUI /object_info endpoint, verifies the selected lane's
required nodes, and hashes the configured local checkpoint plus prepared source
and mask input assets. This helper does not post /prompt, does not execute
generation, does not contact AWS/S3/GitHub/Civitai, and does not start EC2.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$RuntimeRequirementsFile = "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\sdxl_realvisxl_inpaint_detail_lane\runtime_requirements.json",
  [string]$InputAssetManifestFile = "Plan\Instructions\Operations\Prepared_Input_Assets\sdxl_inpaint_detail_micro_nomouth_v4_20260707T034500-0500\INPAINT_MICRO_NOMOUTH_INPUT_ASSET_MANIFEST.json",
  [string]$LocalComfyRoot = "C:\Comfy_UI_Main\ComfyUI",
  [string]$ComfyModelRoot = "C:\Comfy_UI_Main",
  [string]$ExtraModelPathsConfig = "config\comfyui_extra_model_paths.yaml",
  [string]$HostAddress = "127.0.0.1",
  [int]$Port = 8188,
  [int]$ObjectInfoTimeoutSeconds = 20,
  [string]$OutFile = ""
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

function Convert-ToArray {
  param([AllowNull()][object]$Value)
  if ($null -eq $Value) { return @() }
  if ($Value -is [array]) { return @($Value) }
  return @($Value)
}

function Get-FileSha256Lower {
  param([AllowNull()][string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path) -or -not (Test-Path -LiteralPath $Path -PathType Leaf)) { return "" }
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function New-HashProof {
  param(
    [Parameter(Mandatory = $true)][string]$Role,
    [Parameter(Mandatory = $true)][string]$Path,
    [Parameter(Mandatory = $true)][string]$ExpectedSha256
  )
  $resolved = Resolve-ProjectPath -Path $Path
  $exists = (![string]::IsNullOrWhiteSpace($resolved) -and (Test-Path -LiteralPath $resolved -PathType Leaf))
  $actual = $(if ($exists) { Get-FileSha256Lower -Path $resolved } else { "" })
  $bytes = $(if ($exists) { (Get-Item -LiteralPath $resolved).Length } else { 0 })
  return [ordered]@{
    role = $Role
    local_path = ConvertTo-ProjectRelativePath -Path $resolved
    exists = $exists
    bytes = $bytes
    expected_sha256 = $ExpectedSha256
    sha256 = $actual
    sha256_match = ($exists -and $actual -eq $ExpectedSha256.ToLowerInvariant())
  }
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_LOCAL_OBJECT_INFO_INPAINT_DETAIL_MASKTOIMAGE_REFRESH_$stamp.json"
}

$runtimeRequirementsResolved = Resolve-ProjectPath -Path $RuntimeRequirementsFile
$inputAssetResolved = Resolve-ProjectPath -Path $InputAssetManifestFile
if (-not (Test-Path -LiteralPath $runtimeRequirementsResolved -PathType Leaf)) {
  throw "Runtime requirements file not found: $runtimeRequirementsResolved"
}
if (-not (Test-Path -LiteralPath $inputAssetResolved -PathType Leaf)) {
  throw "Input asset manifest file not found: $inputAssetResolved"
}

$runtimeRequirements = Read-JsonFile -Path $runtimeRequirementsResolved
$inputAsset = Read-JsonFile -Path $inputAssetResolved
$apiBaseUrl = "http://$HostAddress`:$Port"
$errors = @()
$objectInfoStatus = "not_started"
$nodeNames = @()

try {
  $objectInfoPayload = Invoke-RestMethod -Method Get -Uri "$apiBaseUrl/object_info" -TimeoutSec $ObjectInfoTimeoutSeconds
  $nodeNames = @($objectInfoPayload.PSObject.Properties.Name | ForEach-Object { [string]$_ })
} catch {
  $errors += "Local ComfyUI /object_info query failed: $($_.Exception.Message)"
}

$requiredNodes = @(Convert-ToArray -Value $runtimeRequirements.required_nodes | ForEach-Object { [string]$_ })
$presentNodes = @($requiredNodes | Where-Object { $nodeNames -contains $_ })
$missingNodes = @($requiredNodes | Where-Object { $nodeNames -notcontains $_ })
$objectInfoStatus = $(if ($errors.Count -eq 0 -and $missingNodes.Count -eq 0) { "pass" } elseif ($errors.Count -eq 0) { "fail" } else { "not_available" })

$modelProofs = @()
foreach ($model in @(Convert-ToArray -Value $runtimeRequirements.required_models)) {
  $modelPath = Join-Path -Path $ComfyModelRoot -ChildPath ("models\" + [string]$model.comfyui_model_subdir + "\" + [string]$model.filename)
  $modelProofs += New-HashProof -Role ([string]$model.role) -Path $modelPath -ExpectedSha256 ([string]$model.sha256)
}

$inputProofs = @()
foreach ($asset in @(Convert-ToArray -Value $runtimeRequirements.required_input_assets)) {
  $role = [string]$asset.role
  $manifestAsset = if ($role -eq "source_image") { $inputAsset.source_image } elseif ($role -eq "mask_image") { $inputAsset.mask_image } else { $null }
  $assetPath = if ($null -ne $manifestAsset -and $manifestAsset.copied_to_local_comfy_input) {
    [string]$manifestAsset.copied_to_local_comfy_input
  } else {
    [string]$asset.comfyui_input_path
  }
  $expected = if ($null -ne $manifestAsset -and $manifestAsset.sha256) { [string]$manifestAsset.sha256 } else { [string]$asset.sha256 }
  $inputProofs += New-HashProof -Role $role -Path $assetPath -ExpectedSha256 $expected
}

$hashFailures = @(
  @($modelProofs | Where-Object { -not [bool]$_.sha256_match })
  @($inputProofs | Where-Object { -not [bool]$_.sha256_match })
)
if ($missingNodes.Count -gt 0) {
  $errors += "Local ComfyUI is missing required nodes: $($missingNodes -join ', ')"
}
if ($hashFailures.Count -gt 0) {
  $errors += "Local model/input hash proof failed for: $(@($hashFailures | ForEach-Object { [string]$_.role }) -join ', ')"
}

$pythonPath = Join-Path -Path $LocalComfyRoot -ChildPath ".venv\Scripts\python.exe"
$record = [ordered]@{
  schema_version = "1.0"
  evidence_id = "W66-LOCAL-OBJECT-INFO-INPAINT-DETAIL-MASKTOIMAGE-REFRESH-$stamp"
  timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  project_root = $ProjectRoot
  lane_id = [string]$runtimeRequirements.lane_id
  module_id = [string]$runtimeRequirements.module_id
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  s3_contacted = $false
  ec2_started = $false
  generation_executed = $false
  prompt_posted = $false
  comfyui_contacted = ($nodeNames.Count -gt 0)
  local_comfy = [ordered]@{
    root = $LocalComfyRoot
    python = $(if (Test-Path -LiteralPath $pythonPath -PathType Leaf) { $pythonPath } else { $null })
    extra_model_paths_config = ConvertTo-ProjectRelativePath -Path $ExtraModelPathsConfig
    port = $Port
    started_by_probe = $false
    stopped_by_probe = $false
    port_closed_after_stop = $false
    preexisting_listener_used = $true
  }
  object_info = [ordered]@{
    status = $objectInfoStatus
    node_count = $nodeNames.Count
    required_nodes_present = $presentNodes
    missing_required_nodes = $missingNodes
  }
  required_models = $modelProofs
  required_input_assets = $inputProofs
  result = $(if ($errors.Count -eq 0) { "pass_local_object_info_model_input_hash_proof" } else { "fail_local_object_info_model_input_hash_proof" })
  errors = $errors
  masks_consumed_as_truth = $false
  masks_promoted = $false
  wave70_hard_gate_rerun = $false
  wave71_plus_activated = $false
  does_not_replace_target_runtime_proof = $true
  next_action = "Use as local selected-lane readiness proof only; target-runtime object_info/path/hash/input proof, bounded target-runtime generation, pullback, technical QA, and strict whole-image visual QA remain required before promotion."
}

$outFileResolved = Resolve-ProjectPath -Path $OutFile
[System.IO.Directory]::CreateDirectory((Split-Path -Path $outFileResolved -Parent)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 30) + [Environment]::NewLine, $utf8NoBom)

$record | ConvertTo-Json -Depth 30
if ($record.result -ne "pass_local_object_info_model_input_hash_proof") { exit 2 }
exit 0
