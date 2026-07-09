<#
.SYNOPSIS
Creates a local-only support certification for the active base-generation runtime queue.

.DESCRIPTION
This helper validates that the active runtime queue and exported ACTIVE_LANES
manifest agree, that lane workflow/request/requirements files exist, and that
lane evidence paths referenced by the queue exist and are pass-like where a
result/status field is present. It does not contact AWS, GitHub, Civitai,
ComfyUI, S3, or EC2, and it does not claim final target-runtime certification.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$RuntimeQueuePath = "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\runtime_lane_queue.json",
  [string]$ActiveLanesPath = "Workflows\base_generation\ACTIVE_LANES.json",
  [string]$OutFile = "",
  [string]$CertificationPath = ""
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectPath {
  param([AllowNull()][object]$Path)
  if ($null -eq $Path) { return $null }
  $text = [string]$Path
  if ([string]::IsNullOrWhiteSpace($text)) { return $null }
  if ([System.IO.Path]::IsPathRooted($text)) {
    return [System.IO.Path]::GetFullPath($text)
  }
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
  param([AllowNull()][object]$Object, [string]$Name)
  if (Has-Property -Object $Object -Name $Name) { return $Object.$Name }
  return $null
}

function Convert-ToArray {
  param([AllowNull()][object]$Value)
  if ($null -eq $Value) { return @() }
  if ($Value -is [array]) { return @($Value) }
  return @($Value)
}

function Test-PassLikeText {
  param([AllowNull()][object]$Value)
  if ($null -eq $Value) { return $true }
  $text = ([string]$Value).Trim().ToLowerInvariant()
  if ([string]::IsNullOrWhiteSpace($text)) { return $true }
  if ($text -match "fail|failed|error|rejected|untrusted|blocked_gold_mask_dependency_missing") { return $false }
  if ($text -match "blocked_before_ec2_start|runtime_blocked_auth|blocked_expired_session|missing_target_runtime|pending_target_runtime|pending_final_certification") { return $true }
  return ($text.StartsWith("pass") -or $text.Contains("pass_with_notes") -or $text.Contains("complete") -or $text.Contains("proven") -or $text.Contains("ready") -or $text.Contains("validated") -or $text.Contains("local_"))
}

function Get-EvidenceResultText {
  param([AllowNull()][object]$Doc)
  foreach ($name in @("result", "qa_result", "qa_status", "status", "local_support_result", "final_certification_result")) {
    $value = Get-PropertyValue -Object $Doc -Name $name
    if ($null -ne $value -and -not [string]::IsNullOrWhiteSpace([string]$value)) {
      return [string]$value
    }
  }
  $qaDecision = Get-PropertyValue -Object $Doc -Name "qa_decision"
  $qaValue = Get-PropertyValue -Object $qaDecision -Name "result"
  if ($null -ne $qaValue) { return [string]$qaValue }
  $decision = Get-PropertyValue -Object $Doc -Name "decision"
  $decisionValue = Get-PropertyValue -Object $decision -Name "result"
  if ($null -ne $decisionValue) { return [string]$decisionValue }
  return $null
}

function Add-Defect {
  param([System.Collections.Generic.List[string]]$Defects, [string]$Text)
  [void]$Defects.Add($Text)
}

function Test-PathLeaf {
  param(
    [System.Collections.Generic.List[string]]$Defects,
    [string]$Label,
    [AllowNull()][object]$Path
  )
  $resolved = Resolve-ProjectPath -Path $Path
  if ($null -eq $resolved) {
    Add-Defect -Defects $Defects -Text "missing_path_value:$Label"
    return $null
  }
  if (-not (Test-Path -LiteralPath $resolved -PathType Leaf)) {
    Add-Defect -Defects $Defects -Text "missing_path:${Label}:$Path"
  }
  return $resolved
}

$runtimeQueueResolved = Resolve-ProjectPath -Path $RuntimeQueuePath
$activeLanesResolved = Resolve-ProjectPath -Path $ActiveLanesPath
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Done_Certifications\W66_ACTIVE_RUNTIME_QUEUE_LOCAL_SUPPORT_CERTIFICATION_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($CertificationPath)) {
  $CertificationPath = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$certificationResolved = Resolve-ProjectPath -Path $CertificationPath

$defects = New-Object System.Collections.Generic.List[string]
$finalBlockers = New-Object System.Collections.Generic.List[string]
$laneResults = @()

$runtimeQueue = Read-JsonFile -Path $runtimeQueueResolved
$activeLanes = Read-JsonFile -Path $activeLanesResolved
$queueLanes = @(Convert-ToArray -Value $runtimeQueue.lanes)
$exportedLanes = @(Convert-ToArray -Value $activeLanes.lanes)

if ($queueLanes.Count -ne 9) {
  Add-Defect -Defects $defects -Text "runtime_queue_lane_count_not_9:$($queueLanes.Count)"
}
if ($exportedLanes.Count -ne $queueLanes.Count) {
  Add-Defect -Defects $defects -Text "active_lanes_count_mismatch:$($exportedLanes.Count):$($queueLanes.Count)"
}
if ($runtimeQueue.runtime_boundary.ec2_start_allowed_by_queue_file -ne $false) {
  Add-Defect -Defects $defects -Text "runtime_queue_allows_ec2_start"
}
if ($activeLanes.runtime_boundaries.ec2_start_allowed_by_this_manifest -ne $false) {
  Add-Defect -Defects $defects -Text "active_lanes_manifest_allows_ec2_start"
}

$exportedByLane = @{}
foreach ($exportedLane in $exportedLanes) {
  $exportedByLane[[string]$exportedLane.lane_id] = $exportedLane
}

$completedLaneIds = @(Convert-ToArray -Value $runtimeQueue.selection_policy.completed_runtime_lane_ids | ForEach-Object { [string]$_ })
foreach ($queueLane in $queueLanes) {
  $laneDefects = New-Object System.Collections.Generic.List[string]
  $laneFinalBlockers = New-Object System.Collections.Generic.List[string]
  $laneNotes = New-Object System.Collections.Generic.List[string]
  $laneId = [string]$queueLane.lane_id

  if (-not $exportedByLane.ContainsKey($laneId)) {
    Add-Defect -Defects $laneDefects -Text "missing_from_active_lanes_export"
  }
  else {
    $exportedLane = $exportedByLane[$laneId]
    foreach ($pair in @(
      @{ label = "workflow"; queue = $queueLane.workflow_path; export = $exportedLane.workflow },
      @{ label = "runtime_requirements"; queue = $queueLane.requirements_path; export = $exportedLane.runtime_requirements }
    )) {
      $queueRel = (ConvertTo-ProjectRelativePath -Path $pair.queue)
      $exportRel = (ConvertTo-ProjectRelativePath -Path $pair.export)
      if ($queueRel -ne $exportRel -and $exportRel -notlike "Workflows/base_generation/$laneId/*") {
        Add-Defect -Defects $laneDefects -Text "$($pair.label)_export_mismatch:$exportRel"
      }
    }
  }

  [void](Test-PathLeaf -Defects $laneDefects -Label "$laneId.workflow_path" -Path $queueLane.workflow_path)
  [void](Test-PathLeaf -Defects $laneDefects -Label "$laneId.requirements_path" -Path $queueLane.requirements_path)
  if ($exportedByLane.ContainsKey($laneId)) {
    $exportedLane = $exportedByLane[$laneId]
    [void](Test-PathLeaf -Defects $laneDefects -Label "$laneId.exported_workflow" -Path $exportedLane.workflow)
    [void](Test-PathLeaf -Defects $laneDefects -Label "$laneId.exported_smoke_request" -Path $exportedLane.smoke_request)
    [void](Test-PathLeaf -Defects $laneDefects -Label "$laneId.exported_runtime_requirements" -Path $exportedLane.runtime_requirements)
  }

  if ($completedLaneIds -notcontains $laneId) {
    Add-Defect -Defects $laneDefects -Text "lane_not_in_completed_runtime_lane_ids"
  }

  $statusText = [string]$queueLane.status
  if (-not (Test-PassLikeText -Value $statusText)) {
    Add-Defect -Defects $laneDefects -Text "queue_status_not_pass_like:$statusText"
  }

  $sourceEvidence = @(Convert-ToArray -Value $queueLane.source_evidence)
  $localEvidence = @(Convert-ToArray -Value $queueLane.local_pre_ec2_evidence)
  $proofEvidence = @(Convert-ToArray -Value $queueLane.proof_evidence)
  $blockerEvidence = @(Convert-ToArray -Value $queueLane.blocker_evidence)
  $evidencePaths = @($sourceEvidence + $localEvidence + $proofEvidence)
  if ($evidencePaths.Count -eq 0) {
    Add-Defect -Defects $laneDefects -Text "no_support_evidence_paths"
  }

  $checkedEvidence = @()
  $passLikeEvidenceCount = 0
  $jsonEvidenceReadCount = 0
  foreach ($evidencePath in $evidencePaths) {
    $resolvedEvidence = Test-PathLeaf -Defects $laneDefects -Label "$laneId.evidence" -Path $evidencePath
    $evidenceResult = $null
    $evidenceReadable = $null
    $evidencePassLike = $null
    if ($null -ne $resolvedEvidence -and (Test-Path -LiteralPath $resolvedEvidence -PathType Leaf) -and [System.IO.Path]::GetExtension($resolvedEvidence).ToLowerInvariant() -eq ".json") {
      try {
        $evidenceDoc = Read-JsonFile -Path $resolvedEvidence
        $jsonEvidenceReadCount += 1
        $evidenceReadable = $true
        $evidenceResult = Get-EvidenceResultText -Doc $evidenceDoc
        $evidencePassLike = Test-PassLikeText -Value $evidenceResult
        if ($evidencePassLike) {
          $passLikeEvidenceCount += 1
        }
        elseif ($null -ne $evidenceResult) {
          [void]$laneNotes.Add("historical_or_superseded_non_pass_evidence:${evidencePath}:$evidenceResult")
        }
      }
      catch {
        $evidenceReadable = $false
        [void]$laneNotes.Add("json_evidence_parse_warning:$evidencePath")
      }
    }
    $checkedEvidence += [pscustomobject][ordered]@{
      path = ConvertTo-ProjectRelativePath -Path $evidencePath
      result = $evidenceResult
      readable = $evidenceReadable
      pass_like = $evidencePassLike
    }
  }

  if ($jsonEvidenceReadCount -gt 0 -and $passLikeEvidenceCount -eq 0) {
    Add-Defect -Defects $laneDefects -Text "no_pass_like_json_support_evidence"
  }

  if ($statusText -match "pending_target_runtime|pending_final_certification|local_") {
    [void]$laneFinalBlockers.Add("target_runtime_or_final_certification_not_proven")
  }
  if ($proofEvidence.Count -eq 0) {
    [void]$laneFinalBlockers.Add("target_runtime_proof_evidence_missing")
  }

  foreach ($laneDefect in @($laneDefects)) {
    Add-Defect -Defects $defects -Text "${laneId}:$laneDefect"
  }
  foreach ($laneBlocker in @($laneFinalBlockers)) {
    [void]$finalBlockers.Add("${laneId}:$laneBlocker")
  }

  $laneResults += [pscustomobject][ordered]@{
    lane_id = $laneId
    order = [int]$queueLane.order
    status = $statusText
    next_gate = [string]$queueLane.required_next_runtime_gate
    support_evidence_count = $evidencePaths.Count
    json_evidence_read_count = $jsonEvidenceReadCount
    pass_like_evidence_count = $passLikeEvidenceCount
    blocker_evidence_count = $blockerEvidence.Count
    checked_evidence = @($checkedEvidence)
    local_support_result = $(if ($laneDefects.Count -eq 0) { "pass_local_support" } else { "fail_local_support" })
    final_certification_status = $(if ($laneDefects.Count -eq 0 -and $laneFinalBlockers.Count -eq 0) { "final_certification_possible" } elseif ($laneDefects.Count -eq 0) { "local_support_pass_final_certification_blocked" } else { "local_support_failed" })
    defects = @($laneDefects)
    notes = @($laneNotes)
    final_blockers = @($laneFinalBlockers)
  }
}

$localSupportResult = if ($defects.Count -eq 0) { "pass_local_active_runtime_queue_support_certification" } else { "fail_local_active_runtime_queue_support_certification" }
$finalCertificationResult = if ($defects.Count -eq 0 -and $finalBlockers.Count -eq 0) { "final_certification_possible" } else { "blocked_final_certification_missing_target_runtime_or_final_review" }

$evidence = [ordered]@{
  schema_version = "1.0"
  artifact_type = "active_runtime_queue_local_support_certification"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  result = $localSupportResult
  final_certification_result = $finalCertificationResult
  local_only = $true
  ec2_started = $false
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  comfyui_contacted = $false
  generation_executed = $false
  runtime_queue = ConvertTo-ProjectRelativePath -Path $runtimeQueueResolved
  active_lanes_manifest = ConvertTo-ProjectRelativePath -Path $activeLanesResolved
  lane_count = $queueLanes.Count
  lanes_checked = @($laneResults)
  defects = @($defects)
  final_blockers = @($finalBlockers)
  certification_boundary = "Local active runtime queue support only. This does not run ComfyUI, start EC2, upload to S3, rerun Wave70 hard gates, consume candidate masks as truth, promote masks, or certify target-runtime/final image quality."
  next_action = "Use this as a queue-level local support certification before any explicitly selected target-runtime proof or final certification path."
}

$outDir = Split-Path -Path $outFileResolved -Parent
$certDir = Split-Path -Path $certificationResolved -Parent
[System.IO.Directory]::CreateDirectory($outDir) | Out-Null
[System.IO.Directory]::CreateDirectory($certDir) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($evidence | ConvertTo-Json -Depth 30) + [Environment]::NewLine, $utf8NoBom)

$laneLines = foreach ($lane in @($laneResults)) {
  "- $($lane.lane_id): $($lane.local_support_result); final status $($lane.final_certification_status); support evidence $($lane.support_evidence_count)"
}
$markdown = @"
# Active Runtime Queue Local Support Certification

- created_at: $($evidence.created_at)
- local_support_result: $localSupportResult
- final_certification_result: $finalCertificationResult
- lane_count: $($queueLanes.Count)

## Lane Results

$($laneLines -join "`n")

## Boundary

$($evidence.certification_boundary)

## Evidence

- $($evidence.runtime_queue)
- $($evidence.active_lanes_manifest)
- $(ConvertTo-ProjectRelativePath -Path $outFileResolved)
"@
[System.IO.File]::WriteAllText($certificationResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

$evidence | ConvertTo-Json -Depth 30
if ($defects.Count -gt 0) { exit 2 }
exit 0
