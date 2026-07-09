<#
.SYNOPSIS
Creates a lane-scoped final-review packet for the completed low-risk runtime smoke lane.

.DESCRIPTION
Validates the existing low-risk lane static proof, bounded runtime smoke, pullback
hash record, and visual QA record, then emits a done-with-notes review packet for
that lane's runtime-smoke artifact scope only. It does not run ComfyUI, start
EC2, contact external services, execute generation, promote masks, or certify
the full project.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LaneId = "sdxl_low_risk_fallback_lane",
  [string]$WorkOrderFile = "",
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

function Add-Text {
  param([System.Collections.Generic.List[string]]$List, [string]$Text)
  [void]$List.Add($Text)
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

$qaRoot = Resolve-ProjectPath -Path "Plan\Instructions\QA\Evidence"
$runtimeReadinessDir = Join-Path $qaRoot "Runtime_Readiness"
$doneCertificationsDir = Join-Path $qaRoot "Done_Certifications"
if ([string]::IsNullOrWhiteSpace($WorkOrderFile)) {
  $WorkOrderFile = Find-LatestFile -Directory $doneCertificationsDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_WORK_ORDER_*.json"
  if ([string]::IsNullOrWhiteSpace($WorkOrderFile)) {
    $WorkOrderFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_WORK_ORDER_*.json"
  }
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Done_Certifications\W66_LOW_RISK_LANE_FINAL_REVIEW_PACKET_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$workOrderResolved = Resolve-ProjectPath -Path $WorkOrderFile
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile

$staticProofPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W61_EC2_LANE_STATIC_PROOF_POST_LOGIN_RETEST_20260706T104311-0500.json"
$workflowSmokePath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Workflow_Runtime/W61_EC2_WORKFLOW_SMOKE_POST_STATIC_PROOF_RETEST_20260706T110424-0500.json"
$runRecordPath = Resolve-ProjectPath -Path "Plan/Instructions/Operations/Run_Records/aws_gpu_workflow_smoke_20260706T110424-0500.json"
$pullbackPath = Resolve-ProjectPath -Path "Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T110424-0500/PULLBACK_RECORD.json"
$visualQaPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W61_IMAGE_QA_VISUAL_20260706T122027-0500.json"

$defects = New-Object System.Collections.Generic.List[string]
foreach ($required in @(
  @{ label = "work_order"; path = $workOrderResolved },
  @{ label = "static_proof"; path = $staticProofPath },
  @{ label = "workflow_smoke"; path = $workflowSmokePath },
  @{ label = "run_record"; path = $runRecordPath },
  @{ label = "pullback"; path = $pullbackPath },
  @{ label = "visual_qa"; path = $visualQaPath }
)) {
  if ([string]::IsNullOrWhiteSpace([string]$required.path) -or -not (Test-Path -LiteralPath $required.path -PathType Leaf)) {
    Add-Text -List $defects -Text "missing_required_input:$($required.label)"
  }
}

$workOrderRecord = Read-JsonFile -Path $workOrderResolved
$staticProof = Read-JsonFile -Path $staticProofPath
$workflowSmoke = Read-JsonFile -Path $workflowSmokePath
$runRecord = Read-JsonFile -Path $runRecordPath
$pullback = Read-JsonFile -Path $pullbackPath
$visualQa = Read-JsonFile -Path $visualQaPath

$workOrder = @(Convert-ToArray -Value $workOrderRecord.work_orders | Where-Object { [string]$_.lane_id -eq $LaneId -and [string]$_.work_order_type -eq "local_final_review_packet" } | Select-Object -First 1)
if ($workOrder.Count -eq 0) {
  Add-Text -List $defects -Text "local_final_review_work_order_missing:$LaneId"
}

$imagePath = Resolve-ProjectPath -Path $visualQa.image_path
$imageHash = $null
if ($null -eq $imagePath -or -not (Test-Path -LiteralPath $imagePath -PathType Leaf)) {
  Add-Text -List $defects -Text "review_image_missing"
}
else {
  $imageHash = (Get-FileHash -LiteralPath $imagePath -Algorithm SHA256).Hash.ToLowerInvariant()
}
$pullbackImage = @(Convert-ToArray -Value $pullback.files | Where-Object { [string]$_.artifact_type -eq "image" } | Select-Object -First 1)
$pullbackImageHash = if ($pullbackImage.Count -gt 0) { [string]$pullbackImage[0].sha256 } else { "" }

$checks = @(
  (New-Check -Name "work_order_ready_for_local_review" -Passed ($workOrder.Count -gt 0 -and [string]$workOrder[0].status -eq "ready_local_review_only_global_project_still_blocked") -Observed $(if ($workOrder.Count -gt 0) { [string]$workOrder[0].status } else { "missing" }) -Expected "ready_local_review_only_global_project_still_blocked"),
  (New-Check -Name "static_proof_passed_and_stopped" -Passed ([string]$staticProof.result -eq "ec2_static_proof_recorded" -and [string]$staticProof.lane_id -eq $LaneId -and [string]$staticProof.final_state -eq "stopped" -and [bool]$staticProof.generation_executed -eq $false) -Observed ([ordered]@{ result = $staticProof.result; lane_id = $staticProof.lane_id; final_state = $staticProof.final_state; generation_executed = $staticProof.generation_executed }) -Expected "static proof recorded for lane, EC2 stopped, no generation"),
  (New-Check -Name "workflow_smoke_generated_and_stopped" -Passed ([string]$workflowSmoke.result -eq "workflow_smoke_generation_complete" -and [string]$workflowSmoke.lane_id -eq $LaneId -and [string]$workflowSmoke.final_state -eq "stopped" -and [bool]$workflowSmoke.generation_executed -eq $true) -Observed ([ordered]@{ result = $workflowSmoke.result; lane_id = $workflowSmoke.lane_id; final_state = $workflowSmoke.final_state; generation_executed = $workflowSmoke.generation_executed }) -Expected "workflow smoke completed one generation and stopped"),
  (New-Check -Name "run_record_matches_workflow_smoke" -Passed ([string]$runRecord.result -eq "workflow_smoke_generation_complete" -and [string]$runRecord.lane_id -eq $LaneId -and [string]$runRecord.final_state -eq "stopped") -Observed ([ordered]@{ result = $runRecord.result; lane_id = $runRecord.lane_id; final_state = $runRecord.final_state }) -Expected "run record matches completed stopped workflow smoke"),
  (New-Check -Name "pullback_hashes_verified" -Passed ([string]$pullback.status -eq "pullback_hashes_verified" -and [bool]$pullback.hashes_verified -eq $true -and @($pullback.errors).Count -eq 0) -Observed ([ordered]@{ status = $pullback.status; hashes_verified = $pullback.hashes_verified; errors = @($pullback.errors).Count }) -Expected "pullback hashes verified with no errors"),
  (New-Check -Name "image_hash_matches_pullback" -Passed (-not [string]::IsNullOrWhiteSpace($imageHash) -and $imageHash -eq $pullbackImageHash.ToLowerInvariant()) -Observed ([ordered]@{ image_hash = $imageHash; pullback_hash = $pullbackImageHash }) -Expected "visual QA image hash matches pullback record"),
  (New-Check -Name "visual_qa_passed_with_notes" -Passed ([string]$visualQa.result -eq "pass_with_notes_for_runtime_smoke" -and [int]$visualQa.qa_score -ge [int]$visualQa.pass_threshold) -Observed ([ordered]@{ result = $visualQa.result; qa_score = $visualQa.qa_score; pass_threshold = $visualQa.pass_threshold }) -Expected "visual QA pass_with_notes_for_runtime_smoke at or above threshold")
)

foreach ($check in $checks) {
  if ([string]$check.result -ne "pass") { Add-Text -List $defects -Text "check_failed:$($check.name)" }
}

$knownIssues = @(
  "Visual QA notes minor beauty-retouch softness, slightly synthetic hair flyaways, and soft blazer/lapel edges.",
  "This packet certifies only the low-risk lane runtime-smoke artifact scope, not final portfolio quality.",
  "Project-level final certification remains blocked by other lane target-runtime/final-review work orders, live gates, and gold-mask-dependent gates."
)

$result = if ($defects.Count -eq 0) { "pass_low_risk_lane_final_review_packet_ready" } else { "fail_low_risk_lane_final_review_packet" }
$finalDecision = if ($defects.Count -eq 0) { "done_with_non_blocking_notes" } else { "failed" }

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "lane_final_review_packet"
  certification_id = "CERT-W66-SDXL-LOW-RISK-LANE-FINAL-REVIEW-$(Get-Date -Format 'yyyyMMddTHHmmss-0500')"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  task_tracker_id = "WO-W66-SDXL_LOW_RISK_FALLBACK_LANE-FINAL-REVIEW-PACKET"
  lane_id = $LaneId
  result = $result
  final_decision = $finalDecision
  local_only = $true
  new_ec2_started = $false
  new_generation_executed = $false
  historical_ec2_started = $true
  historical_generation_executed = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  s3_contacted = $false
  comfyui_contacted = $false
  masks_consumed_as_truth = $false
  masks_promoted = $false
  wave70_hard_gate_rerun = $false
  wave71_plus_activated = $false
  full_project_certification_allowed = $false
  closes_work_order = $true
  artifact_scope = "Lane-scoped final review packet for the completed sdxl_low_risk_fallback_lane runtime smoke proof only."
  implementation_summary = "Reviewed existing lane workflow, EC2 static proof, bounded workflow smoke, pullback/hash evidence, and visual QA evidence without rerunning live runtime."
  tests_performed = @($checks)
  qa_summary = [ordered]@{
    visual_qa_result = [string]$visualQa.result
    qa_score = [int]$visualQa.qa_score
    pass_threshold = [int]$visualQa.pass_threshold
    defects = @(Convert-ToArray -Value $visualQa.defects)
  }
  evidence_paths = [ordered]@{
    work_order = ConvertTo-ProjectRelativePath -Path $workOrderResolved
    static_proof = ConvertTo-ProjectRelativePath -Path $staticProofPath
    workflow_smoke = ConvertTo-ProjectRelativePath -Path $workflowSmokePath
    run_record = ConvertTo-ProjectRelativePath -Path $runRecordPath
    pullback_record = ConvertTo-ProjectRelativePath -Path $pullbackPath
    visual_qa = ConvertTo-ProjectRelativePath -Path $visualQaPath
    reviewed_image = ConvertTo-ProjectRelativePath -Path $imagePath
  }
  known_issues = $knownIssues
  defects = @($defects)
  certifier = "Codex Desktop autonomous release manager"
  certification_boundary = "Lane-scoped runtime-smoke final review only. This does not certify full project completion, final portfolio quality, video/audio/deformation quality, body-mask readiness, Wave70 mask promotion, or Wave71+ activation."
  next_action = "Use this packet as the local review closure for the low-risk lane work order; continue with other final-certification work orders or explicitly gated target-runtime proof."
}

$outDir = Split-Path -Path $outFileResolved -Parent
$mdDir = Split-Path -Path $markdownResolved -Parent
[System.IO.Directory]::CreateDirectory($outDir) | Out-Null
[System.IO.Directory]::CreateDirectory($mdDir) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 30) + [Environment]::NewLine, $utf8NoBom)

$checkLines = foreach ($check in $checks) {
  "- $($check.name): $($check.result)"
}
$evidenceLines = foreach ($prop in $record.evidence_paths.GetEnumerator()) {
  "- $($prop.Name): $($prop.Value)"
}
$knownIssueLines = foreach ($issue in $knownIssues) {
  "- $issue"
}
$markdown = @"
# Low-Risk Lane Final Review Packet

- certification_id: $($record.certification_id)
- created_at: $($record.created_at)
- lane_id: $LaneId
- result: $result
- final_decision: $finalDecision
- full_project_certification_allowed: false

## Checks

$($checkLines -join "`n")

## Evidence

$($evidenceLines -join "`n")

## Known Issues

$($knownIssueLines -join "`n")

## Boundary

$($record.certification_boundary)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

$record | ConvertTo-Json -Depth 30
if ($defects.Count -gt 0) { exit 2 }
exit 0
