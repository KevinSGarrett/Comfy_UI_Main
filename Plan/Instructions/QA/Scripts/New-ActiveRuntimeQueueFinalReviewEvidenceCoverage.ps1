<#
.SYNOPSIS
Builds a local-only evidence coverage matrix for active runtime final-review work orders.

.DESCRIPTION
Consumes the active W66 final-certification work-order manifest, the latest
closure rollup, and Done_Certifications evidence. It records whether each
final-review work order is closed by a local review packet or accounted for by
a lane-scoped blocker packet. The output is a coverage matrix only: it does not
close work orders, contact external services, start EC2, execute generation,
promote masks, rerun Wave70 hard gates, or activate Wave71+.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$WorkOrderFile = "",
  [string]$ClosureRollupFile = "",
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

$qaRoot = Resolve-ProjectPath -Path "Plan\Instructions\QA\Evidence"
$runtimeReadinessDir = Join-Path $qaRoot "Runtime_Readiness"
$doneDirDefault = Join-Path $qaRoot "Done_Certifications"

if ([string]::IsNullOrWhiteSpace($WorkOrderFile)) {
  $WorkOrderFile = Find-LatestFile -Directory $doneDirDefault -Filter "W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_WORK_ORDER_*.json"
  if ([string]::IsNullOrWhiteSpace($WorkOrderFile)) {
    $WorkOrderFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_WORK_ORDER_*.json"
  }
}
if ([string]::IsNullOrWhiteSpace($ClosureRollupFile)) {
  $ClosureRollupFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_CLOSURE_ROLLUP_*.json"
}
if ([string]::IsNullOrWhiteSpace($DoneEvidenceDir)) {
  $DoneEvidenceDir = $doneDirDefault
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_ACTIVE_RUNTIME_QUEUE_FINAL_REVIEW_EVIDENCE_COVERAGE_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$workOrderResolved = Resolve-ProjectPath -Path $WorkOrderFile
$closureRollupResolved = Resolve-ProjectPath -Path $ClosureRollupFile
$doneDirResolved = Resolve-ProjectPath -Path $DoneEvidenceDir
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile

if ([string]::IsNullOrWhiteSpace($workOrderResolved) -or -not (Test-Path -LiteralPath $workOrderResolved -PathType Leaf)) {
  throw "Final-certification work-order manifest not found."
}
if ([string]::IsNullOrWhiteSpace($closureRollupResolved) -or -not (Test-Path -LiteralPath $closureRollupResolved -PathType Leaf)) {
  throw "Closure rollup not found."
}
if ([string]::IsNullOrWhiteSpace($doneDirResolved) -or -not (Test-Path -LiteralPath $doneDirResolved -PathType Container)) {
  throw "Done-certification evidence directory not found."
}

$workOrderRecord = Read-JsonFile -Path $workOrderResolved
$closureRollup = Read-JsonFile -Path $closureRollupResolved
$reviewWorkOrders = @(
  Convert-ToArray -Value $workOrderRecord.work_orders |
    Where-Object { [string]$_.work_order_type -in @("local_final_review_packet", "final_certification_review_required") } |
    Sort-Object priority, lane_id, work_order_id
)

$closurePackets = @{}
$blockerPackets = @{}
Get-ChildItem -LiteralPath $doneDirResolved -Filter "*.json" -File | ForEach-Object {
  $payload = Read-JsonFile -Path $_.FullName
  $taskId = [string]$payload.task_tracker_id
  if ([string]::IsNullOrWhiteSpace($taskId)) { return }

  if ([string]$payload.artifact_type -eq "lane_final_review_packet") {
    $validClosure = (
      [string]$payload.result -match "^pass_" -and
      [string]$payload.final_decision -eq "done_with_non_blocking_notes" -and
      [bool]$payload.local_only -and
      -not [bool]$payload.full_project_certification_allowed
    )
    if ($validClosure) {
      $current = $closurePackets[$taskId]
      if ($null -eq $current -or $_.LastWriteTimeUtc -gt $current.last_write_utc) {
        $closurePackets[$taskId] = [pscustomobject][ordered]@{
          path = $_.FullName
          last_write_utc = $_.LastWriteTimeUtc
          result = [string]$payload.result
          final_decision = [string]$payload.final_decision
          lane_id = [string]$payload.lane_id
        }
      }
    }
  }

  if ([string]$payload.artifact_type -eq "lane_final_review_blocker_packet") {
    $failedChecks = @(Convert-ToArray -Value $payload.tests_performed | Where-Object { [string]$_.result -ne "pass" })
    $defects = @(Convert-ToArray -Value $payload.defects)
    $validBlocker = (
      [string]$payload.result -match "^blocked_" -and
      [string]$payload.final_decision -eq "blocked" -and
      [bool]$payload.local_only -and
      -not [bool]$payload.new_ec2_started -and
      -not [bool]$payload.new_generation_executed -and
      -not [bool]$payload.full_project_certification_allowed -and
      -not [bool]$payload.closes_work_order -and
      $failedChecks.Count -eq 0 -and
      $defects.Count -eq 0
    )
    if ($validBlocker) {
      $current = $blockerPackets[$taskId]
      if ($null -eq $current -or $_.LastWriteTimeUtc -gt $current.last_write_utc) {
        $blockerPackets[$taskId] = [pscustomobject][ordered]@{
          path = $_.FullName
          last_write_utc = $_.LastWriteTimeUtc
          result = [string]$payload.result
          final_decision = [string]$payload.final_decision
          lane_id = [string]$payload.lane_id
          blocker_summary = @(Convert-ToArray -Value $payload.blocker_summary)
        }
      }
    }
  }
}

$rollupById = @{}
foreach ($entry in @(Convert-ToArray -Value $closureRollup.rollup_entries)) {
  $rollupById[[string]$entry.work_order_id] = $entry
}

$coverageEntries = foreach ($order in $reviewWorkOrders) {
  $id = [string]$order.work_order_id
  $rollupEntry = $rollupById[$id]
  $closurePacket = $closurePackets[$id]
  $blockerPacket = $blockerPackets[$id]
  $closedInRollup = if ($null -ne $rollupEntry) { [bool]$rollupEntry.closed } else { $false }

  if ($closedInRollup -and $null -ne $closurePacket) {
    $coverage = "closed_with_review_packet"
    $evidencePath = $closurePacket.path
    $evidenceResult = $closurePacket.result
    $decision = $closurePacket.final_decision
    $missingReason = ""
  }
  elseif (-not $closedInRollup -and $null -ne $blockerPacket) {
    $coverage = "open_with_blocker_packet"
    $evidencePath = $blockerPacket.path
    $evidenceResult = $blockerPacket.result
    $decision = $blockerPacket.final_decision
    $missingReason = ""
  }
  elseif ($closedInRollup) {
    $coverage = "closed_but_review_packet_missing"
    $evidencePath = ""
    $evidenceResult = ""
    $decision = ""
    $missingReason = "closed_work_order_missing_valid_review_packet"
  }
  else {
    $coverage = "open_missing_blocker_packet"
    $evidencePath = ""
    $evidenceResult = ""
    $decision = ""
    $missingReason = "open_final_review_work_order_missing_valid_blocker_packet"
  }

  [pscustomobject][ordered]@{
    work_order_id = $id
    lane_id = [string]$order.lane_id
    work_order_type = [string]$order.work_order_type
    rollup_closed = $closedInRollup
    rollup_status = $(if ($null -ne $rollupEntry) { [string]$rollupEntry.status } else { "missing_from_rollup" })
    coverage_status = $coverage
    evidence_path = ConvertTo-ProjectRelativePath -Path $evidencePath
    evidence_result = $evidenceResult
    evidence_decision = $decision
    missing_reason = $missingReason
  }
}

$closedCoverage = @($coverageEntries | Where-Object { [string]$_.coverage_status -eq "closed_with_review_packet" })
$blockerCoverage = @($coverageEntries | Where-Object { [string]$_.coverage_status -eq "open_with_blocker_packet" })
$missingCoverage = @($coverageEntries | Where-Object { -not [string]::IsNullOrWhiteSpace([string]$_.missing_reason) })

$result = if ($missingCoverage.Count -eq 0 -and $closedCoverage.Count -gt 0 -and $blockerCoverage.Count -gt 0) {
  "pass_local_only_final_review_evidence_coverage_complete"
}
elseif ($missingCoverage.Count -eq 0) {
  "pass_local_only_final_review_evidence_coverage_no_missing"
}
else {
  "fail_final_review_evidence_coverage_missing"
}

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "active_runtime_queue_final_review_evidence_coverage"
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
  closes_work_orders = $false
  source_work_order_manifest = ConvertTo-ProjectRelativePath -Path $workOrderResolved
  source_closure_rollup = ConvertTo-ProjectRelativePath -Path $closureRollupResolved
  done_evidence_dir = ConvertTo-ProjectRelativePath -Path $doneDirResolved
  final_review_work_order_count = $reviewWorkOrders.Count
  closure_packet_count = $closedCoverage.Count
  blocker_packet_count = $blockerCoverage.Count
  missing_review_evidence_count = $missingCoverage.Count
  coverage_entries = @($coverageEntries)
  missing_review_evidence = @($missingCoverage)
  certification_boundary = "Local final-review evidence coverage only. This does not close open work orders, certify full project completion, contact external services, start EC2, execute generation, promote masks, consume candidate masks as truth, rerun Wave70 hard gates, switch to Jira bookkeeping, or activate Wave71+."
  next_action = "Use this matrix to avoid repeating already-accounted final-review blockers. Continue local-safe orchestration/harness work or explicitly gated target-runtime proof only after all live gates pass."
}

$outDir = Split-Path -Path $outFileResolved -Parent
$mdDir = Split-Path -Path $markdownResolved -Parent
[System.IO.Directory]::CreateDirectory($outDir) | Out-Null
[System.IO.Directory]::CreateDirectory($mdDir) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 30) + [Environment]::NewLine, $utf8NoBom)

$coverageLines = foreach ($entry in $coverageEntries) {
  "- $($entry.work_order_id): $($entry.coverage_status) -> $($entry.evidence_result)"
}
$markdown = @"
# Active Runtime Queue Final Review Evidence Coverage

- created_at: $($record.created_at)
- result: $result
- final_review_work_order_count: $($record.final_review_work_order_count)
- closure_packet_count: $($record.closure_packet_count)
- blocker_packet_count: $($record.blocker_packet_count)
- missing_review_evidence_count: $($record.missing_review_evidence_count)
- closes_work_orders: false
- full_project_certification_allowed: false

## Coverage

$($coverageLines -join "`n")

## Boundary

$($record.certification_boundary)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

$record | ConvertTo-Json -Depth 30
if ($missingCoverage.Count -gt 0) { exit 2 }
exit 0
