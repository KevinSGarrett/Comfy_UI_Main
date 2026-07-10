<#
.SYNOPSIS
Exercises local ComfyUI development preflight model-requirement handling.

.DESCRIPTION
Builds disposable project and ComfyUI roots, then verifies missing, malformed,
empty, absent-model, and present-model runtime requirement states. No GPU work,
ComfyUI launch, external service, or authoritative project mutation occurs.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
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

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 20
  )
  $parent = Split-Path -Parent $Path
  if (-not [string]::IsNullOrWhiteSpace($parent)) {
    [System.IO.Directory]::CreateDirectory($parent) | Out-Null
  }
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth) + [Environment]::NewLine, $encoding)
}

function Write-TextNoBom {
  param(
    [Parameter(Mandatory=$true)][string]$Value,
    [Parameter(Mandatory=$true)][string]$Path
  )
  $parent = Split-Path -Parent $Path
  if (-not [string]::IsNullOrWhiteSpace($parent)) {
    [System.IO.Directory]::CreateDirectory($parent) | Out-Null
  }
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, $Value, $encoding)
}

function Get-Check {
  param(
    [AllowNull()][object]$Payload,
    [Parameter(Mandatory=$true)][string]$Name
  )
  if ($null -eq $Payload) { return $null }
  return @($Payload.checks | Where-Object { [string]$_.name -eq $Name } | Select-Object -First 1)
}

function Invoke-RegressionCase {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][string]$RequirementMode,
    [Parameter(Mandatory=$true)][string]$ExpectedStatus,
    [Parameter(Mandatory=$true)][int]$ExpectedModelCount,
    [Parameter(Mandatory=$true)][bool]$ExpectedModelsPresent,
    [ValidateSet("none", "project", "comfy")][string]$ModelPlacement = "none"
  )

  $caseRoot = Join-Path $tempRoot $Name
  $projectFixture = Join-Path $caseRoot "project"
  $comfyFixture = Join-Path $caseRoot "ComfyUI"
  $laneDir = Join-Path $projectFixture "Workflows\base_generation\fixture_lane"
  [System.IO.Directory]::CreateDirectory($laneDir) | Out-Null
  [System.IO.Directory]::CreateDirectory((Join-Path $projectFixture "models\checkpoints")) | Out-Null
  [System.IO.Directory]::CreateDirectory((Join-Path $comfyFixture "models\checkpoints")) | Out-Null
  Write-TextNoBom -Value "# disposable ComfyUI main fixture`n" -Path (Join-Path $comfyFixture "main.py")

  $model = [ordered]@{
    role = "checkpoint"
    filename = "fixture_model.safetensors"
    comfyui_model_subdir = "checkpoints"
    sha256 = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
  $requirementsPath = Join-Path $laneDir "runtime_requirements.json"
  switch ($RequirementMode) {
    "missing" { }
    "malformed" { Write-TextNoBom -Value "{ invalid json" -Path $requirementsPath }
    "empty" { Write-JsonNoBom -Value ([ordered]@{ schema_version = "1.0"; lane_id = "fixture_lane"; required_models = @() }) -Path $requirementsPath }
    "one_model" { Write-JsonNoBom -Value ([ordered]@{ schema_version = "1.0"; lane_id = "fixture_lane"; required_models = @($model) }) -Path $requirementsPath }
    "invalid_model" { Write-JsonNoBom -Value ([ordered]@{ schema_version = "1.0"; lane_id = "fixture_lane"; required_models = @([ordered]@{ role = "checkpoint"; filename = ""; comfyui_model_subdir = ""; sha256 = "bad" }) }) -Path $requirementsPath }
    default { throw "Unsupported requirement mode: $RequirementMode" }
  }
  if ($ModelPlacement -eq "project") {
    Write-TextNoBom -Value "fixture model`n" -Path (Join-Path $projectFixture "models\checkpoints\fixture_model.safetensors")
  } elseif ($ModelPlacement -eq "comfy") {
    Write-TextNoBom -Value "fixture model`n" -Path (Join-Path $comfyFixture "models\checkpoints\fixture_model.safetensors")
  }

  $childOut = Join-Path $resultsRoot "$Name.json"
  & powershell -NoProfile -ExecutionPolicy Bypass -File $preflightScript `
    -ProjectRoot $projectFixture `
    -LaneId "fixture_lane" `
    -LocalComfyRoot $comfyFixture `
    -OutFile $childOut *> $null
  $exitCode = $LASTEXITCODE
  $payload = $null
  if (Test-Path -LiteralPath $childOut -PathType Leaf) {
    try { $payload = Get-Content -LiteralPath $childOut -Raw | ConvertFrom-Json } catch { $payload = $null }
  }
  $requirementsCheck = Get-Check -Payload $payload -Name "selected_lane_runtime_requirements_valid"
  $declaredCheck = Get-Check -Payload $payload -Name "selected_lane_required_models_declared"
  $contractsCheck = Get-Check -Payload $payload -Name "selected_lane_required_model_contracts_valid"
  $modelsCheck = Get-Check -Payload $payload -Name "local_required_models_present"
  $requirementsStatePass = (
    $null -ne $payload -and
    [string]$payload.runtime_requirements.status -eq $ExpectedStatus -and
    [int]$payload.runtime_requirements.required_model_count -eq $ExpectedModelCount
  )
  $modelsStatePass = (
    $null -ne $modelsCheck -and @($modelsCheck).Count -gt 0 -and
    [bool]$modelsCheck[0].passed -eq $ExpectedModelsPresent -and
    [bool]$payload.local_gpu_generation_candidate -eq $false
  )
  $contractCheckPass = if ($RequirementMode -eq "one_model") {
    $null -ne $requirementsCheck -and [bool]$requirementsCheck[0].passed -and
    $null -ne $declaredCheck -and [bool]$declaredCheck[0].passed -and
    $null -ne $contractsCheck -and [bool]$contractsCheck[0].passed
  } elseif ($RequirementMode -eq "invalid_model") {
    $null -ne $requirementsCheck -and [bool]$requirementsCheck[0].passed -and
    $null -ne $declaredCheck -and [bool]$declaredCheck[0].passed -and
    $null -ne $contractsCheck -and -not [bool]$contractsCheck[0].passed
  } elseif ($RequirementMode -eq "empty") {
    $null -ne $requirementsCheck -and [bool]$requirementsCheck[0].passed -and
    $null -ne $declaredCheck -and -not [bool]$declaredCheck[0].passed -and
    $null -ne $contractsCheck -and -not [bool]$contractsCheck[0].passed
  } else {
    $null -ne $requirementsCheck -and -not [bool]$requirementsCheck[0].passed -and
    $null -ne $declaredCheck -and -not [bool]$declaredCheck[0].passed -and
    $null -ne $contractsCheck -and -not [bool]$contractsCheck[0].passed
  }
  $safetyPass = (
    $null -ne $payload -and [bool]$payload.local_only -and
    -not [bool]$payload.aws_contacted -and -not [bool]$payload.github_api_contacted -and
    -not [bool]$payload.civitai_contacted -and -not [bool]$payload.comfyui_contacted -and
    -not [bool]$payload.ec2_started -and -not [bool]$payload.generation_executed -and
    -not [bool]$payload.local_dev_replaces_ec2_final_proof -and [bool]$payload.ec2_final_proof_still_required
  )
  $passed = ($exitCode -eq 0 -and $requirementsStatePass -and $modelsStatePass -and $contractCheckPass -and $safetyPass)

  return [pscustomobject][ordered]@{
    name = $Name
    requirement_mode = $RequirementMode
    model_placement = $ModelPlacement
    result = $(if ($passed) { "pass" } else { "fail" })
    exit_code = $exitCode
    output_exists = Test-Path -LiteralPath $childOut -PathType Leaf
    observed_status = $(if ($null -ne $payload) { [string]$payload.runtime_requirements.status } else { $null })
    expected_status = $ExpectedStatus
    observed_model_count = $(if ($null -ne $payload) { [int]$payload.runtime_requirements.required_model_count } else { $null })
    expected_model_count = $ExpectedModelCount
    models_present = $(if ($null -ne $modelsCheck -and @($modelsCheck).Count -gt 0) { [bool]$modelsCheck[0].passed } else { $null })
    expected_models_present = $ExpectedModelsPresent
    local_gpu_generation_candidate = $(if ($null -ne $payload) { [bool]$payload.local_gpu_generation_candidate } else { $null })
    requirements_state_pass = $requirementsStatePass
    models_state_pass = $modelsStatePass
    contract_check_pass = $contractCheckPass
    safety_pass = $safetyPass
  }
}

if (-not (Test-Path -LiteralPath $ProjectRoot -PathType Container)) {
  throw "Authoritative project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$preflightScript = Join-Path $ProjectRoot "tools\Test-LocalComfyUIDevPreflight.ps1"
if (-not (Test-Path -LiteralPath $preflightScript -PathType Leaf)) {
  throw "Local ComfyUI dev preflight missing: $preflightScript"
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("local_comfy_dev_preflight_regression_{0}" -f ([guid]::NewGuid().ToString("N")))
$resultsRoot = Join-Path $tempRoot "results"
[System.IO.Directory]::CreateDirectory($resultsRoot) | Out-Null

$tests = @()
$tests += Invoke-RegressionCase -Name "missing_requirements_fail_closed" -RequirementMode "missing" -ExpectedStatus "missing" -ExpectedModelCount 0 -ExpectedModelsPresent $false
$tests += Invoke-RegressionCase -Name "malformed_requirements_fail_closed" -RequirementMode "malformed" -ExpectedStatus "invalid_json_or_contract" -ExpectedModelCount 0 -ExpectedModelsPresent $false
$tests += Invoke-RegressionCase -Name "empty_requirements_fail_closed" -RequirementMode "empty" -ExpectedStatus "empty_required_models" -ExpectedModelCount 0 -ExpectedModelsPresent $false
$tests += Invoke-RegressionCase -Name "invalid_model_declaration_fails" -RequirementMode "invalid_model" -ExpectedStatus "invalid_model_contract" -ExpectedModelCount 1 -ExpectedModelsPresent $false
$tests += Invoke-RegressionCase -Name "declared_model_missing_fails" -RequirementMode "one_model" -ExpectedStatus "ready" -ExpectedModelCount 1 -ExpectedModelsPresent $false
$tests += Invoke-RegressionCase -Name "project_model_present_passes" -RequirementMode "one_model" -ExpectedStatus "ready" -ExpectedModelCount 1 -ExpectedModelsPresent $true -ModelPlacement "project"
$tests += Invoke-RegressionCase -Name "comfy_model_present_passes" -RequirementMode "one_model" -ExpectedStatus "ready" -ExpectedModelCount 1 -ExpectedModelsPresent $true -ModelPlacement "comfy"

$failed = @($tests | Where-Object { [string]$_.result -ne "pass" })
$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "local_comfyui_dev_preflight_regression"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  result = $(if ($failed.Count -eq 0) { "pass_local_only" } else { "fail" })
  failure_category = $(if ($failed.Count -eq 0) { $null } else { "local_comfyui_dev_preflight_regression_failed" })
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  s3_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  work_order_id = "W66-LOCAL-COMFYUI-DEV-PREFLIGHT"
  preflight_script = ConvertTo-ProjectRelativePath -Path $preflightScript
  test_count = $tests.Count
  passing_test_count = @($tests | Where-Object { [string]$_.result -eq "pass" }).Count
  failed_test_count = $failed.Count
  tests = @($tests)
  work_order_closed = $false
  target_runtime_proof = $false
  certification_claimed = $false
  boundary = "Disposable local model-requirement regression only. No GPU generation, ComfyUI launch, EC2, or target-runtime proof occurred."
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
  $OutFile = "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_LOCAL_COMFYUI_DEV_PREFLIGHT_REGRESSION_$stamp.json"
}
$outPath = Resolve-ProjectPath -Path $OutFile
Write-JsonNoBom -Value $record -Path $outPath -Depth 20

$tempBase = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd("\") + "\"
$tempResolved = [System.IO.Path]::GetFullPath($tempRoot)
if ($tempResolved.StartsWith($tempBase, [System.StringComparison]::OrdinalIgnoreCase)) {
  Remove-Item -LiteralPath $tempResolved -Recurse -Force
}

$record | ConvertTo-Json -Depth 20
if ($failed.Count -gt 0) { exit 1 }
exit 0
