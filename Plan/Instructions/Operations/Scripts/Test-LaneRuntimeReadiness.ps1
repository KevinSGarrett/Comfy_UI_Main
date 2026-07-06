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
  [string]$ProfileMatrixFile = "",
  [string]$StaticProofFile = "",
  [string]$ModelRegistryCoverageFile = "",
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
    [string]$Filter,
    [string]$ExcludePattern = ""
  )

  if (!(Test-Path -LiteralPath $Directory)) { return $null }
  $files = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File
  if (![string]::IsNullOrWhiteSpace($ExcludePattern)) {
    $files = $files | Where-Object { $_.Name -notmatch $ExcludePattern }
  }
  $file = $files | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($null -eq $file) { return $null }
  return $file.FullName
}

function Test-JsonMatchesLane {
  param(
    [object]$Payload,
    [string]$ExpectedLaneId
  )

  if ($null -eq $Payload -or [string]::IsNullOrWhiteSpace($ExpectedLaneId)) { return $false }
  if ((Has-Property -Object $Payload -Name "lane_id") -and [string]$Payload.lane_id -eq $ExpectedLaneId) {
    return $true
  }
  if (Has-Property -Object $Payload -Name "lane_dir") {
    $laneDirText = ([string]$Payload.lane_dir).Replace("\", "/").TrimEnd("/")
    return $laneDirText.EndsWith("/$ExpectedLaneId", [System.StringComparison]::OrdinalIgnoreCase)
  }
  if (Has-Property -Object $Payload -Name "workflow_path") {
    $workflowText = ([string]$Payload.workflow_path).Replace("\", "/")
    return $workflowText -match "/$([regex]::Escape($ExpectedLaneId))/workflow\.api\.json$"
  }
  return $false
}

function Find-LatestJsonByLaneId {
  param(
    [string]$Directory,
    [string]$Filter,
    [string]$ExpectedLaneId,
    [string]$ExcludePattern = "",
    [string]$RequiredProperty = "",
    [string]$RequiredValue = ""
  )

  if (!(Test-Path -LiteralPath $Directory)) { return $null }
  $files = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File
  if (![string]::IsNullOrWhiteSpace($ExcludePattern)) {
    $files = $files | Where-Object { $_.Name -notmatch $ExcludePattern }
  }
  foreach ($file in @($files | Sort-Object LastWriteTime -Descending)) {
    try {
      $payload = Read-JsonFile -Path $file.FullName
      if (!(Test-JsonMatchesLane -Payload $payload -ExpectedLaneId $ExpectedLaneId)) { continue }
      if (![string]::IsNullOrWhiteSpace($RequiredProperty)) {
        if (!(Has-Property -Object $payload -Name $RequiredProperty)) { continue }
        if (![string]::IsNullOrWhiteSpace($RequiredValue) -and [string]$payload.$RequiredProperty -ne $RequiredValue) { continue }
      }
      return $file.FullName
    } catch {
      continue
    }
  }
  return $null
}

function Resolve-ProjectOrAbsolutePath {
  param([string]$Path)

  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  if ([System.IO.Path]::IsPathRooted($Path)) { return $Path }
  return Join-Path $ProjectRoot $Path
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
if ([string]::IsNullOrWhiteSpace($ProfileMatrixFile)) {
  $ProfileMatrixFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W60_W61_AWS_PROFILE_AUTH_MATRIX_*.json"
}

$workflowStaticDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Static_Validation"
if ([string]::IsNullOrWhiteSpace($StaticProofFile)) {
  $StaticProofFile = Find-LatestFile -Directory $workflowStaticDir -Filter "W61_EC2_LANE_STATIC_PROOF_*.json" -ExcludePattern "DRY_RUN|BLOCKED_EXECUTE"
}

$modelRegistryCoverageDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Model_Registry"
if ([string]::IsNullOrWhiteSpace($ModelRegistryCoverageFile)) {
  $ModelRegistryCoverageFile = Find-LatestFile -Directory $modelRegistryCoverageDir -Filter "W61_MODEL_REGISTRY_COVERAGE*.json"
}

$helperPaths = @(
  (Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-ComfyWorkflowStatic.ps1"),
  (Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-WorkflowModelRegistryCoverage.ps1"),
  (Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1"),
  (Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Invoke-ComfyWorkflowSmoke.ps1"),
  (Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1"),
  (Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Test-AwsAuthGate.ps1"),
  (Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Test-AwsProfileAuthMatrix.ps1"),
  (Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\New-EC2PullbackRecord.ps1"),
  (Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\New-ImageArtifactQARecord.ps1")
)

$workflowStaticValidationFile = Find-LatestJsonByLaneId -Directory $workflowStaticDir -Filter "*WORKFLOW_STATIC_VALIDATION*.json" -ExpectedLaneId $LaneId
$smokeDryRunFile = Find-LatestJsonByLaneId -Directory $workflowStaticDir -Filter "*WORKFLOW_SMOKE_DRY_RUN*.json" -ExpectedLaneId $LaneId -RequiredProperty "mode" -RequiredValue "dry_run"
$smokeRequestFile = $null
if (![string]::IsNullOrWhiteSpace($smokeDryRunFile) -and (Test-Path -LiteralPath $smokeDryRunFile)) {
  try {
    $smokeDryRun = Read-JsonFile -Path $smokeDryRunFile
    if ((Has-Property -Object $smokeDryRun -Name "request_body_written") -and [bool]$smokeDryRun.request_body_written -and
        (Has-Property -Object $smokeDryRun -Name "request_body_path")) {
      $smokeRequestFile = Resolve-ProjectOrAbsolutePath -Path ([string]$smokeDryRun.request_body_path)
    }
  } catch {
    $warnings += "Unable to derive smoke request path from lane-specific smoke dry-run evidence."
  }
}

$evidenceFiles = [ordered]@{
  workflow_static_validation = $workflowStaticValidationFile
  smoke_dry_run = $smokeDryRunFile
  smoke_request = $smokeRequestFile
  model_registry_coverage = $ModelRegistryCoverageFile
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
  result = "missing_auth_gate"
  failure_category = "missing_auth_gate"
  account_match = $false
  remote_login_status = "missing_auth_gate"
  status = "missing_auth_gate"
}
if ($auth.found) {
  $authJson = Read-JsonFile -Path $AuthGateFile
  $auth.ec2_work_allowed = [bool]$authJson.ec2_work_allowed
  $auth.safe_to_start_ec2 = [bool]$authJson.safe_to_start_ec2
  $auth.generation_allowed = [bool]$authJson.generation_allowed
  if (Has-Property -Object $authJson -Name "result") {
    $auth.result = [string]$authJson.result
  } else {
    $auth.result = $(if ($auth.safe_to_start_ec2) { "pass" } else { "blocked" })
  }
  if (Has-Property -Object $authJson -Name "failure_category") {
    $auth.failure_category = $authJson.failure_category
  }
  if (Has-Property -Object $authJson -Name "account_match") {
    $auth.account_match = [bool]$authJson.account_match
  }
  if (Has-Property -Object $authJson -Name "remote_login_status") {
    $auth.remote_login_status = [string]$authJson.remote_login_status
  }
  $auth.status = $(if ($auth.safe_to_start_ec2) { "pass" } else { "blocked" })
  if (Has-Property -Object $authJson -Name "remote_login") {
    $auth.remote_login_status = [string]$authJson.remote_login.status
  }
  if ((Has-Property -Object $authJson -Name "sts_after") -and (Has-Property -Object $authJson.sts_after -Name "failure_category")) {
    $auth.sts_failure_category = [string]$authJson.sts_after.failure_category
  } elseif ((Has-Property -Object $authJson -Name "sts_before") -and (Has-Property -Object $authJson.sts_before -Name "failure_category")) {
    $auth.sts_failure_category = [string]$authJson.sts_before.failure_category
  }
  if ([string]::IsNullOrWhiteSpace([string]$auth.failure_category) -and ![string]::IsNullOrWhiteSpace([string]$auth.sts_failure_category)) {
    $auth.failure_category = [string]$auth.sts_failure_category
  }
}

$profileMatrix = [ordered]@{
  file = $(if ([string]::IsNullOrWhiteSpace($ProfileMatrixFile)) { $null } else { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $ProfileMatrixFile })
  found = (![string]::IsNullOrWhiteSpace($ProfileMatrixFile) -and (Test-Path -LiteralPath $ProfileMatrixFile))
  expected_account = $null
  active_env_profile_name = $null
  profile_count = 0
  profiles_matching_expected_count = 0
  ec2_work_allowed = $false
  safe_to_start_ec2 = $false
  result = "missing_profile_matrix"
  status = "missing_profile_matrix"
}
if ($profileMatrix.found) {
  $profileJson = Read-JsonFile -Path $ProfileMatrixFile
  if (Has-Property -Object $profileJson -Name "expected_account") {
    $profileMatrix.expected_account = [string]$profileJson.expected_account
  }
  if (Has-Property -Object $profileJson -Name "active_env_profile_name") {
    $profileMatrix.active_env_profile_name = [string]$profileJson.active_env_profile_name
  }
  if (Has-Property -Object $profileJson -Name "profile_count") {
    $profileMatrix.profile_count = [int]$profileJson.profile_count
  }
  if (Has-Property -Object $profileJson -Name "profiles_matching_expected_count") {
    $profileMatrix.profiles_matching_expected_count = [int]$profileJson.profiles_matching_expected_count
  }
  if (Has-Property -Object $profileJson -Name "ec2_work_allowed") {
    $profileMatrix.ec2_work_allowed = [bool]$profileJson.ec2_work_allowed
  }
  if (Has-Property -Object $profileJson -Name "safe_to_start_ec2") {
    $profileMatrix.safe_to_start_ec2 = [bool]$profileJson.safe_to_start_ec2
  }
  if (Has-Property -Object $profileJson -Name "result") {
    $profileMatrix.result = [string]$profileJson.result
  }
  $profileMatrix.status = $(if ($profileMatrix.safe_to_start_ec2) { "pass" } else { "blocked" })
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

$modelRegistryCoverage = [ordered]@{
  file = $(if ([string]::IsNullOrWhiteSpace($ModelRegistryCoverageFile)) { $null } else { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $ModelRegistryCoverageFile })
  found = (![string]::IsNullOrWhiteSpace($ModelRegistryCoverageFile) -and (Test-Path -LiteralPath $ModelRegistryCoverageFile))
  result = "missing_model_registry_coverage"
  failed_check_count = $null
  registry_record_count = $null
  runtime_validation_queue_row_count = $null
  active_lane_ids = @()
  selected_lane_covered = $false
  selected_lane_result = $null
  local_only = $false
  aws_contacted = $true
  github_api_contacted = $true
  civitai_contacted = $true
  comfyui_contacted = $true
  ec2_started = $true
  generation_executed = $true
  coverage_allows_selected_lane_ec2_static_proof = $false
}
if ($modelRegistryCoverage.found) {
  $coverageJson = Read-JsonFile -Path $ModelRegistryCoverageFile
  if (Has-Property -Object $coverageJson -Name "result") { $modelRegistryCoverage.result = [string]$coverageJson.result }
  foreach ($name in @("failed_check_count", "registry_record_count", "runtime_validation_queue_row_count")) {
    if (Has-Property -Object $coverageJson -Name $name) { $modelRegistryCoverage[$name] = [int]$coverageJson.$name }
  }
  foreach ($name in @("local_only", "aws_contacted", "github_api_contacted", "civitai_contacted", "comfyui_contacted", "ec2_started", "generation_executed")) {
    if (Has-Property -Object $coverageJson -Name $name) { $modelRegistryCoverage[$name] = [bool]$coverageJson.$name }
  }
  if (Has-Property -Object $coverageJson -Name "active_lane_ids") {
    $modelRegistryCoverage.active_lane_ids = @($coverageJson.active_lane_ids | ForEach-Object { [string]$_ })
    $modelRegistryCoverage.selected_lane_covered = @($modelRegistryCoverage.active_lane_ids) -contains [string]$LaneId
  }
  if (Has-Property -Object $coverageJson -Name "lane_results") {
    $selectedCoverageLaneMatches = @($coverageJson.lane_results | Where-Object { [string]$_.lane_id -eq [string]$LaneId } | Select-Object -First 1)
    if (@($selectedCoverageLaneMatches).Count -gt 0) {
      $modelRegistryCoverage.selected_lane_covered = $true
      if (Has-Property -Object $selectedCoverageLaneMatches[0] -Name "result") {
        $modelRegistryCoverage.selected_lane_result = [string]$selectedCoverageLaneMatches[0].result
      }
    }
  }
  $modelRegistryCoverage.coverage_allows_selected_lane_ec2_static_proof = (
    $modelRegistryCoverage.result -eq "pass_local_only" -and
    $modelRegistryCoverage.failed_check_count -eq 0 -and
    $modelRegistryCoverage.local_only -eq $true -and
    $modelRegistryCoverage.aws_contacted -eq $false -and
    $modelRegistryCoverage.github_api_contacted -eq $false -and
    $modelRegistryCoverage.civitai_contacted -eq $false -and
    $modelRegistryCoverage.comfyui_contacted -eq $false -and
    $modelRegistryCoverage.ec2_started -eq $false -and
    $modelRegistryCoverage.generation_executed -eq $false -and
    $modelRegistryCoverage.selected_lane_covered -eq $true -and
    $modelRegistryCoverage.selected_lane_result -eq "pass"
  )
}
if ($modelRegistryCoverage.result -ne "pass_local_only") {
  $errors += "Model registry coverage validation is missing or not pass_local_only."
}
if ($modelRegistryCoverage.selected_lane_covered -ne $true) {
  $errors += "Selected LaneId $LaneId is not covered by model registry coverage evidence."
}
if ($modelRegistryCoverage.selected_lane_result -ne "pass") {
  $errors += "Selected LaneId $LaneId does not have passing model registry coverage."
}
if ($modelRegistryCoverage.failed_check_count -ne 0) {
  $errors += "Model registry coverage validation has failed checks."
}
if ($modelRegistryCoverage.local_only -ne $true -or $modelRegistryCoverage.aws_contacted -ne $false -or $modelRegistryCoverage.github_api_contacted -ne $false -or $modelRegistryCoverage.civitai_contacted -ne $false -or $modelRegistryCoverage.comfyui_contacted -ne $false) {
  $errors += "Model registry coverage validation is not local-only or reports external contact."
}
if ($modelRegistryCoverage.ec2_started -ne $false -or $modelRegistryCoverage.generation_executed -ne $false) {
  $errors += "Model registry coverage validation unexpectedly started EC2 or generation."
}

$localPreEc2Ready = (
  ($errors.Count -eq 0) -and
  (@($laneFiles | Where-Object { -not $_.exists -or -not $_.json_valid }).Count -eq 0) -and
  (@($helperResults | Where-Object { -not $_.exists -or -not $_.parse_pass }).Count -eq 0) -and
  (@($evidenceResults | Where-Object { -not $_.exists -or -not $_.json_valid }).Count -eq 0)
)

$readyForEc2StaticProof = ($localPreEc2Ready -and [bool]$auth.safe_to_start_ec2 -and [bool]$modelRegistryCoverage.coverage_allows_selected_lane_ec2_static_proof)
$readyForGeneration = ($readyForEc2StaticProof -and [bool]$staticProof.generation_allowed)
$readinessResult = "not_ready"
$readinessFailureCategory = $null

if (!$localPreEc2Ready) {
  $readinessResult = "not_ready"
  $readinessFailureCategory = "local_pre_ec2_contract_failed"
} elseif ($readyForGeneration) {
  $readinessResult = "ready_for_generation"
} elseif ($readyForEc2StaticProof) {
  $readinessResult = "ready_for_ec2_static_proof"
  $readinessFailureCategory = "missing_ec2_static_proof"
} elseif (!$auth.safe_to_start_ec2) {
  $readinessResult = "local_pre_ec2_ready_runtime_blocked_auth"
  $readinessFailureCategory = $(if (![string]::IsNullOrWhiteSpace([string]$auth.failure_category)) { [string]$auth.failure_category } else { "aws_auth_blocked" })
} else {
  $readinessResult = "local_pre_ec2_ready_runtime_blocked"
  $readinessFailureCategory = "runtime_gate_blocked"
}

if (!$auth.safe_to_start_ec2) {
  $warnings += "AWS auth gate does not allow EC2 start."
}
if ($profileMatrix.found -and !$profileMatrix.safe_to_start_ec2) {
  $warnings += "AWS profile matrix found no profile currently safe for EC2 start."
}
if (!$modelRegistryCoverage.coverage_allows_selected_lane_ec2_static_proof) {
  $warnings += "Model registry coverage does not allow selected lane EC2 static proof."
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
  lane_evidence_selection = [ordered]@{
    workflow_static_validation = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $workflowStaticValidationFile
    smoke_dry_run = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $smokeDryRunFile
    smoke_request = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $smokeRequestFile
    lane_specific = $true
  }
  auth_gate = $auth
  profile_matrix = $profileMatrix
  model_registry_coverage = $modelRegistryCoverage
  ec2_static_proof = $staticProof
  result = $readinessResult
  failure_category = $readinessFailureCategory
  local_pre_ec2_ready = $localPreEc2Ready
  ready_for_ec2_static_proof = $readyForEc2StaticProof
  ready_for_generation = $readyForGeneration
  errors = $errors
  warnings = $warnings
  next_action = $(if (!$auth.safe_to_start_ec2) { "Complete AWS remote browser login and rerun Test-AwsAuthGate.ps1." } elseif (!$modelRegistryCoverage.coverage_allows_selected_lane_ec2_static_proof) { "Rerun Test-WorkflowModelRegistryCoverage.ps1 and inspect registry/queue coverage before EC2 static proof." } elseif (!$staticProof.generation_allowed) { "Run Invoke-EC2LaneStaticProof.ps1 -Execute and record object-info/path/hash proof." } else { "Run Invoke-ComfyWorkflowSmoke.ps1 -Execute, pull back artifacts, create PULLBACK_RECORD.json, then perform image QA." })
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
