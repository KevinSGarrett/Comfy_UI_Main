<#
.SYNOPSIS
Creates a lane-scoped final-review blocker packet for the ControlNet Normal lane.

.DESCRIPTION
Reviews existing local Normal v3 and local robustness evidence for
sdxl_realvisxl_controlnet_normal_lane. The helper records why the lane cannot be
closed as a final-review packet yet: local model proof, local generation smoke,
preferred v3 QA, and three-sample robustness exist, but target-runtime proof,
strict whole-image QA, and final Normal certification remain separate gates.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LaneId = "sdxl_realvisxl_controlnet_normal_lane",
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
  $OutFile = "Plan\Instructions\QA\Evidence\Done_Certifications\W66_NORMAL_LANE_FINAL_REVIEW_BLOCKER_PACKET_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$workOrderResolved = Resolve-ProjectPath -Path $WorkOrderFile
$targetRuntimePlanResolved = Resolve-ProjectPath -Path $TargetRuntimePlanFile
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile

$queuePath = Resolve-ProjectPath -Path "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json"
$modelProvisioningPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Model_Registry/W69_LOCAL_CONTROLNET_NORMAL_MODEL_PROVISIONING_20260707T063400-0500.json"
$runtimeExecutePath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Workflow_Runtime/W69_LOCAL_NORMAL_V3_OXFORD_EXECUTE_20260707T075400-0500.json"
$visualQaPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_NORMAL_V3_OXFORD_VISUAL_QA_20260707T075600-0500.json"
$robustnessQaPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_NORMAL_V3_MULTISEED_ROBUSTNESS_VISUAL_QA_20260707T080600-0500.json"
$trackerFollowupPath = Resolve-ProjectPath -Path "Plan/Tracker/Evidence/W69_LOCAL_NORMAL_V3_FOLLOWUP_20260707T075600-0500.json"
$trackerRobustnessPath = Resolve-ProjectPath -Path "Plan/Tracker/Evidence/W69_LOCAL_NORMAL_V3_MULTISEED_ROBUSTNESS_20260707T080600-0500.json"

$missingInputs = New-Object System.Collections.Generic.List[string]
foreach ($required in @(
  @{ label = "work_order"; path = $workOrderResolved },
  @{ label = "target_runtime_plan"; path = $targetRuntimePlanResolved },
  @{ label = "runtime_lane_queue"; path = $queuePath },
  @{ label = "model_provisioning"; path = $modelProvisioningPath },
  @{ label = "runtime_execute"; path = $runtimeExecutePath },
  @{ label = "visual_qa"; path = $visualQaPath },
  @{ label = "robustness_qa"; path = $robustnessQaPath },
  @{ label = "tracker_followup"; path = $trackerFollowupPath },
  @{ label = "tracker_robustness"; path = $trackerRobustnessPath }
)) {
  if ([string]::IsNullOrWhiteSpace([string]$required.path) -or -not (Test-Path -LiteralPath $required.path -PathType Leaf)) {
    Add-Text -List $missingInputs -Text "missing_required_input:$($required.label)"
  }
}

$workOrderRecord = Read-JsonFile -Path $workOrderResolved
$targetRuntimePlan = Read-JsonFile -Path $targetRuntimePlanResolved
$queue = Read-JsonFile -Path $queuePath
$modelProvisioning = Read-JsonFile -Path $modelProvisioningPath
$runtimeExecute = Read-JsonFile -Path $runtimeExecutePath
$visualQa = Read-JsonFile -Path $visualQaPath
$robustnessQa = Read-JsonFile -Path $robustnessQaPath
$trackerFollowup = Read-JsonFile -Path $trackerFollowupPath
$trackerRobustness = Read-JsonFile -Path $trackerRobustnessPath

$workOrder = @(Convert-ToArray -Value $workOrderRecord.work_orders | Where-Object { [string]$_.lane_id -eq $LaneId -and [string]$_.work_order_type -eq "final_certification_review_required" } | Select-Object -First 1)
$queueLane = @(Convert-ToArray -Value $queue.lanes | Where-Object { [string]$_.lane_id -eq $LaneId } | Select-Object -First 1)
$targetCandidate = @(Convert-ToArray -Value $targetRuntimePlan.target_candidates | Where-Object { [string]$_.lane_id -eq $LaneId } | Select-Object -First 1)

$queuePromotionRule = if ($queueLane.Count -gt 0) { [string]$queueLane[0].promotion_rule } else { "" }
$targetCandidateBlockers = if ($targetCandidate.Count -gt 0) { @(Convert-ToArray -Value $targetCandidate[0].blocked_by) } else { @() }
$visualBlockingDefects = @(Convert-ToArray -Value $visualQa.blocking_defects)
$visualRemainingRisks = @(Convert-ToArray -Value $visualQa.remaining_risks)
$robustnessBlockingDefects = @(Convert-ToArray -Value $robustnessQa.blocking_defects)
$robustnessRemainingRisks = @(Convert-ToArray -Value $robustnessQa.remaining_risks)
$sampleResults = @(Convert-ToArray -Value $robustnessQa.sample_results)

$checks = @(
  (New-Check -Name "final_review_work_order_present" -Passed ($workOrder.Count -gt 0 -and [string]$workOrder[0].work_order_id -eq "WO-W66-SDXL_REALVISXL_CONTROLNET_NORMAL_LANE-FINAL-CERTIFICATION-REVIEW") -Observed $(if ($workOrder.Count -gt 0) { [ordered]@{ work_order_id = [string]$workOrder[0].work_order_id; status = [string]$workOrder[0].status } } else { "missing" }) -Expected "Normal final-certification-review work order is present"),
  (New-Check -Name "target_runtime_plan_marks_proof_missing" -Passed ($targetCandidate.Count -gt 0 -and [bool]$targetCandidate[0].target_runtime_proof_evidence_missing -and $targetCandidateBlockers -contains "target_runtime_proof_evidence_missing") -Observed $(if ($targetCandidate.Count -gt 0) { [ordered]@{ target_runtime_proof_evidence_missing = [bool]$targetCandidate[0].target_runtime_proof_evidence_missing; selected_by_default = [bool]$targetCandidate[0].selected_by_default; blocked_by = $targetCandidateBlockers } } else { "missing" }) -Expected "target-runtime plan records missing proof for the Normal lane"),
  (New-Check -Name "queue_rule_requires_target_runtime_before_promotion" -Passed ($queueLane.Count -gt 0 -and $queuePromotionRule -match "Do not promote to target-runtime proven or final normal certification" -and $queuePromotionRule -match "Target-runtime object_info/path/hash/input proof" -and $queuePromotionRule -match "strict whole-image visual QA") -Observed ([ordered]@{ status = $(if ($queueLane.Count -gt 0) { [string]$queueLane[0].status } else { "missing" }); promotion_rule = $queuePromotionRule }) -Expected "runtime queue explicitly requires target-runtime proof before final Normal certification"),
  (New-Check -Name "local_normal_model_hash_verified" -Passed ([string]$modelProvisioning.result -eq "pass_local_model_download_hash_verified" -and [bool]$modelProvisioning.local_only -and -not [bool]$modelProvisioning.ec2_started -and -not [string]::IsNullOrWhiteSpace([string]$modelProvisioning.model.sha256)) -Observed ([ordered]@{ result = $modelProvisioning.result; local_only = $modelProvisioning.local_only; ec2_started = $modelProvisioning.ec2_started; model_sha256 = $modelProvisioning.model.sha256 }) -Expected "local Normal ControlNet model hash proof exists"),
  (New-Check -Name "local_normal_v3_runtime_smoke_passed" -Passed ([string]$runtimeExecute.result -eq "pass_local_run_package_generation_smoke" -and [bool]$runtimeExecute.local_only -and -not [bool]$runtimeExecute.ec2_started -and [bool]$runtimeExecute.generation_executed -and @($runtimeExecute.errors).Count -eq 0) -Observed ([ordered]@{ result = $runtimeExecute.result; local_only = $runtimeExecute.local_only; ec2_started = $runtimeExecute.ec2_started; generation_executed = $runtimeExecute.generation_executed; errors = @($runtimeExecute.errors).Count; run_package_lane = $runtimeExecute.run_package.lane_id }) -Expected "local Normal v3 run package generation smoke passed"),
  (New-Check -Name "normal_v3_visual_qa_passes_but_disallows_certification" -Passed ([string]$visualQa.qa_result -eq "pass_with_notes_promote_as_preferred_local_normal_candidate" -and [bool]$visualQa.local_only -and -not [bool]$visualQa.ec2_started -and -not [bool]$visualQa.certification_allowed -and $visualBlockingDefects.Count -eq 0) -Observed ([ordered]@{ qa_result = $visualQa.qa_result; local_only = $visualQa.local_only; ec2_started = $visualQa.ec2_started; certification_allowed = $visualQa.certification_allowed; blocking_defects = $visualBlockingDefects.Count; remaining_risks = $visualRemainingRisks }) -Expected "Normal v3 local visual QA passes with notes but explicitly disallows certification"),
  (New-Check -Name "normal_v3_multiseed_robustness_passes_but_disallows_certification" -Passed ([string]$robustnessQa.qa_result -eq "pass_with_notes_local_normal_v3_multiseed_robustness" -and [bool]$robustnessQa.local_only -and -not [bool]$robustnessQa.ec2_started -and -not [bool]$robustnessQa.certification_allowed -and $robustnessBlockingDefects.Count -eq 0 -and $sampleResults.Count -eq 3) -Observed ([ordered]@{ qa_result = $robustnessQa.qa_result; local_only = $robustnessQa.local_only; ec2_started = $robustnessQa.ec2_started; certification_allowed = $robustnessQa.certification_allowed; blocking_defects = $robustnessBlockingDefects.Count; robustness_scope = $robustnessQa.robustness_scope; sample_count = $sampleResults.Count; remaining_risks = $robustnessRemainingRisks }) -Expected "Normal v3 local robustness passes with notes but explicitly disallows certification"),
  (New-Check -Name "tracker_records_local_normal_iterations" -Passed ([string]$trackerFollowup.lane_id -eq $LaneId -and [string]$trackerRobustness.lane_id -eq $LaneId -and [string]$trackerFollowup.result -eq "pass_with_notes_promote_as_preferred_local_normal_candidate" -and [string]$trackerRobustness.result -eq "pass_with_notes_local_normal_v3_multiseed_robustness" -and [string]$trackerRobustness.remaining_boundary -match "not final normal lane certification") -Observed ([ordered]@{ followup_lane = $trackerFollowup.lane_id; followup_result = $trackerFollowup.result; robustness_lane = $trackerRobustness.lane_id; robustness_result = $trackerRobustness.result; robustness_boundary = $trackerRobustness.remaining_boundary }) -Expected "tracker mirrors classify Normal evidence as local pass-with-notes iteration")
)

$reviewDefects = New-Object System.Collections.Generic.List[string]
foreach ($missing in $missingInputs) { Add-Text -List $reviewDefects -Text $missing }
foreach ($check in $checks) {
  if ([string]$check.result -ne "pass") { Add-Text -List $reviewDefects -Text "check_failed:$($check.name)" }
}

$blockers = @(
  "normal_lane_target_runtime_proof_evidence_missing",
  "target_runtime_object_info_path_hash_input_proof_missing",
  "bounded_target_runtime_output_missing",
  "target_runtime_pullback_technical_visual_qa_missing",
  "local_three_sample_robustness_not_final_normal_certification",
  "full_body_hands_contact_and_broader_surface_robustness_not_certified",
  "mild_skin_polish_and_small_artifact_notes_not_final_certification",
  "local_pass_with_notes_not_final_certification",
  "explicit_user_target_runtime_selection_required",
  "git_checkpoint_gate_not_clean_for_ec2_execute",
  "deploy_bundle_source_git_dirty_rebuild_required_before_ec2",
  "full_project_certification_allowed_false"
)

$knownIssues = @(
  "W69 Normal model provisioning proves local model hash only.",
  "W69 Normal v3 visual QA passes a local head-and-shoulders candidate with notes, but certification_allowed is false.",
  "W69 Normal v3 three-sample robustness passes locally with notes, but hands, full-body anatomy, contact points, broader surface robustness, and target-runtime behavior remain uncertified.",
  "The Normal lane promotion rule requires target-runtime object_info/path/hash/input proof, bounded target-runtime generation, pullback, technical QA, strict whole-image visual QA, and final certification review before promotion.",
  "This blocker packet does not consume candidate masks as truth, promote masks, rerun Wave70 hard gates, or activate Wave71+."
)

$result = if ($reviewDefects.Count -eq 0) { "blocked_normal_lane_final_review_target_runtime_proof_missing" } else { "fail_normal_lane_final_review_blocker_packet" }
$finalDecision = "blocked"

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "lane_final_review_blocker_packet"
  blocker_id = "BLOCK-W66-SDXL-NORMAL-LANE-FINAL-REVIEW-$(Get-Date -Format 'yyyyMMddTHHmmss-0500')"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  task_tracker_id = "WO-W66-SDXL_REALVISXL_CONTROLNET_NORMAL_LANE-FINAL-CERTIFICATION-REVIEW"
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
  artifact_scope = "Lane-scoped final-review blocker packet for sdxl_realvisxl_controlnet_normal_lane."
  implementation_summary = "Reviewed local Normal model hash proof, local v3 run-package generation smoke, preferred v3 visual QA, three-sample robustness QA, tracker mirrors, target-runtime plan, and runtime queue promotion rule without rerunning live runtime."
  tests_performed = @($checks)
  blocker_summary = @($blockers)
  qa_summary = [ordered]@{
    queue_status = $(if ($queueLane.Count -gt 0) { [string]$queueLane[0].status } else { "missing" })
    target_runtime_proof_evidence_missing = $(if ($targetCandidate.Count -gt 0) { [bool]$targetCandidate[0].target_runtime_proof_evidence_missing } else { $true })
    target_candidate_blockers = @($targetCandidateBlockers)
    model_provisioning_result = [string]$modelProvisioning.result
    local_runtime_result = [string]$runtimeExecute.result
    visual_qa_result = [string]$visualQa.qa_result
    visual_certification_allowed = [bool]$visualQa.certification_allowed
    visual_remaining_risks = @($visualRemainingRisks)
    robustness_qa_result = [string]$robustnessQa.qa_result
    robustness_certification_allowed = [bool]$robustnessQa.certification_allowed
    robustness_scope = [string]$robustnessQa.robustness_scope
    robustness_remaining_risks = @($robustnessRemainingRisks)
  }
  evidence_paths = [ordered]@{
    work_order = ConvertTo-ProjectRelativePath -Path $workOrderResolved
    target_runtime_plan = ConvertTo-ProjectRelativePath -Path $targetRuntimePlanResolved
    runtime_lane_queue = ConvertTo-ProjectRelativePath -Path $queuePath
    model_provisioning = ConvertTo-ProjectRelativePath -Path $modelProvisioningPath
    runtime_execute = ConvertTo-ProjectRelativePath -Path $runtimeExecutePath
    visual_qa = ConvertTo-ProjectRelativePath -Path $visualQaPath
    robustness_qa = ConvertTo-ProjectRelativePath -Path $robustnessQaPath
    tracker_followup = ConvertTo-ProjectRelativePath -Path $trackerFollowupPath
    tracker_robustness = ConvertTo-ProjectRelativePath -Path $trackerRobustnessPath
  }
  known_issues = $knownIssues
  defects = @($reviewDefects)
  certifier = "Codex Desktop autonomous release manager"
  certification_boundary = "Lane-scoped blocker review only. This does not certify full project completion, final Normal lane quality, target-runtime readiness, body-mask readiness, Wave70 mask promotion, or Wave71+ activation."
  next_action = "Do not close the Normal lane final-review work order from current local evidence. Target-runtime proof must be explicitly selected and pass clean Git, clean deploy-bundle, object_info/path/hash/input, bounded output, pullback, technical QA, strict visual QA, and final certification gates first."
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
# Normal Lane Final Review Blocker Packet

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
