param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main"
)

$ErrorActionPreference = "Stop"
$laneId = "sdxl_realvisxl_controlnet_openpose_lane"
$validator = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-ControlNetSelectedLanePackageDeployConsistency.ps1"
$tempRoot = Join-Path $env:TEMP ("controlnet_profile_asset_regression_{0}" -f ([guid]::NewGuid().ToString("N")))
$qaScriptRoot = Join-Path $tempRoot "Plan\Instructions\QA\Scripts"
$laneRoot = Join-Path $tempRoot "Workflows\base_generation\$laneId"
$runRoot = Join-Path $tempRoot "run"
$packagedRoot = Join-Path $runRoot "lane_files"
$deployRoot = Join-Path $tempRoot "deploy"

function Write-Json {
  param([string]$Path, [object]$Value)
  $parent = Split-Path -Parent $Path
  if (-not [string]::IsNullOrWhiteSpace($parent)) {
    New-Item -ItemType Directory -Path $parent -Force | Out-Null
  }
  $Value | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $Path -Encoding utf8
}

function Get-Sha256 {
  param([string]$Path)
  return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Invoke-Case {
  param([string]$Name, [string]$ControlImage, [bool]$ShouldPass)

  $smoke = [ordered]@{
    lane_id = $laneId
    request_patch_values = [ordered]@{
      model_asset = "realvisxlV50_v50Bakedvae.safetensors"
      controlnet_asset = "OpenPoseXL2.safetensors"
      control_image = $ControlImage
    }
  }
  $smokeSource = Join-Path $laneRoot "smoke_test_request.json"
  $smokePackaged = Join-Path $packagedRoot "smoke_test_request.json"
  Write-Json -Path $smokeSource -Value $smoke
  Write-Json -Path $smokePackaged -Value $smoke

  $run = [ordered]@{
    run_id = "profile_asset_$Name"
    lane_id = $laneId
    prompt_profile = [ordered]@{ applied = $true }
    packaged_files = @(
      [ordered]@{
        source = "Workflows/base_generation/$laneId/runtime_requirements.json"
        packaged = "run/lane_files/runtime_requirements.json"
        sha256 = Get-Sha256 -Path (Join-Path $packagedRoot "runtime_requirements.json")
        source_hash_match = $true
      },
      [ordered]@{
        source = "Workflows/base_generation/$laneId/smoke_test_request.json"
        packaged = "run/lane_files/smoke_test_request.json"
        sha256 = Get-Sha256 -Path $smokePackaged
        source_hash_match = $false
        profile_modified = $true
      }
    )
  }
  $runManifest = Join-Path $runRoot "RUN_PACKAGE_MANIFEST.json"
  Write-Json -Path $runManifest -Value $run

  $outFile = Join-Path $tempRoot ("result_{0}.json" -f $Name)
  & powershell -NoProfile -File $validator `
    -ProjectRoot $tempRoot `
    -LaneId $laneId `
    -RunPackageManifestFile $runManifest `
    -DeployBundleManifestFile (Join-Path $deployRoot "DEPLOY_BUNDLE_MANIFEST.json") `
    -RuntimeRequirementsFile (Join-Path $laneRoot "runtime_requirements.json") `
    -SmokeTestRequestFile $smokePackaged `
    -OutFile $outFile *> $null
  $exitCode = $LASTEXITCODE
  $record = Get-Content -LiteralPath $outFile -Raw | ConvertFrom-Json
  $passed = if ($ShouldPass) {
    $exitCode -eq 0 -and [string]$record.result -eq "pass_local_only"
  } else {
    $exitCode -ne 0 -and [string]$record.result -eq "fail" -and
    @($record.failure_categories) -contains "control_image_contract_invalid"
  }
  return [pscustomobject][ordered]@{
    case = $Name
    should_pass = $ShouldPass
    validator_result = [string]$record.result
    failure_categories = @($record.failure_categories)
    expectation_met = $passed
  }
}

try {
  New-Item -ItemType Directory -Path $qaScriptRoot, $laneRoot, $packagedRoot, $deployRoot -Force | Out-Null

  @'
param([string]$ProjectRoot,[string]$RunPackageManifestFile,[string]$DeployBundleManifestFile,[string]$OutFile)
[ordered]@{ result = "pass_local_only"; failure_category = $null; failed_check_count = 0 } |
  ConvertTo-Json | Set-Content -LiteralPath $OutFile -Encoding utf8
exit 0
'@ | Set-Content -LiteralPath (Join-Path $qaScriptRoot "Test-RunPackageDeployBundleConsistency.ps1") -Encoding utf8

  $requirements = [ordered]@{
    lane_id = $laneId
    control_family = "ControlNet OpenPose SDXL"
    required_models = @(
      [ordered]@{ role = "checkpoint"; filename = "realvisxlV50_v50Bakedvae.safetensors"; sha256 = ("a" * 64); node_id = "4"; input = "ckpt_name" },
      [ordered]@{ role = "controlnet"; filename = "OpenPoseXL2.safetensors"; sha256 = ("b" * 64); node_id = "10"; input = "control_net_name" }
    )
    required_input_assets = @(
      [ordered]@{ role = "control_image"; filename = "tabletop.png"; control_map_type = "openpose"; node_id = "11"; node_class = "LoadImage"; input = "image"; sha256 = ("c" * 64) },
      [ordered]@{ role = "profile_scoped_fullbody_walking_control_image"; filename = "fullbody.png"; control_map_type = "dwpose_openpose_body_hands_face"; node_id = "11"; node_class = "LoadImage"; input = "image"; sha256 = ("d" * 64) }
    )
  }
  $requirementsSource = Join-Path $laneRoot "runtime_requirements.json"
  $requirementsPackaged = Join-Path $packagedRoot "runtime_requirements.json"
  Write-Json -Path $requirementsSource -Value $requirements
  Write-Json -Path $requirementsPackaged -Value $requirements
  Write-Json -Path (Join-Path $deployRoot "DEPLOY_BUNDLE_MANIFEST.json") -Value ([ordered]@{ lane_id = $laneId; bundle_id = "fixture" })

  $cases = @(
    Invoke-Case -Name "profile_scoped_match" -ControlImage "fullbody.png" -ShouldPass $true
    Invoke-Case -Name "undeclared_profile_asset" -ControlImage "missing.png" -ShouldPass $false
  )
  $failed = @($cases | Where-Object { -not $_.expectation_met })
  $record = [ordered]@{
    result = $(if ($failed.Count -eq 0) { "pass" } else { "fail" })
    classification = $(if ($failed.Count -eq 0) { "CONTROLNET_PROFILE_ASSET_REGRESSION_PASS" } else { "CONTROLNET_PROFILE_ASSET_REGRESSION_FAIL" })
    checked = $cases.Count
    failed = $failed.Count
    cases = $cases
  }
  $record | ConvertTo-Json -Depth 10
  if ($failed.Count -gt 0) { exit 1 }
} finally {
  if (Test-Path -LiteralPath $tempRoot) {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force
  }
}
