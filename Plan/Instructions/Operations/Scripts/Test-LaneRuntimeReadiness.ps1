<#
.SYNOPSIS
Checks whether the selected workflow lane is ready for EC2 static proof and generation.

.DESCRIPTION
This helper is local-only. It validates the selected lane's workflow contract,
required helper scripts, existing local evidence, and latest AWS auth gate
record. It never starts EC2, posts to ComfyUI, downloads models, or performs
generation. Use it before any EC2 runtime attempt to prevent drift or unsafe
starts.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LaneId = "sdxl_low_risk_fallback_lane",
  [string]$AuthGateFile = "",
  [string]$StaticProofFile = "",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Get-RelativePathCompat {
  param(
    [string]$BasePath,
    [string]$TargetPath
  )

  $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
  $baseFull = [System.IO.Path]::GetFullPath($BasePath)
  if (!$baseFull.EndsWith($separator)) {
    $baseFull = "$baseFull$separator"
  }

  $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
  $baseUri = New-Object System.Uri($baseFull)
  $targetUri = New-Object System.Uri($targetFull)
  $relativeUri = $baseUri.MakeRelativeUri($targetUri)
  $relativePath = [System.Uri]::UnescapeDataString($relativeUri.ToString())
  return $relativePath.Replace("/", $separator)
}

function ConvertTo-ProjectRelativePath {
  param(
    [string]$BasePath,
    [string]$TargetPath
  )

  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }
  $relative = Get-RelativePathCompat -BasePath $BasePath -TargetPath $TargetPath
  return $relative.Replace("\", "/")
}

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path)) { throw "JSON file missing: $Path" }
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Test-PowerShellParser {
  param([Parameter(Mandatory=$true)][string]$Path)

  $tokens = $null
  $errors = $null
  [System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$errors) > $null
  return [ordered]@{
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    exists = (Test-Path -LiteralPath $Path)
    parse_pass = ($errors.Count -eq 0)
    errors = @($errors | ForEach-Object { $_.Message })
  }
}

function Find-LatestFile {
  param(
    [string]$Directory,
    [string]$Filter
  )

  if (!(Test-Path -LiteralPath $Directory)) { return $null }
  $file = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if ($null -eq $file) { return $null }
  return $file.FullName
}

function Has-Property {
  param(
    [object]$Object,
    [string]$Name
  )
  if ($null -eq $Object) { return $false }
  return @($Object.PSObject.Properties.Name) -contains $Name
}

$laneDir = Join-Path $ProjectRoot "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\$LaneId"
$workflowPath = Join-Path $laneDir "workflow.api.json"
$patchPath = Join-Path $laneDir "patch_points.json"
$runtimePath = Join-Path $laneDir "runtime_requirements.json"
$smokePath = Join-Path $laneDir "smoke_test_request.json"

$runtimeReadinessDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Runtime_Readiness"
if ([string]::IsNullOrWhiteSpace($AuthGateFile)) {
  $AuthGateFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W60_W61_AWS_AUTH_GATE_*.json"
}

$workflowStaticDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Static_Validation"
if ([string]::IsNullOrWhiteSpace($StaticProofFile)) {
  $StaticProofFile = Find-LatestFile -Directory $workflowStaticDir -Filter "W61_EC2_LANE_STATIC_PROOF_*.json"
}

$helperPaths = @(
  (Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-ComfyWorkflowStatic.ps1"),
  (Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1"),
  (Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Invoke-ComfyWorkflowSmoke.ps1"),
  (Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1"),
  (Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Test-AwsAuthGate.ps1"),
  (Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\New-EC2PullbackRecord.ps1"),
  (Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\New-ImageArtifactQARecord.ps1")
)

$evidenceFiles = [ordered]@{
  workflow_static_validation = Join-Path $workflowStaticDir "W61_SDXL_LOW_RISK_WORKFLOW_STATIC_VALIDATION_20260706T024811-0500.json"
  smoke_dry_run = Join-Path $workflowStaticDir "W61_COMFY_WORKFLOW_SMOKE_DRY_RUN_20260706T025536-0500.json"
  smoke_request = Join-Path $workflowStaticDir "W61_COMFY_WORKFLOW_SMOKE_REQUEST_20260706T025536-0500.json"
  image_qa_dry_run = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Image_Artifact_QA\W61_IMAGE_QA_DRY_RUN_20260706T030037-0500.json"
  pullback_dry_run = Join-Path $runtimeReadinessDir "W60_EC2_PULLBACK_RECORD_DRY_RUN_20260706T031758-0500.json"
}

$errors = @()
$warnings = @()

$laneFiles = @()
foreach ($path in @($workflowPath, $patchPath, $runtimePath, $smokePath)) {
  $entry = [ordered]@{
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $path
    exists = (Test-Path -LiteralPath $path)
    json_valid = $false
  }
  if ($entry.exists) {
    try {
      $null = Read-JsonFile -Path $path
      $entry.json_valid = $true
    } catch {
      $entry.error = $_.Exception.Message
      $errors += "Invalid JSON: $($entry.path)"
    }
  } else {
    $errors += "Missing lane file: $($entry.path)"
  }
  $laneFiles += $entry
}

$runtime = $null
if (Test-Path -LiteralPath $runtimePath) {
  $runtime = Read-JsonFile -Path $runtimePath
}

$helperResults = @()
foreach ($helper in $helperPaths) {
  $helperResults += Test-PowerShellParser -Path $helper
}
foreach ($helper in $helperResults) {
  if (!$helper.exists) { $errors += "Missing helper script: $($helper.path)" }
  elseif (!$helper.parse_pass) { $errors += "Helper parser failed: $($helper.path)" }
}

$evidenceResults = @()
foreach ($key in $evidenceFiles.Keys) {
  $path = $evidenceFiles[$key]
  $entry = [ordered]@{
    name = $key
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $path
    exists = (Test-Path -LiteralPath $path)
    json_valid = $false
  }
  if ($entry.exists) {
    try {
      $null = Read-JsonFile -Path $path
      $entry.json_valid = $true
    } catch {
      $entry.error = $_.Exception.Message
      $errors += "Invalid evidence JSON: $($entry.path)"
    }
  } else {
    $errors += "Missing evidence file: $($entry.path)"
  }
  $evidenceResults += $entry
}

$auth = [ordered]@{
  file = $(if ([string]::IsNullOrWhiteSpace($AuthGateFile)) { $null } else { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $AuthGateFile })
  found = (![string]::IsNullOrWhiteSpace($AuthGateFile) -and (Test-Path -LiteralPath $AuthGateFile))
  ec2_work_allowed = $false
  safe_to_start_ec2 = $false
  generation_allowed = $false
  status = "missing_auth_gate"
}
if ($auth.found) {
  $authJson = Read-JsonFile -Path $AuthGateFile
  $auth.ec2_work_allowed = [bool]$authJson.ec2_work_allowed
  $auth.safe_to_start_ec2 = [bool]$authJson.safe_to_start_ec2
  $auth.generation_allowed = [bool]$authJson.generation_allowed
  $auth.status = $(if ($auth.safe_to_start_ec2) { "pass" } else { "blocked" })
  if (Has-Property -Object $authJson -Name "remote_login") {
    $auth.remote_login_status = [string]$authJson.remote_login.status
  }
  if (Has-Property -Object $authJson -Name "sts_after" -and $null -ne $authJson.sts_after) {
    $auth.sts_failure_category = [string]$authJson.sts_after.failure_category
  } elseif (Has-Property -Object $authJson -Name "sts_before" -and $null -ne $authJson.sts_before) {
    $auth.sts_failure_category = [string]$authJson.sts_before.failure_category
  }
}

$staticProof = [ordered]@{
  file = $(if ([string]::IsNullOrWhiteSpace($StaticProofFile)) { $null } else { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $StaticProofFile })
  found = (![string]::IsNullOrWhiteSpace($StaticProofFile) -and (Test-Path -LiteralPath $StaticProofFile))
  object_info_pass = $false
  model_hashes_present = $false
  generation_allowed = $false
  status = "missing_ec2_static_proof"
}
if ($staticProof.found) {
  $proofJson = Read-JsonFile -Path $StaticProofFile
  $proofPayload = $proofJson
  if (Has-Property -Object $proofJson -Name "stdout" -and ![string]::IsNullOrWhiteSpace([string]$proofJson.stdout)) {
    try {
      $proofPayload = ([string]$proofJson.stdout | ConvertFrom-Json)
    } catch {
      $warnings += "Static proof stdout was not parseable JSON."
    }
  }
  if (Has-Property -Object $proofPayload -Name "object_info") {
    $staticProof.object_info_pass = ([string]$proofPayload.object_info.status -eq "pass")
  }
  if (Has-Property -Object $proofPayload -Name "model_proofs") {
    $models = @($proofPayload.model_proofs)
    $staticProof.model_hashes_present = ($models.Count -gt 0 -and (@($models | Where-Object { [string]::IsNullOrWhiteSpace([string]$_.sha256) }).Count -eq 0))
  }
  $staticProof.generation_allowed = ($staticProof.object_info_pass -and $staticProof.model_hashes_present)
  $staticProof.status = $(if ($staticProof.generation_allowed) { "pass" } else { "incomplete" })
}

$localPreEc2Ready = (
  ($errors.Count -eq 0) -and
  (@($laneFiles | Where-Object { -not $_.exists -or -not $_.json_valid }).Count -eq 0) -and
  (@($helperResults | Where-Object { -not $_.exists -or -not $_.parse_pass }).Count -eq 0) -and
  (@($evidenceResults | Where-Object { -not $_.exists -or -not $_.json_valid }).Count -eq 0)
)

$readyForEc2StaticProof = ($localPreEc2Ready -and [bool]$auth.safe_to_start_ec2)
$readyForGeneration = ($readyForEc2StaticProof -and [bool]$staticProof.generation_allowed)

if (!$auth.safe_to_start_ec2) {
  $warnings += "AWS auth gate does not allow EC2 start."
}
if (!$staticProof.generation_allowed) {
  $warnings += "Generation remains blocked until EC2 object-info/path/hash proof passes."
}

$record = [ordered]@{
  evidence_id = "LANE-RUNTIME-READINESS-" + (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  lane_id = $LaneId
  lane_dir = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $laneDir
  lane_files = $laneFiles
  runtime_requirements_summary = [ordered]@{
    required_nodes = $(if ($null -ne $runtime) { @($runtime.required_nodes) } else { @() })
    required_model_count = $(if ($null -ne $runtime) { @($runtime.required_models).Count } else { 0 })
  }
  helper_scripts = $helperResults
  evidence_files = $evidenceResults
  auth_gate = $auth
  ec2_static_proof = $staticProof
  local_pre_ec2_ready = $localPreEc2Ready
  ready_for_ec2_static_proof = $readyForEc2StaticProof
  ready_for_generation = $readyForGeneration
  errors = $errors
  warnings = $warnings
  next_action = $(if (!$auth.safe_to_start_ec2) { "Complete AWS remote browser login and rerun Test-AwsAuthGate.ps1." } elseif (!$staticProof.generation_allowed) { "Run Invoke-EC2LaneStaticProof.ps1 -Execute and record object-info/path/hash proof." } else { "Run Invoke-ComfyWorkflowSmoke.ps1 -Execute, pull back artifacts, create PULLBACK_RECORD.json, then perform image QA." })
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $outStamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_$outStamp.json"
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
$record | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $OutFile -Encoding UTF8
Write-Host "Wrote lane runtime readiness record: $OutFile"
$record | ConvertTo-Json -Depth 30

if (!$localPreEc2Ready) { exit 2 }
