<#
.SYNOPSIS
Builds a local-only work-order manifest from active runtime queue final-readiness evidence.

.DESCRIPTION
Consumes the latest active runtime queue final-certification readiness record and
turns its blockers into explicit work orders. The output is an orchestration
artifact only: it does not contact AWS, GitHub, Civitai, S3, ComfyUI, or EC2,
does not execute generation, does not promote masks, and does not certify final
quality.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$ReadinessEvidenceFile = "",
  [string]$OutFile = "",
  [string]$MarkdownOutFile = ""
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

function Find-LatestFile {
  param([string]$Directory, [string]$Filter)
  if (-not (Test-Path -LiteralPath $Directory -PathType Container)) { return $null }
  $item = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File |
    Sort-Object LastWriteTimeUtc, Name -Descending |
    Select-Object -First 1
  if ($null -eq $item) { return $null }
  return $item.FullName
}

function Convert-ToArray {
  param([AllowNull()][object]$Value)
  if ($null -eq $Value) { return @() }
  if ($Value -is [array]) { return @($Value) }
  return @($Value)
}

function New-WorkOrder {
  param(
    [string]$Id,
    [string]$LaneId = "",
    [int]$Priority,
    [string]$Type,
    [string]$Status,
    [string[]]$BlockedBy = @(),
    [string[]]$RequiredEvidence = @(),
    [string]$NextAction
  )

  return [pscustomobject][ordered]@{
    work_order_id = $Id
    lane_id = $LaneId
    priority = $Priority
    work_order_type = $Type
    status = $Status
    blocked_by = @($BlockedBy)
    required_evidence = @($RequiredEvidence)
    next_action = $NextAction
  }
}

$qaRoot = Resolve-ProjectPath -Path "Plan\Instructions\QA\Evidence"
$doneDir = Join-Path $qaRoot "Done_Certifications"
if ([string]::IsNullOrWhiteSpace($ReadinessEvidenceFile)) {
  $ReadinessEvidenceFile = Find-LatestFile -Directory $doneDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_READINESS_*.json"
}
if ([string]::IsNullOrWhiteSpace($ReadinessEvidenceFile) -or -not (Test-Path -LiteralPath (Resolve-ProjectPath -Path $ReadinessEvidenceFile) -PathType Leaf)) {
  throw "Final certification readiness evidence not found."
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_WORK_ORDER_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$readinessResolved = Resolve-ProjectPath -Path $ReadinessEvidenceFile
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile
$readiness = Read-JsonFile -Path $readinessResolved

$workOrders = New-Object System.Collections.Generic.List[object]
$globalBlockers = New-Object System.Collections.Generic.List[string]
$readinessResult = [string]$readiness.result
$gitPasses = [bool]$readiness.git_gate_summary.passes_for_ec2_execute

if (-not $gitPasses) {
  [void]$globalBlockers.Add("git_checkpoint_gate_not_clean_for_ec2_execute")
  [void]$workOrders.Add((New-WorkOrder `
    -Id "WO-W66-GLOBAL-GIT-CHECKPOINT-CLEAN" `
    -Priority 1 `
    -Type "global_preflight_gate" `
    -Status "blocked_by_dirty_worktree" `
    -BlockedBy @("blocked_git_checkpoint_dirty_worktree") `
    -RequiredEvidence @("Invoke-GitHubCheckpoint.ps1 dry-run JSON with result=pass_git_checkpoint_ready, clean_worktree=true, local_matches_origin=true, commit_attempted=false, push_attempted=false") `
    -NextAction "Do not start EC2; intentionally checkpoint or otherwise resolve the dirty worktree only when a target-runtime task is selected."))
}

if (-not $gitPasses -and [string]$readiness.handoff_summary.git_checkpoint_gate_passes_for_ec2_execute -ne "True") {
  [void]$globalBlockers.Add("runtime_handoff_git_gate_not_passing")
}

$laneRows = @(Convert-ToArray -Value $readiness.lanes | Sort-Object order)
foreach ($lane in $laneRows) {
  $laneId = [string]$lane.lane_id
  $laneBlockers = @(Convert-ToArray -Value $lane.final_blockers | ForEach-Object { [string]$_ })
  $needsTargetRuntime = @($laneBlockers | Where-Object { $_ -match "target_runtime_proof_evidence_missing|target_runtime_or_final_certification_not_proven|required_next_runtime_gate_still_requires_target_or_final_review" }).Count -gt 0
  $needsFinalReview = @($laneBlockers | Where-Object { $_ -match "pending_final_certification|queue_status_not_final_certified|final_certification" }).Count -gt 0

  if ([bool]$lane.final_certification_ready) {
    [void]$workOrders.Add((New-WorkOrder `
      -Id ("WO-W66-{0}-FINAL-REVIEW-PACKET" -f $laneId.ToUpperInvariant()) `
      -LaneId $laneId `
      -Priority 20 `
      -Type "local_final_review_packet" `
      -Status "ready_local_review_only_global_project_still_blocked" `
      -BlockedBy @($globalBlockers) `
      -RequiredEvidence @("existing runtime smoke proof", "pullback/hash evidence", "technical QA", "visual QA", "done certification review") `
      -NextAction "Prepare or review the lane final packet locally; do not claim project final certification while other lanes remain blocked."))
    continue
  }

  if ($needsTargetRuntime) {
    [void]$workOrders.Add((New-WorkOrder `
      -Id ("WO-W66-{0}-TARGET-RUNTIME-PROOF" -f $laneId.ToUpperInvariant()) `
      -LaneId $laneId `
      -Priority 40 `
      -Type "target_runtime_proof_required" `
      -Status "blocked_until_explicit_live_window_and_gates" `
      -BlockedBy @($globalBlockers + $laneBlockers) `
      -RequiredEvidence @("explicit user-selected target-runtime task", "clean Git checkpoint gate", "AWS auth/account gate", "S3/deploy-bundle publish proof if used", "EC2 static proof", "bounded workflow smoke run", "artifact pullback/hash proof", "strict whole-image QA") `
      -NextAction "Keep local orchestration ready; run target-runtime proof only after explicit selection and all live gates pass."))
  }

  if ($needsFinalReview) {
    [void]$workOrders.Add((New-WorkOrder `
      -Id ("WO-W66-{0}-FINAL-CERTIFICATION-REVIEW" -f $laneId.ToUpperInvariant()) `
      -LaneId $laneId `
      -Priority 50 `
      -Type "final_certification_runtime_ready" `
      -Status "blocked_until_lane_evidence_complete" `
      -BlockedBy @($laneBlockers) `
      -RequiredEvidence @("lane-specific final review", "all target-runtime and QA gates required by lane status", "done certification record") `
      -NextAction "Perform final review only after lane target-runtime and QA evidence are complete."))
  }
}

$orderedWorkOrders = @($workOrders | Sort-Object priority, lane_id, work_order_id)
$result = if ($orderedWorkOrders.Count -gt 0) { "pass_local_only_final_certification_work_order_ready" } else { "pass_no_work_orders_required" }

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "active_runtime_queue_final_certification_work_order"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  result = $result
  readiness_result = $readinessResult
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  s3_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  active_runtime_marker_written = $false
  masks_consumed_as_truth = $false
  masks_promoted = $false
  wave70_hard_gate_rerun = $false
  wave71_plus_activated = $false
  readiness_evidence = ConvertTo-ProjectRelativePath -Path $readinessResolved
  lane_count = [int]$readiness.lane_count
  final_ready_lane_count = [int]$readiness.final_ready_lane_count
  blocked_lane_count = [int]$readiness.blocked_lane_count
  final_blocker_count = @(Convert-ToArray -Value $readiness.final_blockers).Count
  global_blockers = @($globalBlockers | Select-Object -Unique)
  work_order_count = $orderedWorkOrders.Count
  work_orders = @($orderedWorkOrders)
  certification_boundary = "Local work-order orchestration only. This does not contact external services, start EC2, execute generation, certify final quality, promote masks, consume candidate masks as truth, rerun Wave70 hard gates, or activate Wave71+."
  next_action = "Use this manifest to choose the next explicit non-mask local orchestration task, or to prepare a bounded target-runtime task only after live gates are intentionally selected and passing."
}

$outDir = Split-Path -Path $outFileResolved -Parent
$mdDir = Split-Path -Path $markdownResolved -Parent
[System.IO.Directory]::CreateDirectory($outDir) | Out-Null
[System.IO.Directory]::CreateDirectory($mdDir) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 30) + [Environment]::NewLine, $utf8NoBom)

$orderLines = foreach ($order in $orderedWorkOrders) {
  "- $($order.work_order_id): $($order.status); lane=$($order.lane_id); type=$($order.work_order_type)"
}
$markdown = @"
# Active Runtime Queue Final Certification Work Orders

- created_at: $($record.created_at)
- result: $result
- readiness_result: $readinessResult
- work_order_count: $($record.work_order_count)
- global_blockers: $(@($record.global_blockers) -join ", ")

## Work Orders

$($orderLines -join "`n")

## Boundary

$($record.certification_boundary)

## Evidence

- $($record.readiness_evidence)
- $(ConvertTo-ProjectRelativePath -Path $outFileResolved)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

$record | ConvertTo-Json -Depth 30
exit 0
