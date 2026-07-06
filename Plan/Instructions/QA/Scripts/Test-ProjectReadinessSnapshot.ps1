<#
.SYNOPSIS
Creates a local-only project readiness snapshot for the selected ComfyUI lane.

.DESCRIPTION
This helper consolidates the current local project, validation, index, and
runtime-gate evidence into one machine-readable record. It does not contact
AWS, Civitai, GitHub APIs, ComfyUI, or EC2. AWS auth/runtime blockers are
reported as gate status, not treated as local validation failures.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LaneId = "sdxl_low_risk_fallback_lane",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Get-RelativePathCompat {
  param(
    [string]$BasePath,
    [string]$TargetPath
  )

  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }
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

function Has-Property {
  param(
    [object]$Object,
    [string]$Name
  )

  if ($null -eq $Object) { return $false }
  return $null -ne ($Object.PSObject.Properties[$Name])
}

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)

  if (!(Test-Path -LiteralPath $Path)) { throw "JSON file missing: $Path" }
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Find-LatestFile {
  param(
    [Parameter(Mandatory=$true)][string]$Directory,
    [Parameter(Mandatory=$true)][string]$Filter,
    [string]$ExcludePattern = ""
  )

  if (!(Test-Path -LiteralPath $Directory)) { return $null }
  $files = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File
  if (![string]::IsNullOrWhiteSpace($ExcludePattern)) {
    $files = $files | Where-Object { $_.Name -notmatch $ExcludePattern }
  }
  $latest = $files | Sort-Object LastWriteTime -Descending | Select-Object -First 1
  if ($null -eq $latest) { return $null }
  return $latest.FullName
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
  return $false
}

function Find-LatestJsonByLaneId {
  param(
    [Parameter(Mandatory=$true)][string]$Directory,
    [Parameter(Mandatory=$true)][string]$Filter,
    [Parameter(Mandatory=$true)][string]$ExpectedLaneId,
    [string]$ExcludePattern = ""
  )

  if (!(Test-Path -LiteralPath $Directory)) { return $null }
  $files = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File
  if (![string]::IsNullOrWhiteSpace($ExcludePattern)) {
    $files = $files | Where-Object { $_.Name -notmatch $ExcludePattern }
  }
  foreach ($file in @($files | Sort-Object LastWriteTime -Descending)) {
    try {
      $payload = Read-JsonFile -Path $file.FullName
      if (Test-JsonMatchesLane -Payload $payload -ExpectedLaneId $ExpectedLaneId) {
        return $file.FullName
      }
    } catch {
      continue
    }
  }
  return $null
}

function Test-JsonEvidence {
  param(
    [string]$Name,
    [string]$Path,
    [string[]]$AcceptableResults = @()
  )

  $entry = [ordered]@{
    name = $Name
    path = $(if ([string]::IsNullOrWhiteSpace($Path)) { $null } else { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path })
    found = (![string]::IsNullOrWhiteSpace($Path) -and (Test-Path -LiteralPath $Path))
    json_valid = $false
    result = $null
    acceptable_result = $false
    error = $null
  }

  if (!$entry.found) {
    $entry.error = "Evidence file not found."
    return $entry
  }

  try {
    $payload = Read-JsonFile -Path $Path
    $entry.json_valid = $true
    if (Has-Property -Object $payload -Name "result") {
      $entry.result = [string]$payload.result
    }
    if ($AcceptableResults.Count -eq 0) {
      $entry.acceptable_result = $true
    } else {
      $entry.acceptable_result = @($AcceptableResults) -contains $entry.result
    }
  } catch {
    $entry.error = $_.Exception.Message
  }

  return $entry
}

function Test-PowerShellParser {
  param([Parameter(Mandatory=$true)][string]$Path)

  $tokens = $null
  $errors = $null
  [System.Management.Automation.Language.Parser]::ParseFile($Path, [ref]$tokens, [ref]$errors) > $null
  return [ordered]@{
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $Path
    exists = (Test-Path -LiteralPath $Path)
    parse_errors = $errors.Count
    result = $(if ($errors.Count -eq 0) { "pass" } else { "fail" })
    errors = @($errors | ForEach-Object { $_.Message })
  }
}

function Get-GeneratedIndexParity {
  param([Parameter(Mandatory=$true)][string]$GeneratedIndexDir)

  $pairs = @(
    @{ name = "plan"; csv = "plan_file_index.csv"; json = "plan_file_index.json" },
    @{ name = "instructions"; csv = "instructions_file_index.csv"; json = "instructions_file_index.json" },
    @{ name = "items"; csv = "items_file_index.csv"; json = "items_file_index.json" },
    @{ name = "tracker"; csv = "tracker_file_index.csv"; json = "tracker_file_index.json" }
  )

  $rows = @()
  foreach ($pair in $pairs) {
    $csvPath = Join-Path $GeneratedIndexDir $pair.csv
    $jsonPath = Join-Path $GeneratedIndexDir $pair.json
    $entry = [ordered]@{
      name = $pair.name
      csv_path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $csvPath
      json_path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $jsonPath
      csv_exists = (Test-Path -LiteralPath $csvPath)
      json_exists = (Test-Path -LiteralPath $jsonPath)
      csv_count = $null
      json_count = $null
      row_count_match = $false
      result = "fail"
      error = $null
    }
    try {
      if (!$entry.csv_exists -or !$entry.json_exists) {
        throw "Generated index pair is missing."
      }
      $csv = Import-Csv -LiteralPath $csvPath
      $json = Get-Content -LiteralPath $jsonPath -Raw | ConvertFrom-Json
      $entry.csv_count = @($csv).Count
      $entry.json_count = @($json).Count
      $entry.row_count_match = ($entry.csv_count -eq $entry.json_count)
      $entry.result = $(if ($entry.row_count_match) { "pass" } else { "fail" })
    } catch {
      $entry.error = $_.Exception.Message
    }
    $rows += $entry
  }

  return $rows
}

function Get-SecretScanSummary {
  param([Parameter(Mandatory=$true)][string[]]$Paths)

  $privateTempPath = $(if (![string]::IsNullOrWhiteSpace($env:USERPROFILE)) { Join-Path $env:USERPROFILE "AppData\Local\Temp" } else { "" })
  $patterns = @(
    @{ label = "github_fine_grained_token"; regex = ("github" + "_pat_") },
    @{ label = "github_classic_token"; regex = ("g" + "hp_") },
    @{ label = "civitai_key_assignment"; regex = "CIVITAI_API_KEY\s*=" },
    @{ label = "aws_access_key_assignment"; regex = "AWS_ACCESS_KEY_ID\s*=" },
    @{ label = "aws_secret_key_assignment"; regex = "AWS_SECRET_ACCESS_KEY\s*=" },
    @{ label = "aws_session_token_assignment"; regex = "AWS_SESSION_TOKEN\s*=" },
    @{ label = "private_temp_path"; regex = $(if (![string]::IsNullOrWhiteSpace($privateTempPath)) { [regex]::Escape($privateTempPath) } else { "__PRIVATE_TEMP_PATH_PATTERN_UNAVAILABLE__" }) },
    @{ label = "aws_signin_url"; regex = "signin\.aws\.amazon\.com" },
    @{ label = "awsapps_url"; regex = "\.awsapps\.com" }
  )

  $files = @()
  foreach ($path in $Paths) {
    if (Test-Path -LiteralPath $path -PathType Container) {
      $files += Get-ChildItem -LiteralPath $path -File -Recurse | ForEach-Object { $_.FullName }
    } elseif (Test-Path -LiteralPath $path -PathType Leaf) {
      $files += $path
    }
  }

  $hits = @()
  foreach ($file in ($files | Sort-Object -Unique)) {
    $text = Get-Content -LiteralPath $file -Raw
    foreach ($pattern in $patterns) {
      if ([regex]::IsMatch($text, $pattern.regex)) {
        $hits += [ordered]@{
          file = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $file
          rule = $pattern.label
        }
      }
    }
  }

  return [ordered]@{
    scanned_file_count = @($files | Sort-Object -Unique).Count
    hit_count = @($hits).Count
    hits = $hits
    result = $(if (@($hits).Count -eq 0) { "pass" } else { "fail" })
  }
}

function Get-GitSummary {
  $summary = [ordered]@{
    git_root = $null
    head = $null
    origin_main = $null
    local_matches_origin = $false
    porcelain_count = $null
    clean = $false
    remote = $null
    result = "unknown"
    error = $null
  }

  try {
    Push-Location $ProjectRoot
    try {
      $summary.git_root = ((git rev-parse --show-toplevel 2>$null) | Select-Object -First 1)
      $summary.head = ((git rev-parse HEAD 2>$null) | Select-Object -First 1)
      $summary.origin_main = ((git rev-parse origin/main 2>$null) | Select-Object -First 1)
      $summary.local_matches_origin = (![string]::IsNullOrWhiteSpace($summary.head) -and $summary.head -eq $summary.origin_main)
      $porcelain = @(git status --porcelain 2>$null)
      $summary.porcelain_count = $porcelain.Count
      $summary.clean = ($porcelain.Count -eq 0)
      $remoteLines = @(git remote -v 2>$null)
      $summary.remote = (($remoteLines | Where-Object { $_ -match "^origin\s+" }) | Select-Object -First 1)
      $summary.result = $(if (![string]::IsNullOrWhiteSpace($summary.git_root) -and $summary.local_matches_origin) { "pass" } else { "fail" })
    } finally {
      Pop-Location
    }
  } catch {
    $summary.error = $_.Exception.Message
    $summary.result = "fail"
  }

  return $summary
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")

$qaEvidenceRoot = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence"
$runtimeReadinessDir = Join-Path $qaEvidenceRoot "Runtime_Readiness"
$workflowStaticDir = Join-Path $qaEvidenceRoot "Workflow_Static_Validation"
$workflowRuntimeDir = Join-Path $qaEvidenceRoot "Workflow_Runtime"
$operationsValidationDir = Join-Path $qaEvidenceRoot "Operations_Static_Validation"
$qaValidationDir = Join-Path $qaEvidenceRoot "QA_Helper_Static_Validation"
$hydrationValidationDir = Join-Path $qaEvidenceRoot "Hydration_Helper_Static_Validation"
$itemsTrackerValidationDir = Join-Path $qaEvidenceRoot "Items_Tracker_Validation"
$indexValidationDir = Join-Path $qaEvidenceRoot "Index_Validation"
$generatedIndexDir = Join-Path $ProjectRoot "Plan\Instructions\Indexes\Generated"
$laneDir = Join-Path $ProjectRoot "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\$LaneId"

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $qaEvidenceRoot "Project_Readiness\W61_PROJECT_READINESS_SNAPSHOT_$stamp.json"
}

$latest = [ordered]@{
  auth_gate = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W60_W61_AWS_AUTH_GATE_*.json"
  profile_matrix = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W60_W61_AWS_PROFILE_AUTH_MATRIX_*.json"
  lane_readiness = Find-LatestJsonByLaneId -Directory $runtimeReadinessDir -Filter "W61_LANE_RUNTIME_READINESS_*.json" -ExpectedLaneId $LaneId
  runtime_unblock_handoff = Find-LatestJsonByLaneId -Directory $runtimeReadinessDir -Filter "W61_RUNTIME_UNBLOCK_HANDOFF_*.json" -ExpectedLaneId $LaneId
  ec2_static_proof_blocked = Find-LatestJsonByLaneId -Directory $workflowStaticDir -Filter "W61_EC2_LANE_STATIC_PROOF_BLOCKED_EXECUTE_*.json" -ExpectedLaneId $LaneId
  ec2_workflow_smoke_blocked = Find-LatestJsonByLaneId -Directory $workflowRuntimeDir -Filter "W61_EC2_WORKFLOW_SMOKE_RUN_BLOCKED_EXECUTE_*.json" -ExpectedLaneId $LaneId
  operations_validation = Find-LatestFile -Directory $operationsValidationDir -Filter "W60_OPERATIONS_HELPER_CURRENT_VALIDATION*.json"
  qa_validation = Find-LatestFile -Directory $qaValidationDir -Filter "W61_QA_HELPER_CURRENT_VALIDATION*.json"
  hydration_validation = Find-LatestFile -Directory $hydrationValidationDir -Filter "W62_HYDRATION_HELPER_CURRENT_VALIDATION*.json"
  items_tracker_validation = Find-LatestFile -Directory $itemsTrackerValidationDir -Filter "W59_W60_ITEMS_TRACKER_CURRENT_VALIDATION*.json"
  index_validation = Find-LatestFile -Directory $indexValidationDir -Filter "W59_LIVE_INDEX_REFRESH*.json"
}

$errors = @()
$warnings = @()

$laneFiles = @()
foreach ($fileName in @("workflow.api.json", "patch_points.json", "runtime_requirements.json", "smoke_test_request.json")) {
  $path = Join-Path $laneDir $fileName
  $entry = [ordered]@{
    name = $fileName
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $path
    exists = (Test-Path -LiteralPath $path)
    json_valid = $false
    result = "fail"
    error = $null
  }
  if ($entry.exists) {
    try {
      $null = Read-JsonFile -Path $path
      $entry.json_valid = $true
      $entry.result = "pass"
    } catch {
      $entry.error = $_.Exception.Message
    }
  } else {
    $entry.error = "Lane file missing."
  }
  if ($entry.result -ne "pass") { $errors += "Lane file check failed: $($entry.path)" }
  $laneFiles += $entry
}

$snapshotScript = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-ProjectReadinessSnapshot.ps1"
$snapshotScriptParse = Test-PowerShellParser -Path $snapshotScript
if ($snapshotScriptParse.result -ne "pass") { $errors += "Project readiness snapshot helper does not parse." }

$evidenceChecks = @(
  (Test-JsonEvidence -Name "operations_validation" -Path $latest.operations_validation -AcceptableResults @("pass_local_only")),
  (Test-JsonEvidence -Name "qa_validation" -Path $latest.qa_validation -AcceptableResults @("pass_local_only")),
  (Test-JsonEvidence -Name "hydration_validation" -Path $latest.hydration_validation -AcceptableResults @("pass_local_only")),
  (Test-JsonEvidence -Name "items_tracker_validation" -Path $latest.items_tracker_validation -AcceptableResults @("pass", "pass_local_only")),
  (Test-JsonEvidence -Name "index_validation" -Path $latest.index_validation -AcceptableResults @("pass")),
  (Test-JsonEvidence -Name "auth_gate" -Path $latest.auth_gate -AcceptableResults @("pass", "blocked_expired_session", "blocked_account_mismatch", "blocked_aws_cli_unavailable", "blocked_remote_login_required", "blocked_unknown_auth_state")),
  (Test-JsonEvidence -Name "profile_matrix" -Path $latest.profile_matrix -AcceptableResults @("pass", "blocked_no_valid_profile", "blocked_aws_cli_unavailable", "blocked_no_profiles")),
  (Test-JsonEvidence -Name "lane_readiness" -Path $latest.lane_readiness -AcceptableResults @("ready_for_generation", "ready_for_ec2_static_proof", "local_pre_ec2_ready_runtime_blocked_auth", "local_pre_ec2_ready_runtime_blocked")),
  (Test-JsonEvidence -Name "runtime_unblock_handoff" -Path $latest.runtime_unblock_handoff -AcceptableResults @("handoff_ready_runtime_blocked_auth", "handoff_auth_ready_lane_not_ready", "handoff_ready_for_ec2_static_proof", "handoff_ready_for_generation")),
  (Test-JsonEvidence -Name "ec2_static_proof_blocked_execute" -Path $latest.ec2_static_proof_blocked -AcceptableResults @("blocked_before_ec2_start")),
  (Test-JsonEvidence -Name "ec2_workflow_smoke_blocked_execute" -Path $latest.ec2_workflow_smoke_blocked -AcceptableResults @("blocked_before_ec2_start"))
)

foreach ($check in $evidenceChecks) {
  if (!$check.found -or !$check.json_valid -or !$check.acceptable_result) {
    $errors += "Evidence check failed: $($check.name)"
  }
}

$authSummary = [ordered]@{
  result = "missing_auth_gate"
  failure_category = "missing_auth_gate"
  account_match = $false
  remote_login_status = "missing_auth_gate"
  ec2_work_allowed = $false
  safe_to_start_ec2 = $false
  generation_allowed = $false
}
if (![string]::IsNullOrWhiteSpace($latest.auth_gate) -and (Test-Path -LiteralPath $latest.auth_gate)) {
  $authJson = Read-JsonFile -Path $latest.auth_gate
  foreach ($name in @("result", "failure_category", "remote_login_status")) {
    if (Has-Property -Object $authJson -Name $name) { $authSummary[$name] = [string]$authJson.$name }
  }
  foreach ($name in @("account_match", "ec2_work_allowed", "safe_to_start_ec2", "generation_allowed")) {
    if (Has-Property -Object $authJson -Name $name) { $authSummary[$name] = [bool]$authJson.$name }
  }
}

$profileSummary = [ordered]@{
  expected_account = $null
  profile_count = 0
  profiles_matching_expected_count = 0
  safe_to_start_ec2 = $false
  result = "missing_profile_matrix"
}
if (![string]::IsNullOrWhiteSpace($latest.profile_matrix) -and (Test-Path -LiteralPath $latest.profile_matrix)) {
  $profileJson = Read-JsonFile -Path $latest.profile_matrix
  foreach ($name in @("expected_account", "result")) {
    if (Has-Property -Object $profileJson -Name $name) { $profileSummary[$name] = [string]$profileJson.$name }
  }
  foreach ($name in @("profile_count", "profiles_matching_expected_count")) {
    if (Has-Property -Object $profileJson -Name $name) { $profileSummary[$name] = [int]$profileJson.$name }
  }
  if (Has-Property -Object $profileJson -Name "safe_to_start_ec2") {
    $profileSummary.safe_to_start_ec2 = [bool]$profileJson.safe_to_start_ec2
  }
}

$laneReadinessSummary = [ordered]@{
  result = "missing_lane_readiness"
  failure_category = "missing_lane_readiness"
  lane_id = $null
  lane_match = $false
  local_pre_ec2_ready = $false
  ready_for_ec2_static_proof = $false
  ready_for_generation = $false
}
if (![string]::IsNullOrWhiteSpace($latest.lane_readiness) -and (Test-Path -LiteralPath $latest.lane_readiness)) {
  $readinessJson = Read-JsonFile -Path $latest.lane_readiness
  if (Has-Property -Object $readinessJson -Name "lane_id") {
    $laneReadinessSummary.lane_id = [string]$readinessJson.lane_id
  }
  $laneReadinessSummary.lane_match = ([string]$laneReadinessSummary.lane_id -eq [string]$LaneId)
  foreach ($name in @("result", "failure_category")) {
    if (Has-Property -Object $readinessJson -Name $name) { $laneReadinessSummary[$name] = [string]$readinessJson.$name }
  }
  foreach ($name in @("local_pre_ec2_ready", "ready_for_ec2_static_proof", "ready_for_generation")) {
    if (Has-Property -Object $readinessJson -Name $name) { $laneReadinessSummary[$name] = [bool]$readinessJson.$name }
  }
}

$runtimeHandoffSummary = [ordered]@{
  result = "missing_runtime_unblock_handoff"
  failure_category = "missing_runtime_unblock_handoff"
  next_required_action = "missing_runtime_unblock_handoff"
  lane_id = $null
  lane_match = $false
  local_only = $false
  aws_contacted = $true
  github_api_contacted = $true
  civitai_contacted = $true
  ec2_started = $true
  generation_executed = $true
  command_step_count = 0
  markdown_path = $null
  markdown_written = $false
}
if (![string]::IsNullOrWhiteSpace($latest.runtime_unblock_handoff) -and (Test-Path -LiteralPath $latest.runtime_unblock_handoff)) {
  $handoffJson = Read-JsonFile -Path $latest.runtime_unblock_handoff
  if (Has-Property -Object $handoffJson -Name "lane_id") {
    $runtimeHandoffSummary.lane_id = [string]$handoffJson.lane_id
  }
  $runtimeHandoffSummary.lane_match = ([string]$runtimeHandoffSummary.lane_id -eq [string]$LaneId)
  foreach ($name in @("result", "failure_category", "next_required_action", "markdown_path")) {
    if (Has-Property -Object $handoffJson -Name $name) { $runtimeHandoffSummary[$name] = [string]$handoffJson.$name }
  }
  foreach ($name in @("local_only", "aws_contacted", "github_api_contacted", "civitai_contacted", "ec2_started", "generation_executed", "markdown_written")) {
    if (Has-Property -Object $handoffJson -Name $name) { $runtimeHandoffSummary[$name] = [bool]$handoffJson.$name }
  }
  if (Has-Property -Object $handoffJson -Name "command_step_count") {
    $runtimeHandoffSummary.command_step_count = [int]$handoffJson.command_step_count
  } elseif (Has-Property -Object $handoffJson -Name "command_sequence") {
    $runtimeHandoffSummary.command_step_count = @($handoffJson.command_sequence).Count
  }
}

if ($laneReadinessSummary.lane_match -ne $true) {
  $errors += "Lane readiness evidence does not match selected LaneId $LaneId."
}
if ($runtimeHandoffSummary.local_only -ne $true) {
  $errors += "Runtime unblock handoff is not marked local-only."
}
if ($runtimeHandoffSummary.lane_match -ne $true) {
  $errors += "Runtime unblock handoff does not match selected LaneId $LaneId."
}
if ($runtimeHandoffSummary.aws_contacted -ne $false -or $runtimeHandoffSummary.github_api_contacted -ne $false -or $runtimeHandoffSummary.civitai_contacted -ne $false) {
  $errors += "Runtime unblock handoff unexpectedly contacted an external service."
}
if ($runtimeHandoffSummary.ec2_started -ne $false) {
  $errors += "Runtime unblock handoff unexpectedly started EC2."
}
if ($runtimeHandoffSummary.generation_executed -ne $false) {
  $errors += "Runtime unblock handoff unexpectedly executed generation."
}
if ($runtimeHandoffSummary.command_step_count -lt 8) {
  $errors += "Runtime unblock handoff command sequence is incomplete."
}
if ($runtimeHandoffSummary.markdown_written -ne $true) {
  $errors += "Runtime unblock handoff markdown record was not written."
}

$coordinatorSummary = [ordered]@{
  static_proof_result = "missing"
  static_proof_failure_category = "missing"
  static_proof_ec2_started = $null
  workflow_smoke_result = "missing"
  workflow_smoke_failure_category = "missing"
  workflow_smoke_ec2_started = $null
  workflow_smoke_generation_executed = $null
  blocked_execute_records_safe = $false
}
if (![string]::IsNullOrWhiteSpace($latest.ec2_static_proof_blocked) -and (Test-Path -LiteralPath $latest.ec2_static_proof_blocked)) {
  $staticBlocked = Read-JsonFile -Path $latest.ec2_static_proof_blocked
  if (Has-Property -Object $staticBlocked -Name "result") { $coordinatorSummary.static_proof_result = [string]$staticBlocked.result }
  if (Has-Property -Object $staticBlocked -Name "failure_category") { $coordinatorSummary.static_proof_failure_category = [string]$staticBlocked.failure_category }
  if (Has-Property -Object $staticBlocked -Name "ec2_started") { $coordinatorSummary.static_proof_ec2_started = [bool]$staticBlocked.ec2_started }
}
if (![string]::IsNullOrWhiteSpace($latest.ec2_workflow_smoke_blocked) -and (Test-Path -LiteralPath $latest.ec2_workflow_smoke_blocked)) {
  $workflowBlocked = Read-JsonFile -Path $latest.ec2_workflow_smoke_blocked
  if (Has-Property -Object $workflowBlocked -Name "result") { $coordinatorSummary.workflow_smoke_result = [string]$workflowBlocked.result }
  if (Has-Property -Object $workflowBlocked -Name "failure_category") { $coordinatorSummary.workflow_smoke_failure_category = [string]$workflowBlocked.failure_category }
  if (Has-Property -Object $workflowBlocked -Name "ec2_started") { $coordinatorSummary.workflow_smoke_ec2_started = [bool]$workflowBlocked.ec2_started }
  if (Has-Property -Object $workflowBlocked -Name "generation_executed") { $coordinatorSummary.workflow_smoke_generation_executed = [bool]$workflowBlocked.generation_executed }
}
$coordinatorSummary.blocked_execute_records_safe = (
  $coordinatorSummary.static_proof_result -eq "blocked_before_ec2_start" -and
  $coordinatorSummary.static_proof_ec2_started -eq $false -and
  $coordinatorSummary.workflow_smoke_result -eq "blocked_before_ec2_start" -and
  $coordinatorSummary.workflow_smoke_ec2_started -eq $false -and
  $coordinatorSummary.workflow_smoke_generation_executed -eq $false
)
if (!$coordinatorSummary.blocked_execute_records_safe) {
  $errors += "Blocked coordinator safety evidence is not complete."
}

$generatedIndexParity = Get-GeneratedIndexParity -GeneratedIndexDir $generatedIndexDir
if (@($generatedIndexParity | Where-Object { $_.result -ne "pass" }).Count -gt 0) {
  $errors += "Generated index row-count parity failed."
}

$secretScan = Get-SecretScanSummary -Paths @(
  $generatedIndexDir,
  (Join-Path $ProjectRoot "Plan\Instructions\Hydration_Rehydration"),
  $qaEvidenceRoot
)
if ($secretScan.result -ne "pass") {
  $errors += "Secret/private path scan found matches."
}

$gitSummary = Get-GitSummary
if ($gitSummary.result -ne "pass") {
  $errors += "Git root or local/origin alignment check failed."
}
if (!$gitSummary.clean) {
  $warnings += "Git working tree has pending local changes; this is expected while creating the current snapshot checkpoint."
}

if (!$authSummary.safe_to_start_ec2) {
  $warnings += "AWS auth gate does not allow EC2 start."
}
if (!$laneReadinessSummary.ready_for_ec2_static_proof) {
  $warnings += "Selected lane is not ready for EC2 static proof until runtime gates change."
}
if (!$laneReadinessSummary.ready_for_generation) {
  $warnings += "Generation remains blocked until EC2 object-info/path/hash proof exists."
}

$localReady = (
  $errors.Count -eq 0 -and
  (@($laneFiles | Where-Object { $_.result -ne "pass" }).Count -eq 0) -and
  (@($evidenceChecks | Where-Object { !$_.found -or !$_.json_valid -or !$_.acceptable_result }).Count -eq 0) -and
  (@($generatedIndexParity | Where-Object { $_.result -ne "pass" }).Count -eq 0) -and
  $secretScan.result -eq "pass"
)

$ec2StartAllowed = ($authSummary.safe_to_start_ec2 -and $laneReadinessSummary.ready_for_ec2_static_proof)
$generationAllowed = ($ec2StartAllowed -and $laneReadinessSummary.ready_for_generation)

$result = "fail"
$failureCategory = $null
if ($localReady -and $generationAllowed) {
  $result = "pass_ready_for_generation"
} elseif ($localReady -and $ec2StartAllowed) {
  $result = "pass_local_ready_for_ec2_static_proof"
  $failureCategory = "missing_ec2_static_proof"
} elseif ($localReady -and !$authSummary.safe_to_start_ec2) {
  $result = "pass_local_ready_runtime_blocked_auth"
  $failureCategory = $(if (![string]::IsNullOrWhiteSpace([string]$authSummary.failure_category)) { [string]$authSummary.failure_category } else { "aws_auth_blocked" })
} elseif ($localReady) {
  $result = "pass_local_ready_runtime_blocked"
  $failureCategory = $(if (![string]::IsNullOrWhiteSpace([string]$laneReadinessSummary.failure_category)) { [string]$laneReadinessSummary.failure_category } else { "runtime_gate_blocked" })
} else {
  $failureCategory = "local_project_readiness_failed"
}

$record = [ordered]@{
  evidence_id = "W61-PROJECT-READINESS-SNAPSHOT-$stamp"
  created_at = $createdAt
  artifact_id = "TRK-W61-006"
  artifact_type = "project_readiness_snapshot"
  tracker_ids = @("TRK-W61-006", "TRK-W61-007", "TRK-W61-011", "TRK-W60-010", "TRK-W59-002", "TRK-W59-003")
  item_ids = @("ITEM-W61-006", "ITEM-W61-007", "ITEM-W61-011", "ITEM-W60-010")
  qa_protocol_used = @(
    "README_QA_WAVE61.md",
    "COMFYUI_WORKFLOW_TESTING_PROTOCOL.md",
    "DONE_CERTIFICATION_EVIDENCE_PROTOCOL.md",
    "QA_EVIDENCE_LOG_PROTOCOL.md"
  )
  scope = @(
    "selected SDXL lane local files",
    "latest local helper validation evidence",
    "latest generated index parity",
    "latest auth/readiness/profile/coordinator gate evidence",
    "latest runtime unblock handoff evidence",
    "secret/private path scan over generated indexes, hydration, and QA evidence"
  )
  lane_id = $LaneId
  lane_dir = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $laneDir
  git = $gitSummary
  lane_files = $laneFiles
  helper_self_parse = $snapshotScriptParse
  latest_evidence_inputs = [ordered]@{
    auth_gate = $(if ($latest.auth_gate) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.auth_gate } else { $null })
    profile_matrix = $(if ($latest.profile_matrix) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.profile_matrix } else { $null })
    lane_readiness = $(if ($latest.lane_readiness) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.lane_readiness } else { $null })
    runtime_unblock_handoff = $(if ($latest.runtime_unblock_handoff) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.runtime_unblock_handoff } else { $null })
    ec2_static_proof_blocked = $(if ($latest.ec2_static_proof_blocked) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.ec2_static_proof_blocked } else { $null })
    ec2_workflow_smoke_blocked = $(if ($latest.ec2_workflow_smoke_blocked) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.ec2_workflow_smoke_blocked } else { $null })
    operations_validation = $(if ($latest.operations_validation) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.operations_validation } else { $null })
    qa_validation = $(if ($latest.qa_validation) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.qa_validation } else { $null })
    hydration_validation = $(if ($latest.hydration_validation) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.hydration_validation } else { $null })
    items_tracker_validation = $(if ($latest.items_tracker_validation) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.items_tracker_validation } else { $null })
    index_validation = $(if ($latest.index_validation) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.index_validation } else { $null })
  }
  evidence_checks = $evidenceChecks
  generated_index_parity = $generatedIndexParity
  secret_private_path_scan = $secretScan
  runtime_gates = [ordered]@{
    auth_gate = $authSummary
    profile_matrix = $profileSummary
    lane_readiness = $laneReadinessSummary
    runtime_unblock_handoff = $runtimeHandoffSummary
    coordinator_safety = $coordinatorSummary
    ec2_start_allowed = $ec2StartAllowed
    generation_allowed = $generationAllowed
  }
  local_ready = $localReady
  result = $result
  failure_category = $failureCategory
  errors = $errors
  warnings = $warnings
  known_issues = @(
    "AWS auth remains a runtime gate if safe_to_start_ec2 is false.",
    "This snapshot does not claim EC2 object-info/path/hash proof, ComfyUI generation, artifact pullback, image QA, video QA, audio QA, or final project completion.",
    "A dirty Git working tree during snapshot creation is recorded as a warning and resolved by the guarded checkpoint workflow."
  )
  next_action = $(if (!$authSummary.safe_to_start_ec2) { "Complete AWS browser/SSO login, rerun Test-AwsAuthGate.ps1, then rerun selected-lane readiness before EC2 static proof." } elseif (!$laneReadinessSummary.ready_for_ec2_static_proof) { "Rerun selected-lane readiness and inspect the blocking gate before EC2 static proof." } elseif (!$laneReadinessSummary.ready_for_generation) { "Run Invoke-EC2LaneStaticProof.ps1 -Execute to record object-info/path/hash proof." } else { "Run Invoke-EC2WorkflowSmokeRun.ps1 -Execute, pull back artifacts, then perform image QA." })
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
$record | ConvertTo-Json -Depth 40 | Set-Content -LiteralPath $OutFile -Encoding UTF8
Write-Host "Wrote project readiness snapshot: $OutFile"
$record | ConvertTo-Json -Depth 40

if ($record.result -eq "fail") { exit 2 }
