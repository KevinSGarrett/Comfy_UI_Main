<#
.SYNOPSIS
Validates a selected ControlNet lane package and deploy bundle as a local-only contract.

.DESCRIPTION
Composes Test-RunPackageDeployBundleConsistency.ps1 for generic package and
bundle integrity, then checks the selected ControlNet model, control-map input,
smoke-request bindings, and packaged contract hashes. No external service is
contacted and no target-runtime or certification claim is made.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [Parameter(Mandatory=$true)][string]$LaneId,
  [Parameter(Mandatory=$true)][string]$RunPackageManifestFile,
  [Parameter(Mandatory=$true)][string]$DeployBundleManifestFile,
  [Parameter(Mandatory=$true)][string]$RuntimeRequirementsFile,
  [Parameter(Mandatory=$true)][string]$SmokeTestRequestFile,
  [string]$OutFile = "",
  [switch]$Strict
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectPath {
  param([Parameter(Mandatory=$true)][string]$Path)
  if ([System.IO.Path]::IsPathRooted($Path)) {
    return [System.IO.Path]::GetFullPath($Path)
  }
  return [System.IO.Path]::GetFullPath((Join-Path -Path $ProjectRoot -ChildPath $Path))
}

function ConvertTo-ProjectRelativePath {
  param([Parameter(Mandatory=$true)][string]$Path)
  $root = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/") + [System.IO.Path]::DirectorySeparatorChar
  $resolved = [System.IO.Path]::GetFullPath($Path)
  if ($resolved.StartsWith($root, [System.StringComparison]::OrdinalIgnoreCase)) {
    return $resolved.Substring($root.Length).Replace("\", "/")
  }
  return $resolved
}

function Get-Sha256 {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return "" }
  return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Read-JsonIfPresent {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return $null }
  try {
    return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
  } catch {
    return $null
  }
}

function New-Check {
  param([string]$Name, [bool]$Passed, [object]$Observed, [object]$Expected, [string]$FailureCategory)
  return [pscustomobject][ordered]@{
    name = $Name
    result = $(if ($Passed) { "pass" } else { "fail" })
    observed = $Observed
    expected = $Expected
    failure_category = $(if ($Passed) { $null } else { $FailureCategory })
  }
}

function Test-HashContract {
  param([object]$Row)
  return (
    $null -ne $Row -and
    -not [string]::IsNullOrWhiteSpace([string]$Row.filename) -and
    [string]$Row.sha256 -match '^[0-9a-fA-F]{64}$' -and
    -not [string]::IsNullOrWhiteSpace([string]$Row.node_id) -and
    -not [string]::IsNullOrWhiteSpace([string]$Row.input)
  )
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
Set-Location -LiteralPath $ProjectRoot

$laneMapTypes = [ordered]@{
  sdxl_realvisxl_controlnet_depth_lane = "depth"
  sdxl_realvisxl_controlnet_lineart_lane = "lineart"
  sdxl_realvisxl_controlnet_openpose_lane = "openpose"
  sdxl_realvisxl_controlnet_normal_lane = "normal"
}
$supportedLane = $laneMapTypes.Contains($LaneId)
$expectedMapType = if ($supportedLane) { [string]$laneMapTypes[$LaneId] } else { "" }

$runPath = Resolve-ProjectPath -Path $RunPackageManifestFile
$deployPath = Resolve-ProjectPath -Path $DeployBundleManifestFile
$requirementsPath = Resolve-ProjectPath -Path $RuntimeRequirementsFile
$smokePath = Resolve-ProjectPath -Path $SmokeTestRequestFile
$inputPaths = @($runPath, $deployPath, $requirementsPath, $smokePath)
$missingFiles = @($inputPaths | Where-Object { -not (Test-Path -LiteralPath $_ -PathType Leaf) })

$run = Read-JsonIfPresent -Path $runPath
$deploy = Read-JsonIfPresent -Path $deployPath
$requirements = Read-JsonIfPresent -Path $requirementsPath
$smoke = Read-JsonIfPresent -Path $smokePath
$checks = [System.Collections.Generic.List[object]]::new()
$warnings = [System.Collections.Generic.List[string]]::new()

[void]$checks.Add((New-Check -Name "supported_controlnet_lane" -Passed $supportedLane -Observed $LaneId -Expected @($laneMapTypes.Keys) -FailureCategory "unsupported_controlnet_lane"))
[void]$checks.Add((New-Check -Name "required_input_files" -Passed ($missingFiles.Count -eq 0) -Observed @($missingFiles | ForEach-Object { ConvertTo-ProjectRelativePath -Path $_ }) -Expected "all required JSON inputs exist" -FailureCategory "required_input_missing"))
[void]$checks.Add((New-Check -Name "required_input_json" -Passed ($null -ne $run -and $null -ne $deploy -and $null -ne $requirements -and $null -ne $smoke) -Observed ([ordered]@{
  run_manifest_parsed = $null -ne $run
  deploy_manifest_parsed = $null -ne $deploy
  runtime_requirements_parsed = $null -ne $requirements
  smoke_request_parsed = $null -ne $smoke
}) -Expected "all required JSON inputs parse" -FailureCategory "required_input_json_invalid"))

$genericScript = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-RunPackageDeployBundleConsistency.ps1"
$genericOut = Join-Path $env:TEMP ("controlnet_package_deploy_generic_{0}.json" -f ([guid]::NewGuid().ToString("N")))
$generic = $null
$genericExitCode = -1
if ($supportedLane -and $missingFiles.Count -eq 0 -and $null -ne $run -and $null -ne $deploy -and (Test-Path -LiteralPath $genericScript -PathType Leaf)) {
  & powershell -NoProfile -ExecutionPolicy Bypass -File $genericScript `
    -ProjectRoot $ProjectRoot `
    -RunPackageManifestFile $runPath `
    -DeployBundleManifestFile $deployPath `
    -OutFile $genericOut *> $null
  $genericExitCode = $LASTEXITCODE
  $generic = Read-JsonIfPresent -Path $genericOut
}
$genericPassed = ($genericExitCode -eq 0 -and $null -ne $generic -and [string]$generic.result -eq "pass_local_only" -and [int]$generic.failed_check_count -eq 0)
[void]$checks.Add((New-Check -Name "generic_package_deploy_consistency" -Passed $genericPassed -Observed ([ordered]@{
  script_exists = Test-Path -LiteralPath $genericScript -PathType Leaf
  exit_code = $genericExitCode
  result = $(if ($null -ne $generic) { $generic.result } else { $null })
  failure_category = $(if ($null -ne $generic) { $generic.failure_category } else { $null })
  failed_check_count = $(if ($null -ne $generic) { $generic.failed_check_count } else { $null })
}) -Expected "generic validator returns pass_local_only with zero failed checks" -FailureCategory "generic_package_deploy_validation_failed"))

$laneIds = [ordered]@{
  requested = $LaneId
  run_manifest = $(if ($null -ne $run) { [string]$run.lane_id } else { "" })
  deploy_manifest = $(if ($null -ne $deploy) { [string]$deploy.lane_id } else { "" })
  runtime_requirements = $(if ($null -ne $requirements) { [string]$requirements.lane_id } else { "" })
  smoke_request = $(if ($null -ne $smoke) { [string]$smoke.lane_id } else { "" })
}
$allLaneIdsMatch = ($supportedLane -and @($laneIds.Values | Where-Object { [string]$_ -ne $LaneId }).Count -eq 0)
[void]$checks.Add((New-Check -Name "selected_lane_identity" -Passed $allLaneIdsMatch -Observed $laneIds -Expected "every input lane_id equals requested lane" -FailureCategory "selected_lane_mismatch"))

$models = if ($null -ne $requirements) { @($requirements.required_models) } else { @() }
$checkpoint = @($models | Where-Object { [string]$_.role -eq "checkpoint" } | Select-Object -First 1)
$controlnet = @($models | Where-Object { [string]$_.role -eq "controlnet" } | Select-Object -First 1)
$checkpointRow = if ($checkpoint.Count -gt 0) { $checkpoint[0] } else { $null }
$controlnetRow = if ($controlnet.Count -gt 0) { $controlnet[0] } else { $null }
$modelContractPass = ((Test-HashContract -Row $checkpointRow) -and (Test-HashContract -Row $controlnetRow))
[void]$checks.Add((New-Check -Name "required_model_contracts" -Passed $modelContractPass -Observed ([ordered]@{
  required_model_count = $models.Count
  checkpoint = $checkpointRow
  controlnet = $controlnetRow
}) -Expected "one hash-bound checkpoint and one hash-bound ControlNet model" -FailureCategory "required_model_contract_invalid"))

$controlFamily = if ($null -ne $requirements) { [string]$requirements.control_family } else { "" }
$familyPass = ($supportedLane -and -not [string]::IsNullOrWhiteSpace($controlFamily) -and $controlFamily.ToLowerInvariant().Contains($expectedMapType))
[void]$checks.Add((New-Check -Name "control_family_matches_lane" -Passed $familyPass -Observed $controlFamily -Expected $expectedMapType -FailureCategory "control_family_mismatch"))

$inputAssets = if ($null -ne $requirements) { @($requirements.required_input_assets) } else { @() }
$controlImages = @($inputAssets | Where-Object { [string]$_.role -eq "control_image" })
$controlImage = if ($controlImages.Count -eq 1) { $controlImages[0] } else { $null }
$controlImagePass = (
  $controlImages.Count -eq 1 -and
  (Test-HashContract -Row $controlImage) -and
  [string]$controlImage.control_map_type -eq $expectedMapType
)
[void]$checks.Add((New-Check -Name "control_image_contract" -Passed $controlImagePass -Observed $controlImage -Expected "one hash-bound control_image with control_map_type $expectedMapType" -FailureCategory "control_image_contract_invalid"))

$patch = if ($null -ne $smoke) { $smoke.request_patch_values } else { $null }
$patchBindings = [ordered]@{
  model_asset = $(if ($null -ne $patch) { [string]$patch.model_asset } else { "" })
  expected_model_asset = $(if ($null -ne $checkpointRow) { [string]$checkpointRow.filename } else { "" })
  controlnet_asset = $(if ($null -ne $patch) { [string]$patch.controlnet_asset } else { "" })
  expected_controlnet_asset = $(if ($null -ne $controlnetRow) { [string]$controlnetRow.filename } else { "" })
  control_image = $(if ($null -ne $patch) { [string]$patch.control_image } else { "" })
  expected_control_image = $(if ($null -ne $controlImage) { [string]$controlImage.filename } else { "" })
}
$patchPass = (
  $null -ne $patch -and
  -not [string]::IsNullOrWhiteSpace([string]$patchBindings.model_asset) -and
  [string]$patchBindings.model_asset -eq [string]$patchBindings.expected_model_asset -and
  [string]$patchBindings.controlnet_asset -eq [string]$patchBindings.expected_controlnet_asset -and
  [string]$patchBindings.control_image -eq [string]$patchBindings.expected_control_image
)
[void]$checks.Add((New-Check -Name "smoke_request_asset_bindings" -Passed $patchPass -Observed $patchBindings -Expected "smoke request binds checkpoint, ControlNet, and control image filenames" -FailureCategory "smoke_asset_binding_mismatch"))

$requirementsSource = "Workflows/base_generation/$LaneId/runtime_requirements.json"
$smokeSource = "Workflows/base_generation/$LaneId/smoke_test_request.json"
$packagedRows = if ($null -ne $run) { @($run.packaged_files) } else { @() }
$requirementsRows = @($packagedRows | Where-Object { [string]$_.source -eq $requirementsSource })
$smokeRows = @($packagedRows | Where-Object { [string]$_.source -eq $smokeSource })
$requirementsHash = Get-Sha256 -Path $requirementsPath
$smokeHash = Get-Sha256 -Path $smokePath
$packagedContractPass = (
  $requirementsRows.Count -eq 1 -and $smokeRows.Count -eq 1 -and
  [bool]$requirementsRows[0].source_hash_match -and [bool]$smokeRows[0].source_hash_match -and
  ([string]$requirementsRows[0].sha256).ToLowerInvariant() -eq $requirementsHash -and
  ([string]$smokeRows[0].sha256).ToLowerInvariant() -eq $smokeHash
)
[void]$checks.Add((New-Check -Name "packaged_lane_contract_hashes" -Passed $packagedContractPass -Observed ([ordered]@{
  runtime_requirements_source = $requirementsSource
  runtime_requirements_row_count = $requirementsRows.Count
  runtime_requirements_input_sha256 = $requirementsHash
  runtime_requirements_packaged_sha256 = $(if ($requirementsRows.Count -eq 1) { $requirementsRows[0].sha256 } else { $null })
  smoke_request_source = $smokeSource
  smoke_request_row_count = $smokeRows.Count
  smoke_request_input_sha256 = $smokeHash
  smoke_request_packaged_sha256 = $(if ($smokeRows.Count -eq 1) { $smokeRows[0].sha256 } else { $null })
}) -Expected "selected runtime requirements and smoke request appear once and match packaged source hashes" -FailureCategory "packaged_lane_contract_mismatch"))

$failedChecks = @($checks | Where-Object { [string]$_.result -ne "pass" })
$failureCategories = @($failedChecks | ForEach-Object { [string]$_.failure_category } | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
$result = if ($failedChecks.Count -eq 0 -and (-not $Strict -or $warnings.Count -eq 0)) { "pass_local_only" } else { "fail" }
$failureCategory = if ($result -eq "pass_local_only") { $null } elseif ($failureCategories.Count -gt 0) { $failureCategories[0] } else { "strict_warning_failure" }

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "controlnet_selected_lane_package_deploy_consistency_validation"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  result = $result
  failure_category = $failureCategory
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  s3_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  lane_id = $LaneId
  expected_control_map_type = $expectedMapType
  run_id = $(if ($null -ne $run) { [string]$run.run_id } else { $null })
  bundle_id = $(if ($null -ne $deploy) { [string]$deploy.bundle_id } else { $null })
  run_package_manifest = ConvertTo-ProjectRelativePath -Path $runPath
  deploy_bundle_manifest = ConvertTo-ProjectRelativePath -Path $deployPath
  runtime_requirements = ConvertTo-ProjectRelativePath -Path $requirementsPath
  smoke_test_request = ConvertTo-ProjectRelativePath -Path $smokePath
  generic_validator_result = $(if ($null -ne $generic) { [string]$generic.result } else { $null })
  generic_validator_failure_category = $(if ($null -ne $generic) { $generic.failure_category } else { $null })
  generic_validator_failed_check_count = $(if ($null -ne $generic) { $generic.failed_check_count } else { $null })
  check_count = $checks.Count
  checks = @($checks)
  failed_check_count = $failedChecks.Count
  failure_categories = @($failureCategories)
  warnings = @($warnings)
  target_runtime_proof = $false
  certification_claimed = $false
  promotion_allowed = $false
  boundary = "Local ControlNet package, deploy, and selected-lane contract validation only. No external service was contacted and no target-runtime, promotion, or certification claim is made."
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
  $OutFile = "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_CONTROLNET_SELECTED_LANE_PACKAGE_DEPLOY_CONSISTENCY_$stamp.json"
}
$outPath = Resolve-ProjectPath -Path $OutFile
[System.IO.Directory]::CreateDirectory((Split-Path -Parent $outPath)) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outPath, ($record | ConvertTo-Json -Depth 30) + [Environment]::NewLine, $utf8NoBom)

if (Test-Path -LiteralPath $genericOut -PathType Leaf) {
  Remove-Item -LiteralPath $genericOut -Force
}
$record | ConvertTo-Json -Depth 30
if ($result -ne "pass_local_only") { exit 1 }
exit 0
