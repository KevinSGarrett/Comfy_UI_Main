<#
.SYNOPSIS
Creates a lane-scoped final-review blocker packet for the Inpaint Detail lane.

.DESCRIPTION
Reviews existing local inpaint/detail and Wave25 contact-refine robustness
evidence for sdxl_realvisxl_inpaint_detail_lane. The helper records why the
lane cannot close final review yet: local QA and local object-info proof exist,
but the lane's own promotion rule requires target-runtime object_info/path/hash
input proof, bounded target-runtime output, pullback, technical QA, and strict
whole-image visual QA before final review closure.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LaneId = "sdxl_realvisxl_inpaint_detail_lane",
  [string]$WorkOrderFile = "",
  [string]$TargetRuntimePlanFile = "",
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
if ([string]::IsNullOrWhiteSpace($WorkOrderFile)) {
  $WorkOrderFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_WORK_ORDER_*.json"
}
if ([string]::IsNullOrWhiteSpace($TargetRuntimePlanFile)) {
  $TargetRuntimePlanFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_TARGET_RUNTIME_EXECUTION_PLAN_*.json"
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Done_Certifications\W66_INPAINT_LANE_FINAL_REVIEW_BLOCKER_PACKET_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$workOrderResolved = Resolve-ProjectPath -Path $WorkOrderFile
$targetRuntimePlanResolved = Resolve-ProjectPath -Path $TargetRuntimePlanFile
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile

$queuePath = Resolve-ProjectPath -Path "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json"
$nomouthVisualQaPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_INPAINT_DETAIL_NOMOUTH_V4_VISUAL_QA_20260707T035000-0500.json"
$nomouthRobustnessQaPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_INPAINT_DETAIL_NOMOUTH_V4_ROBUSTNESS_VISUAL_QA_20260707T034000-0500.json"
$maskPreviewQaPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_INPAINT_DETAIL_NOMOUTH_V4_MASK_PREVIEW_VISUAL_QA_20260707T045800-0500.json"
$objectInfoPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Runtime_Readiness/W69_LOCAL_OBJECT_INFO_INPAINT_DETAIL_NOMOUTH_V4_20260707T045500-0500.json"
$contactRefineQaPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_WAVE25_TWO_CHARACTER_CONTACT_REFINE_VISUAL_QA_20260707T120500-0500.json"
$contactRobustnessQaPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_WAVE25_TWO_CHARACTER_CONTACT_REFINE_ROBUSTNESS_VISUAL_QA_20260707T121500-0500.json"
$contactTrackerPath = Resolve-ProjectPath -Path "Plan/Tracker/Evidence/W69_LOCAL_WAVE25_TWO_CHARACTER_CONTACT_REFINE_20260707T120500-0500.json"
$contactRobustnessTrackerPath = Resolve-ProjectPath -Path "Plan/Tracker/Evidence/W69_LOCAL_WAVE25_TWO_CHARACTER_CONTACT_REFINE_ROBUSTNESS_20260707T121500-0500.json"

$missingInputs = New-Object System.Collections.Generic.List[string]
foreach ($required in @(
  @{ label = "work_order"; path = $workOrderResolved },
  @{ label = "target_runtime_plan"; path = $targetRuntimePlanResolved },
  @{ label = "runtime_lane_queue"; path = $queuePath },
  @{ label = "nomouth_visual_qa"; path = $nomouthVisualQaPath },
  @{ label = "nomouth_robustness_qa"; path = $nomouthRobustnessQaPath },
  @{ label = "mask_preview_qa"; path = $maskPreviewQaPath },
  @{ label = "object_info"; path = $objectInfoPath },
  @{ label = "contact_refine_qa"; path = $contactRefineQaPath },
  @{ label = "contact_robustness_qa"; path = $contactRobustnessQaPath },
  @{ label = "contact_tracker"; path = $contactTrackerPath },
  @{ label = "contact_robustness_tracker"; path = $contactRobustnessTrackerPath }
)) {
  if ([string]::IsNullOrWhiteSpace([string]$required.path) -or -not (Test-Path -LiteralPath $required.path -PathType Leaf)) {
    Add-Text -List $missingInputs -Text "missing_required_input:$($required.label)"
  }
}

$workOrderRecord = Read-JsonFile -Path $workOrderResolved
$targetRuntimePlan = Read-JsonFile -Path $targetRuntimePlanResolved
$queue = Read-JsonFile -Path $queuePath
$nomouthVisualQa = Read-JsonFile -Path $nomouthVisualQaPath
$nomouthRobustnessQa = Read-JsonFile -Path $nomouthRobustnessQaPath
$maskPreviewQa = Read-JsonFile -Path $maskPreviewQaPath
$objectInfo = Read-JsonFile -Path $objectInfoPath
$contactRefineQa = Read-JsonFile -Path $contactRefineQaPath
$contactRobustnessQa = Read-JsonFile -Path $contactRobustnessQaPath
$contactTracker = Read-JsonFile -Path $contactTrackerPath
$contactRobustnessTracker = Read-JsonFile -Path $contactRobustnessTrackerPath

$workOrder = @(Convert-ToArray -Value $workOrderRecord.work_orders | Where-Object { [string]$_.lane_id -eq $LaneId -and [string]$_.work_order_type -eq "final_certification_review_required" } | Select-Object -First 1)
$queueLane = @(Convert-ToArray -Value $queue.lanes | Where-Object { [string]$_.lane_id -eq $LaneId } | Select-Object -First 1)
$targetCandidate = @(Convert-ToArray -Value $targetRuntimePlan.target_candidates | Where-Object { [string]$_.lane_id -eq $LaneId } | Select-Object -First 1)

$queuePromotionRule = if ($queueLane.Count -gt 0) { [string]$queueLane[0].promotion_rule } else { "" }
$targetCandidateBlockers = if ($targetCandidate.Count -gt 0) { @(Convert-ToArray -Value $targetCandidate[0].blocked_by) } else { @() }
$contactFailures = @(Convert-ToArray -Value $contactRefineQa.whole_image_visual_qa.failures)
$contactRobustnessFailures = @(Convert-ToArray -Value $contactRobustnessQa.whole_image_visual_qa.failures)
$contactRobustnessNotes = @(Convert-ToArray -Value $contactRobustnessQa.whole_image_visual_qa.notes)

$checks = @(
  (New-Check -Name "final_review_work_order_present" -Passed ($workOrder.Count -gt 0 -and [string]$workOrder[0].work_order_id -eq "WO-W66-SDXL_REALVISXL_INPAINT_DETAIL_LANE-FINAL-CERTIFICATION-REVIEW") -Observed $(if ($workOrder.Count -gt 0) { [ordered]@{ work_order_id = [string]$workOrder[0].work_order_id; status = [string]$workOrder[0].status } } else { "missing" }) -Expected "Inpaint final-certification-review work order is present"),
  (New-Check -Name "target_runtime_plan_marks_proof_missing" -Passed ($targetCandidate.Count -gt 0 -and [bool]$targetCandidate[0].target_runtime_proof_evidence_missing -and $targetCandidateBlockers -contains "target_runtime_proof_evidence_missing") -Observed $(if ($targetCandidate.Count -gt 0) { [ordered]@{ target_runtime_proof_evidence_missing = [bool]$targetCandidate[0].target_runtime_proof_evidence_missing; selected_by_default = [bool]$targetCandidate[0].selected_by_default; blocked_by = $targetCandidateBlockers } } else { "missing" }) -Expected "target-runtime plan records missing proof for the inpaint lane"),
  (New-Check -Name "queue_rule_requires_target_runtime_before_promotion" -Passed ($queueLane.Count -gt 0 -and $queuePromotionRule -match "Do not promote to target-runtime proven" -and $queuePromotionRule -match "target-runtime object_info/path/hash/input proof" -and $queuePromotionRule -match "bounded target-runtime output") -Observed ([ordered]@{ status = $(if ($queueLane.Count -gt 0) { [string]$queueLane[0].status } else { "missing" }); promotion_rule = $queuePromotionRule }) -Expected "runtime queue explicitly requires target-runtime proof before promotion"),
  (New-Check -Name "nomouth_v4_local_iteration_passed" -Passed ([string]$nomouthVisualQa.strict_qa_result -eq "pass_with_notes_for_local_iteration" -and [string]$nomouthVisualQa.certification_status -eq "local_iteration_pass_with_notes_not_target_runtime_certified" -and [bool]$nomouthVisualQa.local_only -and -not [bool]$nomouthVisualQa.ec2_started) -Observed ([ordered]@{ strict_qa_result = $nomouthVisualQa.strict_qa_result; certification_status = $nomouthVisualQa.certification_status; local_only = $nomouthVisualQa.local_only; ec2_started = $nomouthVisualQa.ec2_started }) -Expected "local no-mouth v4 passes as local iteration only"),
  (New-Check -Name "nomouth_v4_local_robustness_passed_with_notes" -Passed ([string]$nomouthRobustnessQa.overall_result -eq "pass_with_notes_for_local_robustness" -and [bool]$nomouthRobustnessQa.local_only -and -not [bool]$nomouthRobustnessQa.ec2_started) -Observed ([ordered]@{ overall_result = $nomouthRobustnessQa.overall_result; local_only = $nomouthRobustnessQa.local_only; ec2_started = $nomouthRobustnessQa.ec2_started }) -Expected "local no-mouth robustness passes with notes only"),
  (New-Check -Name "local_object_info_passed_but_local_only" -Passed ([string]$objectInfo.result -eq "pass_local_object_info_model_input_hash_proof" -and [bool]$objectInfo.local_only -and -not [bool]$objectInfo.ec2_started -and -not [bool]$objectInfo.generation_executed) -Observed ([ordered]@{ result = $objectInfo.result; local_only = $objectInfo.local_only; ec2_started = $objectInfo.ec2_started; generation_executed = $objectInfo.generation_executed }) -Expected "local object-info/hash proof exists but is local-only"),
  (New-Check -Name "contact_refine_passed_local_only_no_final_cert" -Passed ([string]$contactRefineQa.whole_image_visual_qa.result -eq "pass_with_notes_local_wave25_contact_refine_seed210701_improved_contact_boundary" -and [bool]$contactRefineQa.local_only -and -not [bool]$contactRefineQa.ec2_started -and -not [bool]$contactRefineQa.qa_decision.final_certification_allowed -and $contactFailures.Count -eq 0) -Observed ([ordered]@{ result = $contactRefineQa.whole_image_visual_qa.result; local_only = $contactRefineQa.local_only; ec2_started = $contactRefineQa.ec2_started; final_certification_allowed = $contactRefineQa.qa_decision.final_certification_allowed; failures = $contactFailures.Count }) -Expected "contact refine passes local-only but blocks final certification"),
  (New-Check -Name "contact_refine_robustness_passed_local_only_no_final_cert" -Passed ([string]$contactRobustnessQa.whole_image_visual_qa.result -eq "pass_with_notes_local_wave25_contact_refine_robustness_pair_stable" -and [bool]$contactRobustnessQa.local_only -and -not [bool]$contactRobustnessQa.ec2_started -and -not [bool]$contactRobustnessQa.qa_decision.final_certification_allowed -and $contactRobustnessFailures.Count -eq 0) -Observed ([ordered]@{ result = $contactRobustnessQa.whole_image_visual_qa.result; local_only = $contactRobustnessQa.local_only; ec2_started = $contactRobustnessQa.ec2_started; final_certification_allowed = $contactRobustnessQa.qa_decision.final_certification_allowed; failures = $contactRobustnessFailures.Count; notes = $contactRobustnessNotes }) -Expected "contact robustness passes local-only but blocks final certification"),
  (New-Check -Name "tracker_records_local_iterations_only" -Passed ([string]$contactTracker.status -eq "pass_with_notes_local_iteration" -and [string]$contactRobustnessTracker.status -eq "pass_with_notes_local_iteration") -Observed ([ordered]@{ contact_status = $contactTracker.status; robustness_status = $contactRobustnessTracker.status }) -Expected "tracker mirrors classify contact refine evidence as local iterations")
)

$reviewDefects = New-Object System.Collections.Generic.List[string]
foreach ($missing in $missingInputs) { Add-Text -List $reviewDefects -Text $missing }
foreach ($check in $checks) {
  if ([string]$check.result -ne "pass") { Add-Text -List $reviewDefects -Text "check_failed:$($check.name)" }
}

$blockers = @(
  "inpaint_lane_target_runtime_proof_evidence_missing",
  "target_runtime_object_info_path_hash_input_proof_missing",
  "bounded_target_runtime_output_missing",
  "target_runtime_pullback_technical_visual_qa_missing",
  "local_pass_with_notes_not_final_certification",
  "explicit_user_target_runtime_selection_required",
  "git_checkpoint_gate_not_clean_for_ec2_execute",
  "deploy_bundle_source_git_dirty_rebuild_required_before_ec2",
  "full_project_certification_allowed_false"
)

$knownIssues = @(
  "W69 no-mouth v4 and mask preview evidence are local iterations and explicitly not target-runtime certification.",
  "W69 Wave25 contact refine and robustness evidence pass local-only with notes but explicitly keep final certification disabled.",
  "The inpaint lane promotion rule requires target-runtime object_info/path/hash/input proof, bounded target-runtime output, pullback, technical QA, and strict whole-image visual QA.",
  "The current target-runtime execution plan marks inpaint target-runtime proof evidence as missing and execution blocked by explicit selection plus dirty Git/deploy bundle gates.",
  "This blocker packet does not consume candidate masks as truth, promote masks, rerun Wave70 hard gates, or activate Wave71+."
)

$result = if ($reviewDefects.Count -eq 0) { "blocked_inpaint_lane_final_review_target_runtime_proof_missing" } else { "fail_inpaint_lane_final_review_blocker_packet" }
$finalDecision = "blocked"

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "lane_final_review_blocker_packet"
  blocker_id = "BLOCK-W66-SDXL-INPAINT-LANE-FINAL-REVIEW-$(Get-Date -Format 'yyyyMMddTHHmmss-0500')"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  task_tracker_id = "WO-W66-SDXL_REALVISXL_INPAINT_DETAIL_LANE-FINAL-CERTIFICATION-REVIEW"
  lane_id = $LaneId
  result = $result
  final_decision = $finalDecision
  local_only = $true
  new_ec2_started = $false
  new_generation_executed = $false
  historical_ec2_started = $false
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
  artifact_scope = "Lane-scoped final-review blocker packet for sdxl_realvisxl_inpaint_detail_lane."
  implementation_summary = "Reviewed local inpaint/detail no-mouth v4, local object-info, mask preview, Wave25 contact refine, contact robustness, tracker mirrors, target-runtime plan, and runtime queue promotion rule without rerunning live runtime."
  tests_performed = @($checks)
  blocker_summary = @($blockers)
  qa_summary = [ordered]@{
    queue_status = $(if ($queueLane.Count -gt 0) { [string]$queueLane[0].status } else { "missing" })
    target_runtime_proof_evidence_missing = $(if ($targetCandidate.Count -gt 0) { [bool]$targetCandidate[0].target_runtime_proof_evidence_missing } else { $true })
    target_candidate_blockers = @($targetCandidateBlockers)
    nomouth_v4_strict_qa_result = [string]$nomouthVisualQa.strict_qa_result
    nomouth_v4_certification_status = [string]$nomouthVisualQa.certification_status
    contact_refine_result = [string]$contactRefineQa.whole_image_visual_qa.result
    contact_refine_final_certification_allowed = [bool]$contactRefineQa.qa_decision.final_certification_allowed
    contact_robustness_result = [string]$contactRobustnessQa.whole_image_visual_qa.result
    contact_robustness_final_certification_allowed = [bool]$contactRobustnessQa.qa_decision.final_certification_allowed
    contact_robustness_notes = @($contactRobustnessNotes)
  }
  evidence_paths = [ordered]@{
    work_order = ConvertTo-ProjectRelativePath -Path $workOrderResolved
    target_runtime_plan = ConvertTo-ProjectRelativePath -Path $targetRuntimePlanResolved
    runtime_lane_queue = ConvertTo-ProjectRelativePath -Path $queuePath
    nomouth_visual_qa = ConvertTo-ProjectRelativePath -Path $nomouthVisualQaPath
    nomouth_robustness_qa = ConvertTo-ProjectRelativePath -Path $nomouthRobustnessQaPath
    mask_preview_qa = ConvertTo-ProjectRelativePath -Path $maskPreviewQaPath
    object_info = ConvertTo-ProjectRelativePath -Path $objectInfoPath
    contact_refine_qa = ConvertTo-ProjectRelativePath -Path $contactRefineQaPath
    contact_robustness_qa = ConvertTo-ProjectRelativePath -Path $contactRobustnessQaPath
    contact_tracker = ConvertTo-ProjectRelativePath -Path $contactTrackerPath
    contact_robustness_tracker = ConvertTo-ProjectRelativePath -Path $contactRobustnessTrackerPath
  }
  known_issues = $knownIssues
  defects = @($reviewDefects)
  certifier = "Codex Desktop autonomous release manager"
  certification_boundary = "Lane-scoped blocker review only. This does not certify full project completion, final inpaint/detail quality, body-mask readiness, Wave70 mask promotion, or Wave71+ activation."
  next_action = "Do not close the inpaint lane final-review work order from current local evidence. Target-runtime proof must be explicitly selected and pass clean Git, clean deploy-bundle, object_info/path/hash/input, bounded output, pullback, technical QA, and strict visual QA gates first."
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
# Inpaint Lane Final Review Blocker Packet

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
