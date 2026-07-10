<#
.SYNOPSIS
Creates a local-only final-certification readiness record for the active runtime queue.

.DESCRIPTION
Aggregates the active runtime queue local-support certification, runtime handoff,
and structured Git checkpoint gate into a single final-certification readiness
record. This script does not contact AWS, GitHub, Civitai, ComfyUI, S3, or EC2,
does not run generation, does not consume candidate masks as truth, and does not
promote any mask or lane to final certification.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$RuntimeQueuePath = "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\runtime_lane_queue.json",
  [string]$ActiveLanesPath = "Workflows\base_generation\ACTIVE_LANES.json",
  [string]$OutFile = "",
  [string]$ReadinessPath = "",
  [string]$SelectedLaunchGatePath = "",
  [string]$SelectedExecutionReadinessSnapshotPath = ""
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

function Has-Property {
  param([AllowNull()][object]$Object, [string]$Name)
  return ($null -ne $Object -and $null -ne $Object.PSObject.Properties[$Name])
}

function Get-PropertyValue {
  param([AllowNull()][object]$Object, [string]$Name, [object]$Default = $null)
  if (Has-Property -Object $Object -Name $Name) { return $Object.$Name }
  return $Default
}

function Convert-ToArray {
  param([AllowNull()][object]$Value)
  if ($null -eq $Value) { return @() }
  if ($Value -is [array]) { return @($Value) }
  return @($Value)
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

function Add-Text {
  param([System.Collections.Generic.List[string]]$List, [string]$Text)
  [void]$List.Add($Text)
}

function Get-LaneById {
  param([object[]]$Lanes, [string]$LaneId)
  foreach ($lane in @($Lanes)) {
    if ([string]$lane.lane_id -eq $LaneId) { return $lane }
  }
  return $null
}

$runtimeQueueResolved = Resolve-ProjectPath -Path $RuntimeQueuePath
$activeLanesResolved = Resolve-ProjectPath -Path $ActiveLanesPath
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Done_Certifications\W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_READINESS_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($ReadinessPath)) {
  $ReadinessPath = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$readinessResolved = Resolve-ProjectPath -Path $ReadinessPath

$qaRoot = Resolve-ProjectPath -Path "Plan\Instructions\QA\Evidence"
$doneDir = Join-Path $qaRoot "Done_Certifications"
$runtimeReadinessDir = Join-Path $qaRoot "Runtime_Readiness"
$gitVerificationDir = Join-Path $qaRoot "Git_Verification"

$localSupportPath = Find-LatestFile -Directory $doneDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_LOCAL_SUPPORT_CERTIFICATION_*.json"
$handoffPath = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_RUNTIME_UNBLOCK_HANDOFF_WITH_GIT_GATE_*.json"
if ($null -eq $handoffPath) {
  $handoffPath = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_RUNTIME_UNBLOCK_HANDOFF_*.json"
}
$gitGatePath = Find-LatestFile -Directory $gitVerificationDir -Filter "W66_GITHUB_CHECKPOINT_DRY_RUN_JSON_GATE_*.json"
if ([string]::IsNullOrWhiteSpace($SelectedLaunchGatePath)) {
  $SelectedLaunchGatePath = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_SELECTED_TARGET_RUNTIME_LAUNCH_GATE_*.json"
}
else {
  $SelectedLaunchGatePath = Resolve-ProjectPath -Path $SelectedLaunchGatePath
}
if ([string]::IsNullOrWhiteSpace($SelectedExecutionReadinessSnapshotPath)) {
  $SelectedExecutionReadinessSnapshotPath = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_SELECTED_TARGET_RUNTIME_EXECUTION_READINESS_SNAPSHOT_*.json"
}
else {
  $SelectedExecutionReadinessSnapshotPath = Resolve-ProjectPath -Path $SelectedExecutionReadinessSnapshotPath
}

$defects = New-Object System.Collections.Generic.List[string]
$finalBlockers = New-Object System.Collections.Generic.List[string]

foreach ($required in @(
  @{ label = "runtime_queue"; path = $runtimeQueueResolved },
  @{ label = "active_lanes"; path = $activeLanesResolved },
  @{ label = "local_support"; path = $localSupportPath },
  @{ label = "runtime_handoff"; path = $handoffPath },
  @{ label = "git_gate"; path = $gitGatePath },
  @{ label = "selected_launch_gate"; path = $SelectedLaunchGatePath },
  @{ label = "selected_execution_readiness_snapshot"; path = $SelectedExecutionReadinessSnapshotPath }
)) {
  if ([string]::IsNullOrWhiteSpace([string]$required.path) -or -not (Test-Path -LiteralPath $required.path -PathType Leaf)) {
    Add-Text -List $defects -Text "missing_required_input:$($required.label)"
  }
}

$runtimeQueue = Read-JsonFile -Path $runtimeQueueResolved
$activeLanes = Read-JsonFile -Path $activeLanesResolved
$localSupport = if ($null -ne $localSupportPath) { Read-JsonFile -Path $localSupportPath } else { $null }
$handoff = if ($null -ne $handoffPath) { Read-JsonFile -Path $handoffPath } else { $null }
$gitGate = if ($null -ne $gitGatePath) { Read-JsonFile -Path $gitGatePath } else { $null }
$selectedLaunchGate = if ($null -ne $SelectedLaunchGatePath) { Read-JsonFile -Path $SelectedLaunchGatePath } else { $null }
$selectedExecutionSnapshot = if ($null -ne $SelectedExecutionReadinessSnapshotPath) { Read-JsonFile -Path $SelectedExecutionReadinessSnapshotPath } else { $null }

$queueLanes = @(Convert-ToArray -Value $runtimeQueue.lanes)
$activeLaneRows = @(Convert-ToArray -Value $activeLanes.lanes)
$localSupportLanes = @(Convert-ToArray -Value (Get-PropertyValue -Object $localSupport -Name "lanes_checked" -Default @()))

if ($queueLanes.Count -ne 9) { Add-Text -List $defects -Text "runtime_queue_lane_count_not_9:$($queueLanes.Count)" }
if ($activeLaneRows.Count -ne $queueLanes.Count) { Add-Text -List $defects -Text "active_lanes_count_mismatch:$($activeLaneRows.Count):$($queueLanes.Count)" }
if ([string](Get-PropertyValue -Object $localSupport -Name "result" -Default "") -ne "pass_local_active_runtime_queue_support_certification") {
  Add-Text -List $defects -Text "active_runtime_queue_local_support_not_passing"
}
if (@(Get-PropertyValue -Object $localSupport -Name "defects" -Default @()).Count -gt 0) {
  Add-Text -List $defects -Text "active_runtime_queue_local_support_has_defects"
}
if ([string](Get-PropertyValue -Object $handoff -Name "result" -Default "") -ne "handoff_runtime_smoke_qa_complete") {
  Add-Text -List $finalBlockers -Text "runtime_handoff_not_complete_or_current"
}

$gitGateResult = [string](Get-PropertyValue -Object $gitGate -Name "result" -Default "missing_git_gate")
$gitClean = [bool](Get-PropertyValue -Object $gitGate -Name "clean_worktree" -Default $false)
$gitMatchesOrigin = [bool](Get-PropertyValue -Object $gitGate -Name "local_matches_origin" -Default $false)
$gitCommitAttempted = [bool](Get-PropertyValue -Object $gitGate -Name "commit_attempted" -Default $false)
$gitPushAttempted = [bool](Get-PropertyValue -Object $gitGate -Name "push_attempted" -Default $false)
$currentGitStatus = @()
try {
  $currentGitStatus = @(git -C $ProjectRoot status --porcelain)
} catch {
  $currentGitStatus = @("git_status_failed:$($_.Exception.Message)")
}
$currentGitDirty = ($currentGitStatus.Count -gt 0)
if ($currentGitDirty) {
  $gitClean = $false
  Add-Text -List $finalBlockers -Text "current_worktree_dirty_after_stored_git_gate:$($currentGitStatus.Count)"
}
$gitPassesForEc2 = ($gitGateResult -eq "pass_git_checkpoint_ready" -and $gitClean -and $gitMatchesOrigin -and -not $gitCommitAttempted -and -not $gitPushAttempted)
if (-not $gitPassesForEc2) {
  Add-Text -List $finalBlockers -Text "git_checkpoint_gate_not_clean_for_ec2_execute:$gitGateResult"
}

$handoffGitGate = Get-PropertyValue -Object (Get-PropertyValue -Object $handoff -Name "gate_summary") -Name "git_checkpoint_gate"
$handoffGitPass = [bool](Get-PropertyValue -Object $handoffGitGate -Name "passes_for_ec2_execute" -Default $false)
if (-not $handoffGitPass -and -not $gitPassesForEc2) {
  Add-Text -List $finalBlockers -Text "runtime_handoff_git_checkpoint_gate_not_passing"
}

$selectedLaneId = "sdxl_realvisxl_inpaint_detail_lane"
$launchGateResult = [string](Get-PropertyValue -Object $selectedLaunchGate -Name "result" -Default "missing_selected_launch_gate")
$launchGateLaneId = [string](Get-PropertyValue -Object $selectedLaunchGate -Name "selected_lane_id" -Default "")
if ([string]::IsNullOrWhiteSpace($launchGateLaneId)) {
  $launchGateLaneId = [string](Get-PropertyValue -Object $selectedLaunchGate -Name "lane_id" -Default "")
}
$launchGateFailedCheckCount = [int](Get-PropertyValue -Object $selectedLaunchGate -Name "failed_check_count" -Default -1)
$launchGateAllowsLaunch = [bool](Get-PropertyValue -Object $selectedLaunchGate -Name "target_runtime_launch_allowed" -Default $false)
$launchGateEc2Started = [bool](Get-PropertyValue -Object $selectedLaunchGate -Name "ec2_started" -Default $false)
$launchGateGenerationExecuted = [bool](Get-PropertyValue -Object $selectedLaunchGate -Name "generation_executed" -Default $false)
if ($launchGateLaneId -ne $selectedLaneId) {
  Add-Text -List $defects -Text "selected_launch_gate_lane_mismatch:$launchGateLaneId"
}
if ($launchGateFailedCheckCount -ne 0 -or $launchGateEc2Started -or $launchGateGenerationExecuted) {
  Add-Text -List $defects -Text "selected_launch_gate_invalid_or_mutating:$launchGateResult"
}
if (-not $launchGateAllowsLaunch) {
  Add-Text -List $finalBlockers -Text "selected_launch_gate_target_runtime_launch_blocked:$launchGateResult"
  foreach ($blocker in @(Convert-ToArray -Value (Get-PropertyValue -Object $selectedLaunchGate -Name "exact_blockers" -Default @()))) {
    Add-Text -List $finalBlockers -Text "selected_launch_gate:$([string]$blocker)"
  }
}

$executionSnapshotResult = [string](Get-PropertyValue -Object $selectedExecutionSnapshot -Name "result" -Default "missing_selected_execution_readiness_snapshot")
$executionSnapshotLaneId = [string](Get-PropertyValue -Object $selectedExecutionSnapshot -Name "selected_lane_id" -Default "")
$executionSnapshotFailedCheckCount = [int](Get-PropertyValue -Object $selectedExecutionSnapshot -Name "failed_check_count" -Default -1)
$executionSnapshotReadyForLive = [bool](Get-PropertyValue -Object $selectedExecutionSnapshot -Name "ready_for_live_execution" -Default $false)
$executionSnapshotExecuteAllowed = [bool](Get-PropertyValue -Object $selectedExecutionSnapshot -Name "execute_allowed_now" -Default $false)
$executionSnapshotEc2Started = [bool](Get-PropertyValue -Object $selectedExecutionSnapshot -Name "ec2_started" -Default $false)
$executionSnapshotGenerationExecuted = [bool](Get-PropertyValue -Object $selectedExecutionSnapshot -Name "generation_executed" -Default $false)
if ($executionSnapshotLaneId -ne $selectedLaneId) {
  Add-Text -List $defects -Text "selected_execution_readiness_snapshot_lane_mismatch:$executionSnapshotLaneId"
}
if ($executionSnapshotFailedCheckCount -ne 0 -or $executionSnapshotEc2Started -or $executionSnapshotGenerationExecuted) {
  Add-Text -List $defects -Text "selected_execution_readiness_snapshot_invalid_or_mutating:$executionSnapshotResult"
}
if (-not $executionSnapshotReadyForLive -or -not $executionSnapshotExecuteAllowed) {
  Add-Text -List $finalBlockers -Text "selected_execution_readiness_snapshot_execute_blocked:$executionSnapshotResult"
}

$laneResults = @()
foreach ($queueLane in $queueLanes) {
  $laneId = [string]$queueLane.lane_id
  $supportLane = Get-LaneById -Lanes $localSupportLanes -LaneId $laneId
  $laneBlockers = New-Object System.Collections.Generic.List[string]
  $laneDefects = New-Object System.Collections.Generic.List[string]

  if ($null -eq $supportLane) {
    Add-Text -List $laneDefects -Text "missing_local_support_lane_row"
  }
  else {
    foreach ($blocker in @(Convert-ToArray -Value $supportLane.final_blockers)) {
      Add-Text -List $laneBlockers -Text ([string]$blocker)
    }
    foreach ($defect in @(Convert-ToArray -Value $supportLane.defects)) {
      Add-Text -List $laneDefects -Text ([string]$defect)
    }
  }

  if ([string]$queueLane.status -match "pending_target_runtime|pending_final_certification|local_") {
    Add-Text -List $laneBlockers -Text "queue_status_not_final_certified:$([string]$queueLane.status)"
  }
  if (@(Convert-ToArray -Value $queueLane.proof_evidence).Count -eq 0) {
    Add-Text -List $laneBlockers -Text "target_runtime_proof_evidence_missing"
  }
  if ([string]$queueLane.required_next_runtime_gate -match "optional_target_runtime|final_.*certification|pending_target_runtime|target_runtime") {
    Add-Text -List $laneBlockers -Text "required_next_runtime_gate_still_requires_target_or_final_review"
  }

  foreach ($laneBlocker in @($laneBlockers)) {
    Add-Text -List $finalBlockers -Text "${laneId}:$laneBlocker"
  }
  foreach ($laneDefect in @($laneDefects)) {
    Add-Text -List $defects -Text "${laneId}:$laneDefect"
  }

  $laneResults += [pscustomobject][ordered]@{
    lane_id = $laneId
    order = [int]$queueLane.order
    queue_status = [string]$queueLane.status
    required_next_runtime_gate = [string]$queueLane.required_next_runtime_gate
    local_support_result = [string](Get-PropertyValue -Object $supportLane -Name "local_support_result" -Default "missing")
    local_support_final_status = [string](Get-PropertyValue -Object $supportLane -Name "final_certification_status" -Default "missing")
    final_certification_ready = ($laneDefects.Count -eq 0 -and $laneBlockers.Count -eq 0)
    defects = @($laneDefects)
    final_blockers = @($laneBlockers | Select-Object -Unique)
  }
}

$uniqueFinalBlockers = @($finalBlockers | Select-Object -Unique)
$result = if ($defects.Count -gt 0) {
  "fail_final_certification_readiness_inputs_invalid"
}
elseif ($uniqueFinalBlockers.Count -eq 0) {
  "pass_final_certification_ready"
}
else {
  "blocked_final_certification_target_runtime_or_final_review_missing"
}

$evidence = [ordered]@{
  schema_version = "1.0"
  artifact_type = "active_runtime_queue_final_certification_readiness"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  result = $result
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  comfyui_contacted = $false
  s3_contacted = $false
  ec2_started = $false
  generation_executed = $false
  active_runtime_marker_written = $false
  masks_consumed_as_truth = $false
  masks_promoted = $false
  wave70_hard_gate_rerun = $false
  wave71_plus_activated = $false
  runtime_queue = ConvertTo-ProjectRelativePath -Path $runtimeQueueResolved
  active_lanes_manifest = ConvertTo-ProjectRelativePath -Path $activeLanesResolved
  local_support_certification = ConvertTo-ProjectRelativePath -Path $localSupportPath
  runtime_handoff = ConvertTo-ProjectRelativePath -Path $handoffPath
  git_checkpoint_gate = ConvertTo-ProjectRelativePath -Path $gitGatePath
  selected_target_runtime_launch_gate = ConvertTo-ProjectRelativePath -Path $SelectedLaunchGatePath
  selected_target_runtime_execution_readiness_snapshot = ConvertTo-ProjectRelativePath -Path $SelectedExecutionReadinessSnapshotPath
  lane_count = $queueLanes.Count
  final_ready_lane_count = @($laneResults | Where-Object { $_.final_certification_ready }).Count
  blocked_lane_count = @($laneResults | Where-Object { -not $_.final_certification_ready }).Count
  defects = @($defects)
  final_blockers = @($uniqueFinalBlockers)
  git_gate_summary = [ordered]@{
    result = $gitGateResult
    clean_worktree = $gitClean
    local_matches_origin = $gitMatchesOrigin
    commit_attempted = $gitCommitAttempted
    push_attempted = $gitPushAttempted
    passes_for_ec2_execute = $gitPassesForEc2
    current_git_status_count = $currentGitStatus.Count
    current_git_dirty_preview = @($currentGitStatus | Select-Object -First 20)
  }
  handoff_summary = [ordered]@{
    result = [string](Get-PropertyValue -Object $handoff -Name "result" -Default "")
    git_checkpoint_gate_passes_for_ec2_execute = $handoffGitPass
    ec2_started = [bool](Get-PropertyValue -Object $handoff -Name "ec2_started" -Default $false)
    generation_executed = [bool](Get-PropertyValue -Object $handoff -Name "generation_executed" -Default $false)
  }
  selected_launch_gate_summary = [ordered]@{
    result = $launchGateResult
    selected_lane_id = $launchGateLaneId
    failed_check_count = $launchGateFailedCheckCount
    target_runtime_launch_allowed = $launchGateAllowsLaunch
    exact_blockers = @(Convert-ToArray -Value (Get-PropertyValue -Object $selectedLaunchGate -Name "exact_blockers" -Default @()))
  }
  selected_execution_readiness_snapshot_summary = [ordered]@{
    result = $executionSnapshotResult
    selected_lane_id = $executionSnapshotLaneId
    failed_check_count = $executionSnapshotFailedCheckCount
    ready_for_live_execution = $executionSnapshotReadyForLive
    execute_allowed_now = $executionSnapshotExecuteAllowed
  }
  lanes = @($laneResults)
  certification_boundary = "Local final-certification readiness aggregation only. This does not run ComfyUI, contact AWS/S3/GitHub/Civitai, start EC2, execute generation, promote masks, consume candidate masks as truth, rerun Wave70 hard gates, activate Wave71+, or certify final image quality."
  next_action = "Continue local-first non-mask orchestration/runtime work. Final certification remains blocked until target-runtime proof, clean Git checkpoint, final review, and lane-specific remaining gates are intentionally selected and proven."
}

$outDir = Split-Path -Path $outFileResolved -Parent
$readinessDir = Split-Path -Path $readinessResolved -Parent
[System.IO.Directory]::CreateDirectory($outDir) | Out-Null
[System.IO.Directory]::CreateDirectory($readinessDir) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($evidence | ConvertTo-Json -Depth 30) + [Environment]::NewLine, $utf8NoBom)

$laneLines = foreach ($lane in @($laneResults)) {
  "- $($lane.lane_id): final_ready=$($lane.final_certification_ready); blockers=$(@($lane.final_blockers).Count); local_support=$($lane.local_support_result)"
}
$markdown = @"
# Active Runtime Queue Final Certification Readiness

- created_at: $($evidence.created_at)
- result: $result
- lane_count: $($evidence.lane_count)
- final_ready_lane_count: $($evidence.final_ready_lane_count)
- blocked_lane_count: $($evidence.blocked_lane_count)
- git_gate_result: $gitGateResult
- git_clean_worktree: $gitClean
- git_local_matches_origin: $gitMatchesOrigin
- selected_launch_gate_result: $launchGateResult
- selected_launch_gate_allows_launch: $launchGateAllowsLaunch
- selected_execution_snapshot_result: $executionSnapshotResult
- selected_execution_snapshot_execute_allowed: $executionSnapshotExecuteAllowed

## Lane Readiness

$($laneLines -join "`n")

## Boundary

$($evidence.certification_boundary)

## Evidence

- $($evidence.local_support_certification)
- $($evidence.runtime_handoff)
- $($evidence.git_checkpoint_gate)
- $($evidence.selected_target_runtime_launch_gate)
- $($evidence.selected_target_runtime_execution_readiness_snapshot)
- $(ConvertTo-ProjectRelativePath -Path $outFileResolved)
"@
[System.IO.File]::WriteAllText($readinessResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

$evidence | ConvertTo-Json -Depth 30
if ($defects.Count -gt 0) { exit 2 }
exit 0
