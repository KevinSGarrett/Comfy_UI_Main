<#
.SYNOPSIS
Creates a lane-scoped final-review blocker packet for the RealESRGAN lane.

.DESCRIPTION
Reviews existing local upscale/polish evidence for
sdxl_realesrgan_upscale_polish_lane. The helper records why the lane cannot be
closed as a final-review packet yet: local model provisioning, local generation
smoke, strict visual QA, and pass-planner binding exist, but the lane promotion
rule and target-runtime plan still require target-runtime proof, broader
robustness, pullback, technical QA, and strict final visual QA before closure.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LaneId = "sdxl_realesrgan_upscale_polish_lane",
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
  $OutFile = "Plan\Instructions\QA\Evidence\Done_Certifications\W66_REALESRGAN_LANE_FINAL_REVIEW_BLOCKER_PACKET_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$workOrderResolved = Resolve-ProjectPath -Path $WorkOrderFile
$targetRuntimePlanResolved = Resolve-ProjectPath -Path $TargetRuntimePlanFile
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile

$queuePath = Resolve-ProjectPath -Path "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json"
$modelProvisioningPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Model_Registry/W69_LOCAL_REALESRGAN_UPSCALE_MODEL_PROVISIONING_20260707T110500-0500.json"
$runtimeExecutePath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Workflow_Runtime/W69_LOCAL_UPSCALE_POLISH_REALESRGAN_CANNY_SEED711570105_EXECUTE_20260707T111000-0500.json"
$visualQaPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Image_Artifact_QA/W69_LOCAL_UPSCALE_POLISH_REALESRGAN_CANNY_SEED711570105_VISUAL_QA_20260707T111500-0500.json"
$plannerBindingPath = Resolve-ProjectPath -Path "Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W69_LOCAL_PASS_PLANNER_CANNY_INPAINT_READINESS_P06_BOUND_20260707T112000-0500.json"
$runPackagePath = Resolve-ProjectPath -Path "runtime_artifacts/run_packages/upscale_polish_w69_canny_seed711570105/RUN_PACKAGE_MANIFEST.json"

$missingInputs = New-Object System.Collections.Generic.List[string]
foreach ($required in @(
  @{ label = "work_order"; path = $workOrderResolved },
  @{ label = "target_runtime_plan"; path = $targetRuntimePlanResolved },
  @{ label = "runtime_lane_queue"; path = $queuePath },
  @{ label = "model_provisioning"; path = $modelProvisioningPath },
  @{ label = "runtime_execute"; path = $runtimeExecutePath },
  @{ label = "visual_qa"; path = $visualQaPath },
  @{ label = "planner_binding"; path = $plannerBindingPath },
  @{ label = "run_package"; path = $runPackagePath }
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
$plannerBinding = Read-JsonFile -Path $plannerBindingPath
$runPackage = Read-JsonFile -Path $runPackagePath

$workOrder = @(Convert-ToArray -Value $workOrderRecord.work_orders | Where-Object { [string]$_.lane_id -eq $LaneId -and [string]$_.work_order_type -eq "final_certification_review_required" } | Select-Object -First 1)
$queueLane = @(Convert-ToArray -Value $queue.lanes | Where-Object { [string]$_.lane_id -eq $LaneId } | Select-Object -First 1)
$targetCandidate = @(Convert-ToArray -Value $targetRuntimePlan.target_candidates | Where-Object { [string]$_.lane_id -eq $LaneId } | Select-Object -First 1)

$queuePromotionRule = if ($queueLane.Count -gt 0) { [string]$queueLane[0].promotion_rule } else { "" }
$targetCandidateBlockers = if ($targetCandidate.Count -gt 0) { @(Convert-ToArray -Value $targetCandidate[0].blocked_by) } else { @() }
$remainingRisks = @(Convert-ToArray -Value $visualQa.remaining_risks)
$plannerRemainingGaps = @(Convert-ToArray -Value $plannerBinding.remaining_gaps)
$tradeoffs = @(Convert-ToArray -Value $visualQa.comparison_to_source.tradeoffs_or_notes)

$checks = @(
  (New-Check -Name "final_review_work_order_present" -Passed ($workOrder.Count -gt 0 -and [string]$workOrder[0].work_order_id -eq "WO-W66-SDXL_REALESRGAN_UPSCALE_POLISH_LANE-FINAL-CERTIFICATION-REVIEW") -Observed $(if ($workOrder.Count -gt 0) { [ordered]@{ work_order_id = [string]$workOrder[0].work_order_id; status = [string]$workOrder[0].status } } else { "missing" }) -Expected "RealESRGAN final-certification-review work order is present"),
  (New-Check -Name "target_runtime_plan_marks_proof_missing" -Passed ($targetCandidate.Count -gt 0 -and [bool]$targetCandidate[0].target_runtime_proof_evidence_missing -and $targetCandidateBlockers -contains "target_runtime_proof_evidence_missing") -Observed $(if ($targetCandidate.Count -gt 0) { [ordered]@{ target_runtime_proof_evidence_missing = [bool]$targetCandidate[0].target_runtime_proof_evidence_missing; selected_by_default = [bool]$targetCandidate[0].selected_by_default; blocked_by = $targetCandidateBlockers } } else { "missing" }) -Expected "target-runtime plan records missing proof for the RealESRGAN lane"),
  (New-Check -Name "queue_rule_requires_target_runtime_before_promotion" -Passed ($queueLane.Count -gt 0 -and $queuePromotionRule -match "Do not promote to final upscale/polish certification" -and $queuePromotionRule -match "Target-runtime object_info/path/hash proof" -and $queuePromotionRule -match "strict whole-image visual QA") -Observed ([ordered]@{ status = $(if ($queueLane.Count -gt 0) { [string]$queueLane[0].status } else { "missing" }); promotion_rule = $queuePromotionRule }) -Expected "runtime queue explicitly requires target-runtime proof before final upscale/polish certification"),
  (New-Check -Name "local_model_provisioning_passed_but_not_certifying" -Passed ([string]$modelProvisioning.qa_result -eq "pass_local_model_present_hash_recorded_and_runtime_loaded" -and [bool]$modelProvisioning.local_only -and -not [bool]$modelProvisioning.ec2_started -and -not [bool]$modelProvisioning.certification_allowed) -Observed ([ordered]@{ qa_result = $modelProvisioning.qa_result; local_only = $modelProvisioning.local_only; ec2_started = $modelProvisioning.ec2_started; certification_allowed = $modelProvisioning.certification_allowed }) -Expected "local RealESRGAN model provisioning passed but does not certify target runtime"),
  (New-Check -Name "local_runtime_smoke_passed" -Passed ([string]$runtimeExecute.result -eq "pass_local_run_package_generation_smoke" -and [bool]$runtimeExecute.local_only -and -not [bool]$runtimeExecute.ec2_started -and [bool]$runtimeExecute.generation_executed -and @($runtimeExecute.errors).Count -eq 0) -Observed ([ordered]@{ result = $runtimeExecute.result; local_only = $runtimeExecute.local_only; ec2_started = $runtimeExecute.ec2_started; generation_executed = $runtimeExecute.generation_executed; errors = @($runtimeExecute.errors).Count }) -Expected "local upscale/polish run package generation smoke passed"),
  (New-Check -Name "visual_qa_passes_with_notes_but_disallows_certification" -Passed ([string]$visualQa.qa_result -eq "pass_with_notes_local_realesrgan_upscale_polish_runtime_and_visual_qa" -and [bool]$visualQa.local_only -and -not [bool]$visualQa.ec2_started -and -not [bool]$visualQa.certification_allowed -and $remainingRisks -contains "No broad multi-image upscale robustness matrix was run.") -Observed ([ordered]@{ qa_result = $visualQa.qa_result; local_only = $visualQa.local_only; ec2_started = $visualQa.ec2_started; certification_allowed = $visualQa.certification_allowed; remaining_risks = $remainingRisks; tradeoffs = $tradeoffs }) -Expected "local visual QA passes with notes but explicitly disallows certification"),
  (New-Check -Name "pass_planner_p06_bound_but_target_runtime_unbound" -Passed ([string]$plannerBinding.qa_result -eq "pass_local_pass_planner_contract_p06_upscale_polish_bound_no_warnings" -and [bool]$plannerBinding.local_only -and -not [bool]$plannerBinding.evidence_boundaries.target_runtime_proof_bound -and -not [bool]$plannerBinding.certification_allowed) -Observed ([ordered]@{ qa_result = $plannerBinding.qa_result; local_only = $plannerBinding.local_only; target_runtime_proof_bound = $plannerBinding.evidence_boundaries.target_runtime_proof_bound; certification_allowed = $plannerBinding.certification_allowed; remaining_gaps = $plannerRemainingGaps }) -Expected "p06 evidence binding is cleared locally but target-runtime proof remains unbound"),
  (New-Check -Name "run_package_matches_lane" -Passed ([string]$runPackage.lane_id -eq $LaneId -and [string]$runPackage.result -eq "pass_local_only") -Observed ([ordered]@{ lane_id = $runPackage.lane_id; result = $runPackage.result }) -Expected "run package manifest belongs to the RealESRGAN lane and passed local package validation")
)

$reviewDefects = New-Object System.Collections.Generic.List[string]
foreach ($missing in $missingInputs) { Add-Text -List $reviewDefects -Text $missing }
foreach ($check in $checks) {
  if ([string]$check.result -ne "pass") { Add-Text -List $reviewDefects -Text "check_failed:$($check.name)" }
}

$blockers = @(
  "realesrgan_lane_target_runtime_proof_evidence_missing",
  "target_runtime_object_info_path_hash_proof_missing",
  "bounded_target_runtime_output_missing",
  "target_runtime_pullback_technical_visual_qa_missing",
  "single_local_upscale_sample_not_broad_robustness_matrix",
  "local_pass_with_notes_not_final_certification",
  "explicit_user_target_runtime_selection_required",
  "git_checkpoint_gate_not_clean_for_ec2_execute",
  "deploy_bundle_source_git_dirty_rebuild_required_before_ec2",
  "full_project_certification_allowed_false"
)

$knownIssues = @(
  "W69 RealESRGAN model provisioning proves local model presence and local runtime loading only.",
  "W69 local upscale/polish generation smoke proves one local source-image pass only and explicitly keeps EC2 target-runtime proof separate.",
  "W69 local visual QA passes with notes but certification_allowed is false and no broad multi-image upscale robustness matrix was run.",
  "Wave14 pass-planner p06 evidence binding is cleared locally, but target_runtime_proof_bound remains false.",
  "The RealESRGAN lane promotion rule requires target-runtime object_info/path/hash proof, bounded target-runtime generation, pullback, technical QA, strict whole-image visual QA, and final certification review before promotion."
)

$result = if ($reviewDefects.Count -eq 0) { "blocked_realesrgan_lane_final_review_target_runtime_proof_missing" } else { "fail_realesrgan_lane_final_review_blocker_packet" }
$finalDecision = "blocked"

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "lane_final_review_blocker_packet"
  blocker_id = "BLOCK-W66-SDXL-REALESRGAN-LANE-FINAL-REVIEW-$(Get-Date -Format 'yyyyMMddTHHmmss-0500')"
  created_at = (Get-Date -Format "yyyy-MM-ddTHH:mm:sszzz")
  task_tracker_id = "WO-W66-SDXL_REALESRGAN_UPSCALE_POLISH_LANE-FINAL-CERTIFICATION-REVIEW"
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
  artifact_scope = "Lane-scoped final-review blocker packet for sdxl_realesrgan_upscale_polish_lane."
  implementation_summary = "Reviewed local RealESRGAN model provisioning, local run-package generation smoke, strict visual QA, p06 pass-planner binding, target-runtime plan, and runtime queue promotion rule without rerunning live runtime."
  tests_performed = @($checks)
  blocker_summary = @($blockers)
  qa_summary = [ordered]@{
    queue_status = $(if ($queueLane.Count -gt 0) { [string]$queueLane[0].status } else { "missing" })
    target_runtime_proof_evidence_missing = $(if ($targetCandidate.Count -gt 0) { [bool]$targetCandidate[0].target_runtime_proof_evidence_missing } else { $true })
    target_candidate_blockers = @($targetCandidateBlockers)
    model_provisioning_result = [string]$modelProvisioning.qa_result
    local_runtime_result = [string]$runtimeExecute.result
    visual_qa_result = [string]$visualQa.qa_result
    visual_certification_allowed = [bool]$visualQa.certification_allowed
    visual_remaining_risks = @($remainingRisks)
    visual_tradeoffs_or_notes = @($tradeoffs)
    planner_binding_result = [string]$plannerBinding.qa_result
    planner_target_runtime_proof_bound = [bool]$plannerBinding.evidence_boundaries.target_runtime_proof_bound
    planner_remaining_gaps = @($plannerRemainingGaps)
  }
  evidence_paths = [ordered]@{
    work_order = ConvertTo-ProjectRelativePath -Path $workOrderResolved
    target_runtime_plan = ConvertTo-ProjectRelativePath -Path $targetRuntimePlanResolved
    runtime_lane_queue = ConvertTo-ProjectRelativePath -Path $queuePath
    model_provisioning = ConvertTo-ProjectRelativePath -Path $modelProvisioningPath
    runtime_execute = ConvertTo-ProjectRelativePath -Path $runtimeExecutePath
    visual_qa = ConvertTo-ProjectRelativePath -Path $visualQaPath
    planner_binding = ConvertTo-ProjectRelativePath -Path $plannerBindingPath
    run_package = ConvertTo-ProjectRelativePath -Path $runPackagePath
  }
  known_issues = $knownIssues
  defects = @($reviewDefects)
  certifier = "Codex Desktop autonomous release manager"
  certification_boundary = "Lane-scoped blocker review only. This does not certify full project completion, final RealESRGAN upscale/polish quality, target-runtime readiness, body-mask readiness, Wave70 mask promotion, or Wave71+ activation."
  next_action = "Do not close the RealESRGAN lane final-review work order from current local evidence. Target-runtime proof must be explicitly selected and pass clean Git, clean deploy-bundle, object_info/path/hash, bounded output, pullback, technical QA, strict visual QA, and robustness/final-review gates first."
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
# RealESRGAN Lane Final Review Blocker Packet

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
