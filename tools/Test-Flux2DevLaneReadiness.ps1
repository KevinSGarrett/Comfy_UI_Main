<#
.SYNOPSIS
Validates the local Flux2 Dev lane contract without launching ComfyUI or contacting external services.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$ConfigPath = "",
  [string]$AssetManifestPath = "",
  [string]$WorkflowRoot = "",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Write-JsonNoBom {
  param([object]$Value, [string]$Path, [int]$Depth = 24)
  $parent = Split-Path -Parent $Path
  if (-not [string]::IsNullOrWhiteSpace($parent)) { [System.IO.Directory]::CreateDirectory($parent) | Out-Null }
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth) + [Environment]::NewLine, $encoding)
}

function Add-Check {
  param([System.Collections.ArrayList]$Checks, [string]$Name, [bool]$Passed, [object]$Observed = $null, [string]$Message = "")
  [void]$Checks.Add([ordered]@{ name = $Name; passed = $Passed; result = $(if ($Passed) { "pass" } else { "fail" }); observed = $Observed; message = $Message })
}

function Get-PropertyValue {
  param([AllowNull()][object]$Object, [string]$Name)
  if ($null -eq $Object -or $null -eq $Object.PSObject.Properties[$Name]) { return $null }
  return $Object.$Name
}

function Read-JsonSafe {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
  try { return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json } catch { return $null }
}

function Read-EnvFile {
  param([string]$Path)
  $values = @{}
  if (Test-Path -LiteralPath $Path -PathType Leaf) {
    foreach ($line in Get-Content -LiteralPath $Path) {
      if ($line -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
        $values[$matches[1]] = $matches[2].Trim().Trim('"').Trim("'")
      }
    }
  }
  return $values
}

function Resolve-ConfiguredPath {
  param([string]$Path, [string]$Base)
  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  if ([System.IO.Path]::IsPathRooted($Path)) { return [System.IO.Path]::GetFullPath($Path) }
  return [System.IO.Path]::GetFullPath((Join-Path $Base $Path))
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) { throw "Project root not found: $ProjectRoot" }
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
if ([string]::IsNullOrWhiteSpace($ConfigPath)) { $ConfigPath = Join-Path $ProjectRoot "Plan\07_IMPLEMENTATION\templates\repo\.env.example" }
if ([string]::IsNullOrWhiteSpace($AssetManifestPath)) { $AssetManifestPath = Join-Path $ProjectRoot "models\flux2\dev\manifests\flux2_dev_asset_manifest.json" }
if ([string]::IsNullOrWhiteSpace($WorkflowRoot)) { $WorkflowRoot = Join-Path $ProjectRoot "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\flux2_dev_primary_base" }
$ConfigPath = Resolve-ConfiguredPath -Path $ConfigPath -Base $ProjectRoot
$AssetManifestPath = Resolve-ConfiguredPath -Path $AssetManifestPath -Base $ProjectRoot
$WorkflowRoot = Resolve-ConfiguredPath -Path $WorkflowRoot -Base $ProjectRoot

$checks = New-Object System.Collections.ArrayList
$config = Read-EnvFile -Path $ConfigPath
$manifest = Read-JsonSafe -Path $AssetManifestPath
$engineRegistry = Read-JsonSafe -Path (Join-Path $ProjectRoot "Plan\10_REGISTRIES\wave06_engine_registry.json")
$laneRegistry = Read-JsonSafe -Path (Join-Path $ProjectRoot "Plan\10_REGISTRIES\wave15_image_base_lane_registry.json")
$requirements = Read-JsonSafe -Path (Join-Path $ProjectRoot "Plan\10_REGISTRIES\wave06_flux2_integration_requirements.json")

$engine = @($engineRegistry | Where-Object { [string]$_.engine_id -eq "flux2_dev_local" } | Select-Object -First 1)
$lane = @($laneRegistry | Where-Object { [string]$_.lane_id -eq "flux2_dev_primary_base" } | Select-Object -First 1)
Add-Check $checks "authoritative_flux2_contracts_parse" ($null -ne $requirements -and $engine.Count -eq 1 -and $lane.Count -eq 1)
Add-Check $checks "promotion_remains_fail_closed" ($engine.Count -eq 1 -and [string]$engine[0].promotion_status -eq "blocked_until_runtime_proof" -and $lane.Count -eq 1 -and [string]$lane[0].promotion_state -eq "not_promoted")

$enabled = $config.ContainsKey("FLUX2_ENABLED") -and [string]$config["FLUX2_ENABLED"] -match '^(?i:true)$'
$configKeys = @("FLUX2_DEV_MODEL_FILENAME", "FLUX2_DEV_MODEL_SHA256", "FLUX2_TEXT_ENCODER_FILENAME", "FLUX2_TEXT_ENCODER_SHA256", "FLUX2_VAE_FILENAME", "FLUX2_VAE_SHA256", "FLUX2_MIN_COMFYUI_VERSION")
$missingConfig = @($configKeys | Where-Object { -not $config.ContainsKey($_) -or [string]::IsNullOrWhiteSpace([string]$config[$_]) })
$invalidConfigHashes = @("FLUX2_DEV_MODEL_SHA256", "FLUX2_TEXT_ENCODER_SHA256", "FLUX2_VAE_SHA256" | Where-Object { $config.ContainsKey($_) -and [string]$config[$_] -notmatch '^[0-9a-fA-F]{64}$' })
Add-Check $checks "flux2_enabled" $enabled $config["FLUX2_ENABLED"] "Flux2 must remain disabled until all readiness checks pass and promotion is separately approved."
Add-Check $checks "exact_asset_config_complete" ($missingConfig.Count -eq 0) $missingConfig
Add-Check $checks "asset_config_hashes_valid" ($missingConfig.Count -eq 0 -and $invalidConfigHashes.Count -eq 0) $invalidConfigHashes

$assetRoles = @(
  [ordered]@{ role = "diffusion_model"; filename_key = "FLUX2_DEV_MODEL_FILENAME"; hash_key = "FLUX2_DEV_MODEL_SHA256" },
  [ordered]@{ role = "text_encoder"; filename_key = "FLUX2_TEXT_ENCODER_FILENAME"; hash_key = "FLUX2_TEXT_ENCODER_SHA256" },
  [ordered]@{ role = "vae"; filename_key = "FLUX2_VAE_FILENAME"; hash_key = "FLUX2_VAE_SHA256" }
)
$assetResults = @()
foreach ($spec in $assetRoles) {
  $entry = @(@(Get-PropertyValue $manifest "assets") | Where-Object { [string]$_.role -eq $spec.role } | Select-Object -First 1)
  $filename = if ($config.ContainsKey($spec.filename_key)) { [string]$config[$spec.filename_key] } else { "" }
  $expectedHash = if ($config.ContainsKey($spec.hash_key)) { ([string]$config[$spec.hash_key]).ToLowerInvariant() } else { "" }
  $entryValid = $entry.Count -eq 1 -and -not [string]::IsNullOrWhiteSpace([string]$entry[0].source_url) -and -not [string]::IsNullOrWhiteSpace([string]$entry[0].license_or_access_notes) -and [string]$entry[0].filename -eq $filename -and ([string]$entry[0].sha256).ToLowerInvariant() -eq $expectedHash -and $expectedHash -match '^[0-9a-f]{64}$'
  $resolvedAssetPath = if ($entry.Count -eq 1) { Resolve-ConfiguredPath -Path ([string]$entry[0].local_cache_path) -Base $ProjectRoot } else { $null }
  $exists = $entryValid -and -not [string]::IsNullOrWhiteSpace($resolvedAssetPath) -and (Test-Path -LiteralPath $resolvedAssetPath -PathType Leaf)
  $observedHash = if ($exists) { (Get-FileHash -LiteralPath $resolvedAssetPath -Algorithm SHA256).Hash.ToLowerInvariant() } else { "" }
  $assetResults += [ordered]@{ role = $spec.role; manifest_entry_valid = $entryValid; path = $resolvedAssetPath; exists = $exists; expected_sha256 = $expectedHash; observed_sha256 = $observedHash; hash_match = ($exists -and $observedHash -eq $expectedHash) }
}
Add-Check $checks "asset_manifest_parses" ($null -ne $manifest) $AssetManifestPath
Add-Check $checks "all_asset_manifest_entries_complete" (@($assetResults | Where-Object { -not $_.manifest_entry_valid }).Count -eq 0) $assetResults
Add-Check $checks "all_asset_files_present" (@($assetResults | Where-Object { -not $_.exists }).Count -eq 0) $assetResults
Add-Check $checks "all_asset_hashes_match" (@($assetResults | Where-Object { -not $_.hash_match }).Count -eq 0) $assetResults

$nodeClasses = @(Get-PropertyValue $manifest "required_node_classes")
$runtimeContractValid = $null -ne $manifest -and [string](Get-PropertyValue $manifest "required_comfyui_version") -eq [string]$config["FLUX2_MIN_COMFYUI_VERSION"] -and $nodeClasses.Count -gt 0 -and @($nodeClasses | Where-Object { [string]::IsNullOrWhiteSpace([string]$_) }).Count -eq 0
Add-Check $checks "runtime_contract_complete" $runtimeContractValid ([ordered]@{ required_comfyui_version = Get-PropertyValue $manifest "required_comfyui_version"; required_node_classes = $nodeClasses })

$proofFiles = [ordered]@{
  workflow_api = Join-Path $WorkflowRoot "workflow.api.json"
  smoke_request = Join-Path $WorkflowRoot "smoke_request.json"
  object_info_proof = Join-Path $WorkflowRoot "object_info_proof.json"
  smoke_output_proof = Join-Path $WorkflowRoot "smoke_output_proof.json"
}
foreach ($proofName in @($proofFiles.Keys)) {
  $proof = Read-JsonSafe -Path $proofFiles[$proofName]
  $proofPassed = $null -ne $proof -and [string](Get-PropertyValue $proof "result") -match '^pass'
  Add-Check $checks "$($proofName)_present_and_passed" $proofPassed $proofFiles[$proofName]
}

$failed = @($checks | Where-Object { -not $_.passed })
$ready = $failed.Count -eq 0
$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "flux2_dev_lane_local_readiness"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  result = $(if ($ready) { "pass_local_flux2_dev_candidate" } else { "blocked_flux2_dev_prerequisites_missing" })
  classification = $(if ($ready) { "FLUX2_DEV_LOCAL_READINESS_CANDIDATE" } else { "BLOCKED_FLUX2_DEV_ASSET_OR_RUNTIME_PROOF_MISSING" })
  lane_id = "flux2_dev_primary_base"
  engine_id = "flux2_dev_local"
  local_only = $true
  aws_contacted = $false
  s3_contacted = $false
  github_api_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  mask_consumed_as_truth = $false
  target_runtime_proof = $false
  certification_claimed = $false
  promotion_claimed = $false
  config_path = $ConfigPath
  asset_manifest_path = $AssetManifestPath
  workflow_root = $WorkflowRoot
  asset_results = $assetResults
  check_count = $checks.Count
  failed_check_count = $failed.Count
  failed_check_names = @($failed | ForEach-Object { $_.name })
  checks = @($checks)
  next_action = $(if ($ready) { "Run a separately authorized local or EC2 ComfyUI proof; this static candidate does not promote the lane." } else { "Obtain authoritative licensed Flux2 Dev asset identities, hashes, sources, and compatible ComfyUI requirements; then install and produce the missing API/object_info/smoke proofs without promoting from documentation alone." })
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_FLUX2_DEV_LOCAL_READINESS_$stamp.json"
} else { $OutFile = Resolve-ConfiguredPath -Path $OutFile -Base $ProjectRoot }
Write-JsonNoBom -Value $record -Path $OutFile
$record | ConvertTo-Json -Depth 24
exit 0
