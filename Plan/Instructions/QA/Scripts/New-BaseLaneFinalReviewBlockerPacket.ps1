<#
.SYNOPSIS
Creates a lane-scoped final-review blocker packet for the RealVisXL base lane.

.DESCRIPTION
Reviews existing target-runtime and local quality evidence for
sdxl_realvisxl_base_lane. The helper records why the lane cannot be closed as a
final-review packet yet: the target-runtime smoke proves generic base runtime
viability, while the later single-hand and two-character contact evidence
explicitly disallows final certification and identifies missing refine,
robustness, and candidate-specific proof.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LaneId = "sdxl_realvisxl_base_lane",
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
  $OutFile = "Plan\Instructions\QA\Evidence\Done_Certifications\W66_BASE_LANE_FINAL_REVIEW_BLOCKER_PACKET_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$workOrderResolved = Resolve-ProjectPath -Path $WorkOrderFile
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile

$staticProofPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Workflow_Static_Validation/W63_EC2_LANE_STATIC_PROOF_REALVISXL_AFTER_INSTALL_20260706T131129-0500.json"
$workflowSmokePath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Workflow_Runtime/W63_EC2_WORKFLOW_SMOKE_REALVISXL_AFTER_STATIC_PROOF_20260706T132206-0500.json"
$pullbackPath = Resolve-ProjectPath -Path "Plan/Instructions/Operations/Pulled_Back_Artifacts/aws_gpu_workflow_smoke_20260706T132206-0500/PULLBACK_RECORD.json"
$runtimeVisualQaPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W63_REALVISXL_IMAGE_QA_VISUAL_20260706T140120-0500.json"
$singleHandVisualQaPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_REALVISXL_SINGLE_HAND_CONTACT_CLOSEUP_V1_VISUAL_QA_20260707T095000-0500.json"
$singleHandTrackerPath = Resolve-ProjectPath -Path "Plan/Tracker/Evidence/W69_LOCAL_REALVISXL_SINGLE_HAND_CONTACT_CLOSEUP_20260707T095000-0500.json"
$twoCharacterVisualQaPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_REALVISXL_TWO_CHARACTER_HAND_TO_BODY_VISUAL_QA_20260707T115000-0500.json"
$twoCharacterTrackerPath = Resolve-ProjectPath -Path "Plan/Tracker/Evidence/W69_LOCAL_REALVISXL_TWO_CHARACTER_HAND_TO_BODY_PIXEL_ATTEMPT_20260707T115000-0500.json"
$queuePath = Resolve-ProjectPath -Path "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json"

$missingInputs = New-Object System.Collections.Generic.List[string]
foreach ($required in @(
  @{ label = "work_order"; path = $workOrderResolved },
  @{ label = "static_proof"; path = $staticProofPath },
  @{ label = "workflow_smoke"; path = $workflowSmokePath },
  @{ label = "pullback"; path = $pullbackPath },
  @{ label = "runtime_visual_qa"; path = $runtimeVisualQaPath },
  @{ label = "single_hand_visual_qa"; path = $singleHandVisualQaPath },
  @{ label = "single_hand_tracker"; path = $singleHandTrackerPath },
  @{ label = "two_character_visual_qa"; path = $twoCharacterVisualQaPath },
  @{ label = "two_character_tracker"; path = $twoCharacterTrackerPath },
  @{ label = "runtime_lane_queue"; path = $queuePath }
)) {
  if ([string]::IsNullOrWhiteSpace([string]$required.path) -or -not (Test-Path -LiteralPath $required.path -PathType Leaf)) {
    Add-Text -List $missingInputs -Text "missing_required_input:$($required.label)"
  }
}

$workOrderRecord = Read-JsonFile -Path $workOrderResolved
$staticProof = Read-JsonFile -Path $staticProofPath
$workflowSmoke = Read-JsonFile -Path $workflowSmokePath
$pullback = Read-JsonFile -Path $pullbackPath
$runtimeVisualQa = Read-JsonFile -Path $runtimeVisualQaPath
$singleHandVisualQa = Read-JsonFile -Path $singleHandVisualQaPath
$singleHandTracker = Read-JsonFile -Path $singleHandTrackerPath
$twoCharacterVisualQa = Read-JsonFile -Path $twoCharacterVisualQaPath
$twoCharacterTracker = Read-JsonFile -Path $twoCharacterTrackerPath
$queue = Read-JsonFile -Path $queuePath

$workOrder = @(Convert-ToArray -Value $workOrderRecord.work_orders | Where-Object { [string]$_.lane_id -eq $LaneId -and [string]$_.work_order_type -eq "final_certification_runtime_ready" } | Select-Object -First 1)
$targetProofWorkOrder = @(Convert-ToArray -Value $workOrderRecord.work_orders | Where-Object { [string]$_.lane_id -eq $LaneId -and [string]$_.work_order_type -eq "target_runtime_proof_required" } | Select-Object -First 1)
$queueLane = @(Convert-ToArray -Value $queue.lanes | Where-Object { [string]$_.lane_id -eq $LaneId } | Select-Object -First 1)

$runtimeVisualDefects = @(Convert-ToArray -Value $runtimeVisualQa.defects)
$singleHandRemainingNotes = @(Convert-ToArray -Value $singleHandVisualQa.sample.remaining_notes)
$twoCharacterRemainingRisks = @(Convert-ToArray -Value $twoCharacterVisualQa.remaining_risks)
$queuePromotionRule = if ($queueLane.Count -gt 0) { [string]$queueLane[0].promotion_rule } else { "" }
$workOrderBlockerList = New-Object System.Collections.Generic.List[string]
if ($workOrder.Count -gt 0) {
  foreach ($blocker in @(Convert-ToArray -Value $workOrder[0].blocked_by)) {
    if (-not [string]::IsNullOrWhiteSpace([string]$blocker)) { Add-Text -List $workOrderBlockerList -Text ([string]$blocker) }
  }
}
if ($targetProofWorkOrder.Count -gt 0) {
  foreach ($blocker in @(Convert-ToArray -Value $targetProofWorkOrder[0].blocked_by)) {
    if (-not [string]::IsNullOrWhiteSpace([string]$blocker)) { Add-Text -List $workOrderBlockerList -Text ([string]$blocker) }
  }
}
$workOrderBlockers = @($workOrderBlockerList | Select-Object -Unique)

$checks = @(
  (New-Check -Name "final_review_work_order_present" -Passed ($workOrder.Count -gt 0 -and [string]$workOrder[0].work_order_id -eq "WO-W66-SDXL_REALVISXL_BASE_LANE-FINAL-CERTIFICATION-REVIEW") -Observed $(if ($workOrder.Count -gt 0) { [ordered]@{ work_order_id = [string]$workOrder[0].work_order_id; status = [string]$workOrder[0].status } } else { "missing" }) -Expected "Base lane final-certification-review work order is present"),
  (New-Check -Name "generic_target_runtime_smoke_exists" -Passed ([string]$staticProof.result -eq "ec2_static_proof_recorded" -and [string]$workflowSmoke.result -eq "workflow_smoke_generation_complete" -and [string]$staticProof.lane_id -eq $LaneId -and [string]$workflowSmoke.lane_id -eq $LaneId -and [string]$staticProof.final_state -eq "stopped" -and [string]$workflowSmoke.final_state -eq "stopped" -and [bool]$workflowSmoke.generation_executed) -Observed ([ordered]@{ static_result = $staticProof.result; smoke_result = $workflowSmoke.result; static_lane = $staticProof.lane_id; smoke_lane = $workflowSmoke.lane_id; static_final_state = $staticProof.final_state; smoke_final_state = $workflowSmoke.final_state }) -Expected "W63 base target-runtime static proof and smoke exist and stopped EC2"),
  (New-Check -Name "generic_pullback_hashes_verified" -Passed ([string]$pullback.status -eq "pullback_hashes_verified" -and [bool]$pullback.hashes_verified -and @($pullback.errors).Count -eq 0) -Observed ([ordered]@{ status = $pullback.status; hashes_verified = $pullback.hashes_verified; errors = @($pullback.errors).Count }) -Expected "W63 pullback hashes verified"),
  (New-Check -Name "runtime_visual_qa_scope_is_smoke_only" -Passed ([string]$runtimeVisualQa.result -eq "pass_with_notes_for_runtime_smoke" -and [int]$runtimeVisualQa.qa_score -ge [int]$runtimeVisualQa.pass_threshold -and [string]$runtimeVisualQa.decision -match "not final portfolio/style certification") -Observed ([ordered]@{ result = $runtimeVisualQa.result; qa_score = $runtimeVisualQa.qa_score; pass_threshold = $runtimeVisualQa.pass_threshold; decision = $runtimeVisualQa.decision; defect_count = $runtimeVisualDefects.Count }) -Expected "W63 visual QA passes runtime smoke but explicitly excludes final certification"),
  (New-Check -Name "single_hand_local_qa_disallows_final" -Passed ([string]$singleHandVisualQa.overall_result -eq "pass_with_notes_local_single_hand_contact_closeup" -and -not [bool]$singleHandVisualQa.final_decision_allowed -and -not [bool]$singleHandVisualQa.qa_decision.promotion_allowed) -Observed ([ordered]@{ overall_result = $singleHandVisualQa.overall_result; final_decision_allowed = $singleHandVisualQa.final_decision_allowed; promotion_allowed = $singleHandVisualQa.qa_decision.promotion_allowed; reason = $singleHandVisualQa.qa_decision.reason }) -Expected "single-hand local QA passes with notes but blocks final decision/promotion"),
  (New-Check -Name "two_character_local_qa_disallows_final" -Passed ([string]$twoCharacterVisualQa.qa_result -eq "pass_with_notes_local_two_character_hand_to_body_first_pixel_attempt_seed7152026252_preferred" -and -not [bool]$twoCharacterVisualQa.certification_allowed) -Observed ([ordered]@{ qa_result = $twoCharacterVisualQa.qa_result; certification_allowed = $twoCharacterVisualQa.certification_allowed; remaining_risks = $twoCharacterRemainingRisks }) -Expected "two-character local QA passes with notes but disallows final certification"),
  (New-Check -Name "queue_rule_requires_no_final_promotion_from_local_samples" -Passed ($queueLane.Count -gt 0 -and $queuePromotionRule -match "Do not promote to final RealVisXL certification" -and $queuePromotionRule -match "mask-routed refine, robustness, target-runtime proof, and final certification remain separate") -Observed ([ordered]@{ status = $(if ($queueLane.Count -gt 0) { [string]$queueLane[0].status } else { "missing" }); promotion_rule = $queuePromotionRule }) -Expected "runtime queue explicitly prevents final promotion from current local samples alone")
)

$reviewDefects = New-Object System.Collections.Generic.List[string]
foreach ($missing in $missingInputs) { Add-Text -List $reviewDefects -Text $missing }
foreach ($check in $checks) {
  if ([string]$check.result -ne "pass") { Add-Text -List $reviewDefects -Text "check_failed:$($check.name)" }
}

$blockerList = New-Object System.Collections.Generic.List[string]
foreach ($blocker in @(
  "base_lane_final_review_candidate_scope_mismatch",
  "generic_w63_target_runtime_smoke_does_not_certify_current_single_hand_or_two_character_contact_candidates",
  "single_hand_contact_closeup_final_decision_allowed_false",
  "two_character_hand_to_body_certification_allowed_false",
  "mask_routed_refine_or_small_robustness_pair_missing_for_base_contact_scope",
  "full_project_certification_allowed_false"
)) {
  Add-Text -List $blockerList -Text $blocker
}
foreach ($blocker in $workOrderBlockers) {
  Add-Text -List $blockerList -Text $blocker
}
$blockers = @($blockerList | Select-Object -Unique)

$knownIssues = @(
  "W63 proves the base lane can run on target runtime and return a coherent close-face smoke image, but that QA explicitly says it is not final portfolio/style certification.",
  "W69 single-hand evidence passes only an isolated tabletop-contact close-up and explicitly blocks final decision/promotion.",
  "W69 two-character evidence is a first pixel-facing attempt after one QA-driven rerun, not multi-seed robustness or mask-routed refine.",
  "The base lane runtime queue promotion rule explicitly says not to promote final RealVisXL certification from the current local samples alone.",
  "This blocker packet does not consume candidate masks as truth, promote masks, rerun Wave70 hard gates, or activate Wave71+."
)

$result = if ($reviewDefects.Count -eq 0) { "blocked_base_lane_final_review_candidate_scope_mismatch" } else { "fail_base_lane_final_review_blocker_packet" }
$finalDecision = "blocked"

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "lane_final_review_blocker_packet"
  blocker_id = "BLOCK-W66-SDXL-BASE-LANE-FINAL-REVIEW-$(Get-Date -Format 'yyyyMMddTHHmmss-0500')"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  task_tracker_id = "WO-W66-SDXL_REALVISXL_BASE_LANE-FINAL-CERTIFICATION-REVIEW"
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
  closes_work_order = $false
  artifact_scope = "Lane-scoped final-review blocker packet for sdxl_realvisxl_base_lane."
  implementation_summary = "Reviewed W63 target-runtime smoke, pullback, W63 visual QA, W69 single-hand contact close-up QA, W69 two-character hand-to-body QA, tracker mirrors, and runtime queue promotion rule without rerunning live runtime."
  tests_performed = @($checks)
  blocker_summary = @($blockers)
  qa_summary = [ordered]@{
    runtime_visual_result = [string]$runtimeVisualQa.result
    runtime_visual_decision = [string]$runtimeVisualQa.decision
    runtime_visual_defects = @($runtimeVisualDefects)
    single_hand_result = [string]$singleHandVisualQa.overall_result
    single_hand_final_decision_allowed = [bool]$singleHandVisualQa.final_decision_allowed
    single_hand_promotion_allowed = [bool]$singleHandVisualQa.qa_decision.promotion_allowed
    single_hand_remaining_notes = @($singleHandRemainingNotes)
    two_character_result = [string]$twoCharacterVisualQa.qa_result
    two_character_certification_allowed = [bool]$twoCharacterVisualQa.certification_allowed
    two_character_remaining_risks = @($twoCharacterRemainingRisks)
    tracker_single_hand_result = [string]$singleHandTracker.result
    tracker_two_character_status = [string]$twoCharacterTracker.status
  }
  evidence_paths = [ordered]@{
    work_order = ConvertTo-ProjectRelativePath -Path $workOrderResolved
    runtime_lane_queue = ConvertTo-ProjectRelativePath -Path $queuePath
    static_proof = ConvertTo-ProjectRelativePath -Path $staticProofPath
    workflow_smoke = ConvertTo-ProjectRelativePath -Path $workflowSmokePath
    pullback_record = ConvertTo-ProjectRelativePath -Path $pullbackPath
    runtime_visual_qa = ConvertTo-ProjectRelativePath -Path $runtimeVisualQaPath
    single_hand_visual_qa = ConvertTo-ProjectRelativePath -Path $singleHandVisualQaPath
    single_hand_tracker = ConvertTo-ProjectRelativePath -Path $singleHandTrackerPath
    two_character_visual_qa = ConvertTo-ProjectRelativePath -Path $twoCharacterVisualQaPath
    two_character_tracker = ConvertTo-ProjectRelativePath -Path $twoCharacterTrackerPath
  }
  known_issues = $knownIssues
  defects = @($reviewDefects)
  certifier = "Codex Desktop autonomous release manager"
  certification_boundary = "Lane-scoped blocker review only. This does not certify full project completion, final RealVisXL base-lane quality, body-mask readiness, Wave70 mask promotion, or Wave71+ activation."
  next_action = "Do not close the base lane final-review work order from current evidence. Add mask-routed refine or a small robustness pair for the base contact scope, then obtain candidate-appropriate target-runtime proof before final-review closure."
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
$blockerLines = foreach ($blocker in $blockers) {
  "- $blocker"
}
$evidenceLines = foreach ($prop in $record.evidence_paths.GetEnumerator()) {
  "- $($prop.Name): $($prop.Value)"
}
$markdown = @"
# Base Lane Final Review Blocker Packet

- blocker_id: $($record.blocker_id)
- created_at: $($record.created_at)
- lane_id: $LaneId
- result: $result
- final_decision: $finalDecision
- closes_work_order: false
- full_project_certification_allowed: false

## Checks

$($checkLines -join "`n")

## Blockers

$($blockerLines -join "`n")

## Evidence

$($evidenceLines -join "`n")

## Boundary

$($record.certification_boundary)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

$record | ConvertTo-Json -Depth 30
if ($reviewDefects.Count -gt 0) { exit 2 }
exit 0
