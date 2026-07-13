<#
.SYNOPSIS
Creates a local-only Normal target-runtime window intent contract.

.DESCRIPTION
Generates a unique runtime-window identifier and binds future Row042 schedule
and watchdog evidence to it. This helper has no execute mode. It never contacts
AWS, mutates the queue, starts EC2, sends SSM, or runs generation.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$CandidateReadinessFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W64_NORMAL_TARGET_RUNTIME_CANDIDATE_LOCAL_READINESS_20260713T103230-0500.json",
  [string]$RuntimeLaneQueueFile = "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\runtime_lane_queue.json",
  [string]$TtlWatchdogEvidenceFile = "Plan\Instructions\QA\Evidence\Wave64\ec2_ttl_watchdog.json",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$laneId = "sdxl_realvisxl_controlnet_normal_lane"
$trackerId = "TRK-W64-042"
$itemId = "ITEM-W64-042"

function Resolve-ProjectContainedPath {
  param([Parameter(Mandatory=$true)][string]$Path)
  $root = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/")
  $candidate = if ([System.IO.Path]::IsPathRooted($Path)) {
    [System.IO.Path]::GetFullPath($Path)
  } else {
    [System.IO.Path]::GetFullPath((Join-Path $root $Path))
  }
  $prefix = $root + [System.IO.Path]::DirectorySeparatorChar
  if (!$candidate.StartsWith($prefix, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Path is outside ProjectRoot: $Path"
  }
  return $candidate
}

function ConvertTo-ProjectRelativePath {
  param([Parameter(Mandatory=$true)][string]$Path)
  $root = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/") + [System.IO.Path]::DirectorySeparatorChar
  $resolved = [System.IO.Path]::GetFullPath($Path)
  return $resolved.Substring($root.Length).Replace("\", "/")
}

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function Has-Property {
  param([object]$Object, [string]$Name)
  return $null -ne $Object -and $null -ne $Object.PSObject.Properties[$Name]
}

function New-Check {
  param([string]$Name, [bool]$Passed, [object]$Observed, [object]$Expected)
  return [pscustomobject][ordered]@{
    name = $Name
    result = $(if ($Passed) { "pass" } else { "fail" })
    observed = $Observed
    expected = $Expected
  }
}

function Write-JsonNoBom {
  param([Parameter(Mandatory=$true)][string]$Path, [Parameter(Mandatory=$true)][object]$Payload)
  [System.IO.Directory]::CreateDirectory((Split-Path -Parent $Path)) | Out-Null
  [System.IO.File]::WriteAllText($Path, ($Payload | ConvertTo-Json -Depth 30) + [Environment]::NewLine, (New-Object System.Text.UTF8Encoding($false)))
}

$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$runtimeWindowId = "rw-normal-{0}-{1}" -f $stamp, ([guid]::NewGuid().ToString("N").Substring(0, 8))
$errors = @()
$failureCategories = @()
$checks = @()
$candidate = $null
$queue = $null
$ttl = $null
$inputRecords = @()

$inputSpecs = @(
  [pscustomobject]@{ name = "candidate_readiness"; supplied = $CandidateReadinessFile },
  [pscustomobject]@{ name = "runtime_lane_queue"; supplied = $RuntimeLaneQueueFile },
  [pscustomobject]@{ name = "ttl_watchdog_evidence"; supplied = $TtlWatchdogEvidenceFile }
)
foreach ($spec in $inputSpecs) {
  $record = [ordered]@{ name = $spec.name; path = $null; found = $false; json_valid = $false; sha256 = $null }
  try {
    $resolved = Resolve-ProjectContainedPath -Path ([string]$spec.supplied)
    $record.path = ConvertTo-ProjectRelativePath -Path $resolved
    $record.found = Test-Path -LiteralPath $resolved -PathType Leaf
    if (!$record.found) { throw "Required input missing: $($spec.name)" }
    $payload = Read-JsonFile -Path $resolved
    $record.json_valid = $true
    $record.sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $resolved).Hash.ToLowerInvariant()
    if ($spec.name -eq "candidate_readiness") { $candidate = $payload }
    elseif ($spec.name -eq "runtime_lane_queue") { $queue = $payload }
    else { $ttl = $payload }
  } catch {
    $errors += $_.Exception.Message
    $failureCategories += $(if ($_.Exception.Message -match "JSON|convert") { "invalid_json" } else { "missing_required_input" })
  }
  $inputRecords += $record
}

if ($runtimeWindowId -notmatch '^rw-normal-[0-9]{8}T[0-9]{6}[+-][0-9]{4}-[0-9a-f]{8}$') {
  $errors += "Generated runtime_window_id is invalid."
  $failureCategories += "runtime_window_id_generation_failed"
}

if ($null -ne $candidate) {
  $checks += New-Check "candidate_classification" ([string]$candidate.classification -ceq "NORMAL_TARGET_RUNTIME_CANDIDATE_LOCAL_READINESS_PASS_QUEUE_NOT_SELECTED") $candidate.classification "NORMAL_TARGET_RUNTIME_CANDIDATE_LOCAL_READINESS_PASS_QUEUE_NOT_SELECTED"
  $checks += New-Check "candidate_lane" ([string]$candidate.lane_id -ceq $laneId) $candidate.lane_id $laneId
  $checks += New-Check "candidate_window_selected" ([bool]$candidate.candidate_selected_for_next_bounded_runtime_window) $candidate.candidate_selected_for_next_bounded_runtime_window $true
  $checks += New-Check "candidate_local_static_ready" ([bool]$candidate.local_readiness.ready_for_ec2_static_proof) $candidate.local_readiness.ready_for_ec2_static_proof $true
  $checks += New-Check "candidate_generation_still_blocked" (-not [bool]$candidate.local_readiness.ready_for_generation) $candidate.local_readiness.ready_for_generation $false
}
if ($null -ne $queue) {
  $candidateRows = @($queue.lanes | Where-Object { [string]$_.lane_id -ceq $laneId })
  $checks += New-Check "queue_candidate_cardinality" ($candidateRows.Count -eq 1) $candidateRows.Count 1
  $checks += New-Check "queue_boundary_present" (Has-Property $queue "runtime_boundary") (Has-Property $queue "runtime_boundary") $true
  $checks += New-Check "queue_selection_policy_present" (Has-Property $queue "selection_policy") (Has-Property $queue "selection_policy") $true
}
if ($null -ne $ttl) {
  $ttlBlockers = @($ttl.live_readiness.blockers | ForEach-Object { [string]$_ })
  $checks += New-Check "ttl_tracker_id" ([string]$ttl.tracker_id -ceq $trackerId) $ttl.tracker_id $trackerId
  $checks += New-Check "ttl_item_id" ([string]$ttl.item_id -ceq $itemId) $ttl.item_id $itemId
  $checks += New-Check "ttl_row_fail_closed" (-not [bool]$ttl.row_complete) $ttl.row_complete $false
  $checks += New-Check "ttl_schedule_missing" (-not [bool]$ttl.live_readiness.live_schedule_present -and $ttlBlockers -contains "live_emergency_stop_schedule_missing") $ttl.live_readiness.live_schedule_present $false
  $checks += New-Check "ttl_watchdog_missing" (-not [bool]$ttl.live_readiness.watchdog_proof_present -and $ttlBlockers -contains "ssm_watchdog_proof_missing") $ttl.live_readiness.watchdog_proof_present $false
}

$failedChecks = @($checks | Where-Object { [string]$_.result -eq "fail" })
foreach ($check in $failedChecks) {
  $errors += "Structural check failed: $($check.name)"
  if ($check.name -eq "candidate_lane") { $failureCategories += "candidate_lane_mismatch" }
  elseif ($check.name -eq "candidate_window_selected") { $failureCategories += "candidate_not_selected_for_runtime_window" }
  elseif ($check.name -like "ttl_tracker*" -or $check.name -like "ttl_item*") { $failureCategories += "ttl_watchdog_tracker_item_mismatch" }
  elseif ($check.name -like "ttl_*") { $failureCategories += "ttl_watchdog_binding_evidence_missing" }
  else { $failureCategories += "contract_internal_consistency_failed" }
}

$structurallyValid = ($errors.Count -eq 0 -and $checks.Count -ge 12)
$queueCurrentLane = if ($null -ne $queue -and (Has-Property $queue "selection_policy")) { [string]$queue.selection_policy.current_runtime_lane_id } else { "" }
$queueEc2Allowed = if ($null -ne $queue -and (Has-Property $queue "runtime_boundary")) { [bool]$queue.runtime_boundary.ec2_start_allowed_by_queue_file } else { $false }
$queueGenerationAllowed = if ($null -ne $queue -and (Has-Property $queue "runtime_boundary")) { [bool]$queue.runtime_boundary.generation_allowed_by_queue_file } else { $false }
$exactBlockers = @()
if ($queueCurrentLane -cne $laneId) { $exactBlockers += "queue_lane_not_selected" }
if (!$queueEc2Allowed -or !$queueGenerationAllowed) { $exactBlockers += "queue_permission_denied_by_file" }
if ($null -ne $ttl -and -not [bool]$ttl.live_readiness.live_schedule_present) { $exactBlockers += "live_emergency_stop_schedule_missing" }
if ($null -ne $ttl -and -not [bool]$ttl.live_readiness.watchdog_proof_present) { $exactBlockers += "ssm_watchdog_proof_missing" }
if (!$structurallyValid) { $exactBlockers += "contract_internal_consistency_failed" }
$exactBlockers = @($exactBlockers | Select-Object -Unique)

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "normal_runtime_window_contract"
  created_at = $createdAt
  result = $(if ($structurallyValid) { "blocked_normal_runtime_window_contract_waiting_for_queue_and_live_controls" } else { "invalid_normal_runtime_window_contract" })
  failure_category = $(if ($structurallyValid) { "queue_and_live_controls_not_authorized" } else { (@($failureCategories | Select-Object -Unique) -join ";") })
  structural_consistency_valid = $structurallyValid
  contract_valid = $false
  execution_authorized = $false
  authority_semantics = "contract_valid and execution_authorized are always false; structural_consistency_valid means only that this local blocked-intent artifact is internally coherent."
  local_only = $true
  runtime_window_id = $runtimeWindowId
  lane_id = $laneId
  tracker_id = $trackerId
  item_id = $itemId
  schedule_binding_required = $true
  watchdog_binding_required = $true
  future_schedule_runtime_window_id = $runtimeWindowId
  future_watchdog_runtime_window_id = $runtimeWindowId
  authority_snapshot = [ordered]@{
    candidate_selected_for_next_bounded_runtime_window = $(if ($null -ne $candidate) { [bool]$candidate.candidate_selected_for_next_bounded_runtime_window } else { $false })
    queue_current_runtime_lane_id = $queueCurrentLane
    queue_ec2_start_allowed = $queueEc2Allowed
    queue_generation_allowed = $queueGenerationAllowed
    ttl_schedule_present = $(if ($null -ne $ttl) { [bool]$ttl.live_readiness.live_schedule_present } else { $false })
    ttl_watchdog_proof_present = $(if ($null -ne $ttl) { [bool]$ttl.live_readiness.watchdog_proof_present } else { $false })
  }
  permissions = [ordered]@{
    execute_allowed_now = $false
    schedule_create_allowed_now = $false
    ssm_watchdog_send_allowed_now = $false
    ec2_start_allowed_now = $false
    generation_allowed_now = $false
    queue_mutation_allowed = $false
  }
  inputs = $inputRecords
  checks = $checks
  check_summary = [ordered]@{ checked = $checks.Count; passed = @($checks | Where-Object { $_.result -eq "pass" }).Count; failed = $failedChecks.Count }
  exact_blockers = $exactBlockers
  errors = @($errors | Select-Object -Unique)
  safety_boundary = [ordered]@{
    aws_contacted = $false
    s3_mutated = $false
    scheduler_mutated = $false
    ssm_command_sent = $false
    ec2_started_or_stopped = $false
    generation_executed = $false
    queue_mutated = $false
    git_mutated = $false
  }
  next_action = "Checkpoint this contract. A later explicit queue-authorized live window must pass the same runtime_window_id to New-EC2EmergencyStopSchedule.ps1 and Start-EC2InstanceStopWatchdog.ps1 before any EC2 start."
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W64_NORMAL_RUNTIME_WINDOW_CONTRACT_$stamp.json"
}
$outPath = Resolve-ProjectContainedPath -Path $OutFile
Write-JsonNoBom -Path $outPath -Payload $record
$record | ConvertTo-Json -Depth 30
if (!$structurallyValid) { exit 2 }
exit 0
