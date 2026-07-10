<#
.SYNOPSIS
Builds a local-only closure rollup for active runtime queue final-certification work orders.

.DESCRIPTION
Consumes the final-certification work-order manifest and completed lane review
packets, then marks which work orders are closed and which remain blocked or
open. The output is a state rollup only: it does not contact AWS, GitHub,
Civitai, S3, ComfyUI, or EC2, does not execute generation, does not promote
masks, and does not certify the full project.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$WorkOrderFile = "",
  [string]$DoneEvidenceDir = "",
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

function New-RollupEntry {
  param(
    [object]$WorkOrder,
    [bool]$Closed,
    [string]$ClosureEvidence = "",
    [string]$ClosureResult = "",
    [string]$ClosureDecision = ""
  )

  $status = if ($Closed) { "closed_local_review_packet" } else { [string]$WorkOrder.status }
  $remainingReason = if ($Closed) { "" } else { [string]$WorkOrder.status }

  return [pscustomobject][ordered]@{
    work_order_id = [string]$WorkOrder.work_order_id
    lane_id = [string]$WorkOrder.lane_id
    work_order_type = [string]$WorkOrder.work_order_type
    priority = [int]$WorkOrder.priority
    status = $status
    closed = $Closed
    closure_evidence = $ClosureEvidence
    closure_result = $ClosureResult
    closure_decision = $ClosureDecision
    remaining_reason = $remainingReason
  }
}

$qaRoot = Resolve-ProjectPath -Path "Plan\Instructions\QA\Evidence"
$runtimeReadinessDir = Join-Path $qaRoot "Runtime_Readiness"
$doneDirDefault = Join-Path $qaRoot "Done_Certifications"

if ([string]::IsNullOrWhiteSpace($WorkOrderFile)) {
  $WorkOrderFile = Find-LatestFile -Directory $doneDirDefault -Filter "W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_WORK_ORDER_*.json"
  if ([string]::IsNullOrWhiteSpace($WorkOrderFile)) {
    $WorkOrderFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_WORK_ORDER_*.json"
  }
}
if ([string]::IsNullOrWhiteSpace($DoneEvidenceDir)) {
  $DoneEvidenceDir = $doneDirDefault
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_CLOSURE_ROLLUP_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$workOrderResolved = Resolve-ProjectPath -Path $WorkOrderFile
$doneDirResolved = Resolve-ProjectPath -Path $DoneEvidenceDir
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile

if ([string]::IsNullOrWhiteSpace($workOrderResolved) -or -not (Test-Path -LiteralPath $workOrderResolved -PathType Leaf)) {
  throw "Final-certification work-order manifest not found."
}
if ([string]::IsNullOrWhiteSpace($doneDirResolved) -or -not (Test-Path -LiteralPath $doneDirResolved -PathType Container)) {
  throw "Done-certification evidence directory not found."
}

$workOrderRecord = Read-JsonFile -Path $workOrderResolved
$workOrders = @(Convert-ToArray -Value $workOrderRecord.work_orders | Sort-Object priority, lane_id, work_order_id)
$closurePackets = @(
  Get-ChildItem -LiteralPath $doneDirResolved -Filter "*.json" -File |
    ForEach-Object {
      $payload = Read-JsonFile -Path $_.FullName
      if ([string]$payload.artifact_type -eq "lane_final_review_packet") {
        [pscustomobject][ordered]@{
          path = $_.FullName
          task_tracker_id = [string]$payload.task_tracker_id
          lane_id = [string]$payload.lane_id
          result = [string]$payload.result
          final_decision = [string]$payload.final_decision
          full_project_certification_allowed = [bool]$payload.full_project_certification_allowed
          local_only = [bool]$payload.local_only
        }
      }
    }
)

$closedById = @{}
foreach ($packet in $closurePackets) {
  $isClosedPacket = (
    -not [string]::IsNullOrWhiteSpace($packet.task_tracker_id) -and
    [string]$packet.result -match "^pass_" -and
    [string]$packet.final_decision -eq "done_with_non_blocking_notes" -and
    [bool]$packet.local_only -and
    -not [bool]$packet.full_project_certification_allowed
  )
  if ($isClosedPacket -and -not $closedById.ContainsKey($packet.task_tracker_id)) {
    $closedById[$packet.task_tracker_id] = $packet
  }
}

$rollupEntries = foreach ($order in $workOrders) {
  $id = [string]$order.work_order_id
  if ($closedById.ContainsKey($id)) {
    $packet = $closedById[$id]
    New-RollupEntry `
      -WorkOrder $order `
      -Closed $true `
      -ClosureEvidence (ConvertTo-ProjectRelativePath -Path $packet.path) `
      -ClosureResult $packet.result `
      -ClosureDecision $packet.final_decision
  }
  else {
    New-RollupEntry -WorkOrder $order -Closed $false
  }
}

$closedEntries = @($rollupEntries | Where-Object { [bool]$_.closed })
$openEntries = @($rollupEntries | Where-Object { -not [bool]$_.closed })
$remainingLocalReady = @($openEntries | Where-Object { [string]$_.status -eq "ready_local_review_only_global_project_still_blocked" })
$remainingTargetRuntime = @($openEntries | Where-Object { [string]$_.work_order_type -eq "target_runtime_proof_required" })
$remainingFinalReview = @($openEntries | Where-Object { [string]$_.work_order_type -eq "final_certification_runtime_ready" })
$remainingGlobal = @($openEntries | Where-Object { [string]$_.work_order_type -eq "global_preflight_gate" })

$result = if ($closedEntries.Count -gt 0) {
  "pass_local_only_final_certification_closure_rollup"
}
elseif ($workOrders.Count -gt 0) {
  "pass_local_only_no_work_orders_closed_yet"
}
else {
  "pass_local_only_no_work_orders"
}

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "active_runtime_queue_final_certification_closure_rollup"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  result = $result
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
  full_project_certification_allowed = $false
  source_work_order_manifest = ConvertTo-ProjectRelativePath -Path $workOrderResolved
  done_evidence_dir = ConvertTo-ProjectRelativePath -Path $doneDirResolved
  source_work_order_count = $workOrders.Count
  closed_work_order_count = $closedEntries.Count
  open_work_order_count = $openEntries.Count
  remaining_local_ready_count = $remainingLocalReady.Count
  remaining_global_preflight_count = $remainingGlobal.Count
  remaining_target_runtime_count = $remainingTargetRuntime.Count
  remaining_final_review_count = $remainingFinalReview.Count
  closed_work_order_ids = @($closedEntries | ForEach-Object { $_.work_order_id })
  open_work_order_ids = @($openEntries | ForEach-Object { $_.work_order_id })
  rollup_entries = @($rollupEntries)
  certification_boundary = "Local closure-state rollup only. This does not certify the full project, contact external services, start EC2, execute generation, promote masks, consume candidate masks as truth, rerun Wave70 hard gates, or activate Wave71+."
  next_action = "Use this rollup to avoid reopening closed local review packets. Continue local-safe orchestration/harness work or explicitly gated target-runtime proof only after all live gates pass."
}

$outDir = Split-Path -Path $outFileResolved -Parent
$mdDir = Split-Path -Path $markdownResolved -Parent
[System.IO.Directory]::CreateDirectory($outDir) | Out-Null
[System.IO.Directory]::CreateDirectory($mdDir) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 30) + [Environment]::NewLine, $utf8NoBom)

$closedLines = foreach ($entry in $closedEntries) {
  "- $($entry.work_order_id): $($entry.closure_decision); evidence=$($entry.closure_evidence)"
}
if ($closedLines.Count -eq 0) { $closedLines = @("- none") }
$remainingLines = foreach ($entry in $openEntries) {
  "- $($entry.work_order_id): $($entry.status); type=$($entry.work_order_type); lane=$($entry.lane_id)"
}
if ($remainingLines.Count -eq 0) { $remainingLines = @("- none") }

$markdown = @"
# Active Runtime Queue Final Certification Closure Rollup

- created_at: $($record.created_at)
- result: $result
- source_work_order_count: $($record.source_work_order_count)
- closed_work_order_count: $($record.closed_work_order_count)
- open_work_order_count: $($record.open_work_order_count)
- remaining_local_ready_count: $($record.remaining_local_ready_count)
- remaining_target_runtime_count: $($record.remaining_target_runtime_count)
- remaining_final_review_count: $($record.remaining_final_review_count)
- full_project_certification_allowed: false

## Closed Work Orders

$($closedLines -join "`n")

## Remaining Work Orders

$($remainingLines -join "`n")

## Boundary

$($record.certification_boundary)

## Evidence

- $($record.source_work_order_manifest)
- $(ConvertTo-ProjectRelativePath -Path $outFileResolved)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

$record | ConvertTo-Json -Depth 30
exit 0
