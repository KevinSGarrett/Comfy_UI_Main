<#
.SYNOPSIS
Creates a local-only target-runtime execution plan from the active final-certification work-order rollup.

.DESCRIPTION
Selects the next target-runtime proof candidate from the closure rollup using
runtime queue order and target-runtime-proof-missing blockers, then emits an
exact gated command plan. The output is a plan only: it does not contact AWS,
GitHub, Civitai, S3, ComfyUI, or EC2, does not execute generation, does not
write an active runtime marker, and does not certify final quality.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$ClosureRollupFile = "",
  [string]$RuntimeQueueFile = "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\runtime_lane_queue.json",
  [string]$ActiveLanesFile = "Workflows\base_generation\ACTIVE_LANES.json",
  [string]$GitCheckpointGateFile = "",
  [string]$S3TransferReadinessFile = "",
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

function New-CommandStep {
  param(
    [string]$Name,
    [string]$Gate,
    [string]$Command,
    [string]$ExpectedEvidence,
    [string]$WhenToRun,
    [bool]$ExecuteAllowedNow = $false
  )

  return [pscustomobject][ordered]@{
    name = $Name
    gate = $Gate
    command = $Command
    expected_evidence = $ExpectedEvidence
    when_to_run = $WhenToRun
    execute_allowed_now = $ExecuteAllowedNow
  }
}

$qaRoot = Resolve-ProjectPath -Path "Plan\Instructions\QA\Evidence"
$runtimeReadinessDir = Join-Path $qaRoot "Runtime_Readiness"
$gitVerificationDir = Join-Path $qaRoot "Git_Verification"
$operationsStaticDir = Join-Path $qaRoot "Operations_Static_Validation"

if ([string]::IsNullOrWhiteSpace($ClosureRollupFile)) {
  $ClosureRollupFile = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_CLOSURE_ROLLUP_*.json"
}
if ([string]::IsNullOrWhiteSpace($GitCheckpointGateFile)) {
  $GitCheckpointGateFile = Find-LatestFile -Directory $gitVerificationDir -Filter "W66_GITHUB_CHECKPOINT_DRY_RUN_JSON_GATE_*.json"
}
if ([string]::IsNullOrWhiteSpace($S3TransferReadinessFile)) {
  $S3TransferReadinessFile = Find-LatestFile -Directory $operationsStaticDir -Filter "W66_S3_RUNTIME_TRANSFER_READINESS_CURRENT_ACTIVE_LANES_*.json"
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
  $OutFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_ACTIVE_RUNTIME_QUEUE_TARGET_RUNTIME_EXECUTION_PLAN_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$closureResolved = Resolve-ProjectPath -Path $ClosureRollupFile
$runtimeQueueResolved = Resolve-ProjectPath -Path $RuntimeQueueFile
$activeLanesResolved = Resolve-ProjectPath -Path $ActiveLanesFile
$gitGateResolved = Resolve-ProjectPath -Path $GitCheckpointGateFile
$s3ReadinessResolved = Resolve-ProjectPath -Path $S3TransferReadinessFile
$outFileResolved = Resolve-ProjectPath -Path $OutFile
$markdownResolved = Resolve-ProjectPath -Path $MarkdownOutFile

foreach ($required in @(
  @{ label = "closure_rollup"; path = $closureResolved },
  @{ label = "runtime_queue"; path = $runtimeQueueResolved },
  @{ label = "active_lanes"; path = $activeLanesResolved },
  @{ label = "git_checkpoint_gate"; path = $gitGateResolved },
  @{ label = "s3_transfer_readiness"; path = $s3ReadinessResolved }
)) {
  if ([string]::IsNullOrWhiteSpace([string]$required.path) -or -not (Test-Path -LiteralPath $required.path -PathType Leaf)) {
    throw "Required input missing: $($required.label)"
  }
}

$closure = Read-JsonFile -Path $closureResolved
$workOrderManifestPath = Resolve-ProjectPath -Path $closure.source_work_order_manifest
if ([string]::IsNullOrWhiteSpace($workOrderManifestPath) -or -not (Test-Path -LiteralPath $workOrderManifestPath -PathType Leaf)) {
  throw "Source work-order manifest from closure rollup not found."
}
$workOrderManifest = Read-JsonFile -Path $workOrderManifestPath
$runtimeQueue = Read-JsonFile -Path $runtimeQueueResolved
$activeLanes = Read-JsonFile -Path $activeLanesResolved
$gitGate = Read-JsonFile -Path $gitGateResolved
$s3Readiness = Read-JsonFile -Path $s3ReadinessResolved

$queueOrder = @{}
foreach ($lane in @(Convert-ToArray -Value $runtimeQueue.lanes)) {
  $queueOrder[[string]$lane.lane_id] = [int]$lane.order
}

$workOrdersById = @{}
foreach ($order in @(Convert-ToArray -Value $workOrderManifest.work_orders)) {
  $workOrdersById[[string]$order.work_order_id] = $order
}

$targetCandidates = foreach ($entry in @(Convert-ToArray -Value $closure.rollup_entries)) {
  if ([bool]$entry.closed -or [string]$entry.work_order_type -ne "target_runtime_proof_required") { continue }
  $id = [string]$entry.work_order_id
  $manifestOrder = if ($workOrdersById.ContainsKey($id)) { $workOrdersById[$id] } else { $null }
  $blockedBy = @(Convert-ToArray -Value $(if ($null -ne $manifestOrder) { $manifestOrder.blocked_by } else { @() }) | ForEach-Object { [string]$_ })
  $requiresMissingTargetProof = @($blockedBy | Where-Object { $_ -eq "target_runtime_proof_evidence_missing" }).Count -gt 0
  $laneId = [string]$entry.lane_id
  $laneQueueOrder = if ($queueOrder.ContainsKey($laneId)) { [int]$queueOrder[$laneId] } else { 9999 }
  [pscustomobject][ordered]@{
    work_order_id = $id
    lane_id = $laneId
    queue_order = $laneQueueOrder
    status = [string]$entry.status
    target_runtime_proof_evidence_missing = $requiresMissingTargetProof
    blocked_by = @($blockedBy)
    selected_by_default = $false
  }
}

$selected = @($targetCandidates |
  Where-Object { [bool]$_.target_runtime_proof_evidence_missing } |
  Sort-Object queue_order, lane_id |
  Select-Object -First 1)

if ($selected.Count -eq 0) {
  $selected = @($targetCandidates | Sort-Object queue_order, lane_id | Select-Object -First 1)
}
if ($selected.Count -eq 0) {
  throw "No open target-runtime proof work order found in closure rollup."
}

$selectedLaneId = [string]$selected[0].lane_id
$selectedWorkOrderId = [string]$selected[0].work_order_id
$selectedQueueOrder = [int]$selected[0].queue_order
$selectedBlockedBy = @($selected[0].blocked_by)
foreach ($candidate in $targetCandidates) {
  if ([string]$candidate.work_order_id -eq $selectedWorkOrderId) {
    $candidate.selected_by_default = $true
  }
}

$gitGatePasses = (
  [string]$gitGate.result -eq "pass_git_checkpoint_ready" -and
  [bool]$gitGate.clean_worktree -and
  [bool]$gitGate.local_matches_origin -and
  -not [bool]$gitGate.commit_attempted -and
  -not [bool]$gitGate.push_attempted
)
$s3Ready = ([string]$s3Readiness.result -eq "ready_local_only")
$explicitSelectionRequired = $true
$executeAllowedNow = $false
$blockers = New-Object System.Collections.Generic.List[string]
[void]$blockers.Add("explicit_user_target_runtime_selection_required")
if (-not $gitGatePasses) { [void]$blockers.Add("git_checkpoint_gate_not_clean_for_ec2_execute") }
if (-not $s3Ready) { [void]$blockers.Add("s3_runtime_transfer_readiness_not_ready") }
foreach ($blocker in $selectedBlockedBy) {
  if ($gitGatePasses -and [string]$blocker -eq "git_checkpoint_gate_not_clean_for_ec2_execute") { continue }
  if ($gitGatePasses -and [string]$blocker -eq "runtime_handoff_git_gate_not_passing") { continue }
  if (-not [string]::IsNullOrWhiteSpace($blocker)) { [void]$blockers.Add($blocker) }
}
$result = if ($gitGatePasses) {
  "blocked_target_runtime_execution_plan_waiting_for_explicit_selection"
} else {
  "blocked_target_runtime_execution_plan_waiting_for_explicit_selection_and_clean_git"
}

$commandSequence = @(
  (New-CommandStep -Name "explicit_target_runtime_selection" -Gate "manual_selection_required" -Command "User selects target-runtime proof for lane $selectedLaneId and confirms EC2 live-window intent." -ExpectedEvidence "A current user instruction explicitly selects this lane and target-runtime task." -WhenToRun "Before any live upload, marker write, EC2 static proof, or workflow smoke." -ExecuteAllowedNow $false),
  (New-CommandStep -Name "closure_rollup_recheck" -Gate "before_any_ec2_execute" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\New-ActiveRuntimeQueueFinalCertificationClosureRollup.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_ACTIVE_RUNTIME_QUEUE_FINAL_CERTIFICATION_CLOSURE_ROLLUP_<timestamp>.json" -ExpectedEvidence "remaining_local_ready_count=0 and selected target-runtime work order still open." -WhenToRun "Before selecting the live lane if any work-order or done-certification evidence changed." -ExecuteAllowedNow $true),
  (New-CommandStep -Name "git_checkpoint_recheck" -Gate "before_any_ec2_execute" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-GitHubCheckpoint.ps1 -ProjectRoot C:\Comfy_UI_Main -Message `"pre-ec2 checkpoint gate dry run`" -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Git_Verification\W66_GITHUB_CHECKPOINT_DRY_RUN_JSON_GATE_<timestamp>.json" -ExpectedEvidence "result=pass_git_checkpoint_ready, clean_worktree=true, local_matches_origin=true, commit_attempted=false, push_attempted=false." -WhenToRun "Immediately before any EC2 helper runs with -Execute." -ExecuteAllowedNow $true),
  (New-CommandStep -Name "runtime_unblock_handoff_recheck" -Gate "before_any_ec2_execute" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-RuntimeUnblockHandoff.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId $selectedLaneId -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_RUNTIME_UNBLOCK_HANDOFF_${selectedLaneId}_<timestamp>.json" -ExpectedEvidence "handoff records selected lane, active queue support, model registry coverage, Git checkpoint gate, and command sequence." -WhenToRun "After explicit lane selection and before live runtime." -ExecuteAllowedNow $true),
  (New-CommandStep -Name "active_runtime_queue_local_support_recheck" -Gate "before_any_ec2_execute" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\Test-ActiveRuntimeQueueLocalSupportCertification.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Done_Certifications\W66_ACTIVE_RUNTIME_QUEUE_LOCAL_SUPPORT_CERTIFICATION_<timestamp>.json" -ExpectedEvidence "result=pass_local_active_runtime_queue_support_certification, lane_count=9, defects=0." -WhenToRun "Before target-runtime proof if queue files, lane exports, evidence paths, or local support certification changed." -ExecuteAllowedNow $true),
  (New-CommandStep -Name "runtime_lane_queue_recheck" -Gate "before_any_ec2_execute" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\Test-RuntimeLaneQueue.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Prerequisite_Matching\W66_RUNTIME_LANE_QUEUE_<timestamp>.json" -ExpectedEvidence "result=pass_local_only, failed_check_count=0, selected lane remains in active queue." -WhenToRun "Before EC2 static proof if queue files or evidence changed." -ExecuteAllowedNow $true),
  (New-CommandStep -Name "model_registry_coverage_recheck" -Gate "before_any_ec2_execute" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\Test-WorkflowModelRegistryCoverage.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Model_Registry\W66_MODEL_REGISTRY_COVERAGE_<timestamp>.json" -ExpectedEvidence "result=pass_local_only and selected lane $selectedLaneId has result=pass." -WhenToRun "Before EC2 static proof if model registry, runtime requirements, or queue files changed." -ExecuteAllowedNow $true),
  (New-CommandStep -Name "lane_runtime_readiness_recheck" -Gate "auth_gate_safe_to_start_ec2_true" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-LaneRuntimeReadiness.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId $selectedLaneId -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_LANE_RUNTIME_READINESS_${selectedLaneId}_<timestamp>.json" -ExpectedEvidence "lane_id=$selectedLaneId and ready_for_ec2_static_proof=true." -WhenToRun "Only after AWS auth gate reports safe_to_start_ec2=true." -ExecuteAllowedNow $false),
  (New-CommandStep -Name "deploy_bundle_build" -Gate "before_ec2_sync_or_execute" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-EC2DeployBundle.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId $selectedLaneId -RunPackageManifestFile <run-package-manifest>" -ExpectedEvidence "DEPLOY_BUNDLE_MANIFEST.json and bundle zip created while EC2 is stopped." -WhenToRun "After a current run package is selected for the lane." -ExecuteAllowedNow $false),
  (New-CommandStep -Name "deploy_bundle_s3_publish" -Gate "before_ec2_sync_or_execute" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Publish-DeployBundleToS3.ps1 -BundleManifestFile <deploy-bundle-manifest> -S3BaseUri s3://<bucket>/<deploy-bundle-prefix>" -ExpectedEvidence "s3_bundle_uri and bundle_zip_sha256 recorded before EC2 starts." -WhenToRun "Add -Execute only after explicit live-window selection, AWS auth, and S3 permission gates pass." -ExecuteAllowedNow $false),
  (New-CommandStep -Name "active_runtime_marker_plan_or_write" -Gate "after_all_pre_ec2_gates_pass" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-EC2RuntimeWindowMarkerPlan.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId $selectedLaneId -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_EC2_RUNTIME_WINDOW_MARKER_PLAN_<timestamp>.json" -ExpectedEvidence "Dry-run marker plan or explicit marker write evidence only after all gates pass." -WhenToRun "Do not write ACTIVE_EC2_RUNTIME_WINDOW.json until the live window is actually selected." -ExecuteAllowedNow $false),
  (New-CommandStep -Name "ec2_static_proof_execute" -Gate "ready_for_ec2_static_proof_true" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1 -LaneId $selectedLaneId -Execute -SkipGitLfsPull -DeployBundleS3Uri <s3-bundle-uri> -DeployBundleSha256 <bundle-sha256> -MaxEc2RuntimeMinutes 25 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W66_EC2_LANE_STATIC_PROOF_${selectedLaneId}_<timestamp>.json" -ExpectedEvidence "object_info, checkpoint path/hash, lane match, S3 bundle verification, and final EC2 stopped state." -WhenToRun "Only after explicit selection, clean Git gate, AWS auth, queue/model/readiness gates, S3 bundle proof, and emergency stop are all proven." -ExecuteAllowedNow $false),
  (New-CommandStep -Name "workflow_smoke_execute" -Gate "ec2_static_proof_passed" -Command "powershell -NoProfile -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1 -LaneId $selectedLaneId -Execute -SkipGitLfsPull -DeployBundleS3Uri <s3-bundle-uri> -DeployBundleSha256 <bundle-sha256> -MaxEc2RuntimeMinutes 45 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Runtime\W66_EC2_WORKFLOW_SMOKE_${selectedLaneId}_<timestamp>.json" -ExpectedEvidence "bounded generation, artifact pullback plan, technical QA, visual QA, and final EC2 stopped state." -WhenToRun "Only after EC2 static proof passes for the selected lane." -ExecuteAllowedNow $false)
)

$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "active_runtime_queue_target_runtime_execution_plan"
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
  execute_allowed_now = $executeAllowedNow
  explicit_user_selection_required = $explicitSelectionRequired
  source_closure_rollup = ConvertTo-ProjectRelativePath -Path $closureResolved
  source_work_order_manifest = ConvertTo-ProjectRelativePath -Path $workOrderManifestPath
  runtime_queue = ConvertTo-ProjectRelativePath -Path $runtimeQueueResolved
  active_lanes = ConvertTo-ProjectRelativePath -Path $activeLanesResolved
  git_checkpoint_gate = ConvertTo-ProjectRelativePath -Path $gitGateResolved
  s3_transfer_readiness = ConvertTo-ProjectRelativePath -Path $s3ReadinessResolved
  selected_work_order_id = $selectedWorkOrderId
  selected_lane_id = $selectedLaneId
  selected_lane_queue_order = $selectedQueueOrder
  selection_policy = "First open target-runtime proof work order with target_runtime_proof_evidence_missing, sorted by runtime queue order; already-proven or reuse-bound lanes are not selected by default."
  target_candidate_count = @($targetCandidates).Count
  target_candidates = @($targetCandidates | Sort-Object queue_order, lane_id)
  blocker_summary = @($blockers | Select-Object -Unique)
  git_checkpoint_summary = [ordered]@{
    result = [string]$gitGate.result
    clean_worktree = [bool]$gitGate.clean_worktree
    local_matches_origin = [bool]$gitGate.local_matches_origin
    passes_for_ec2_execute = $gitGatePasses
  }
  s3_transfer_summary = [ordered]@{
    result = [string]$s3Readiness.result
    ready_local_only = $s3Ready
  }
  active_lanes_summary = [ordered]@{
    lane_count = @(Convert-ToArray -Value $activeLanes.lanes).Count
    source_queue = [string]$activeLanes.source_queue
  }
  command_sequence = @($commandSequence)
  command_step_count = @($commandSequence).Count
  certification_boundary = "Local target-runtime execution planning only. This does not authorize or perform live upload, marker write, EC2 start, generation, final certification, mask promotion, Wave70 hard-gate rerun, Jira bookkeeping, or Wave71+ activation."
  next_action = $(if ($gitGatePasses) { "Keep EC2 stopped. If the user explicitly selects this target-runtime lane, rerun the listed gates in order and require AWS/S3/runtime proof before any -Execute command." } else { "Keep EC2 stopped. If the user explicitly selects this target-runtime lane, rerun the listed gates in order and require clean Git plus AWS/S3/runtime proof before any -Execute command." })
}

$outDir = Split-Path -Path $outFileResolved -Parent
$mdDir = Split-Path -Path $markdownResolved -Parent
[System.IO.Directory]::CreateDirectory($outDir) | Out-Null
[System.IO.Directory]::CreateDirectory($mdDir) | Out-Null
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($outFileResolved, ($record | ConvertTo-Json -Depth 30) + [Environment]::NewLine, $utf8NoBom)

$candidateLines = foreach ($candidate in @($record.target_candidates)) {
  "- $($candidate.queue_order). $($candidate.lane_id): missing_target_runtime_proof=$($candidate.target_runtime_proof_evidence_missing); selected=$($candidate.selected_by_default)"
}
$stepLines = foreach ($step in $commandSequence) {
  "- $($step.name): gate=$($step.gate); execute_allowed_now=$($step.execute_allowed_now)"
}
$markdown = @"
# Active Runtime Queue Target Runtime Execution Plan

- created_at: $($record.created_at)
- result: $($record.result)
- selected_lane_id: $selectedLaneId
- selected_work_order_id: $selectedWorkOrderId
- selected_lane_queue_order: $selectedQueueOrder
- execute_allowed_now: false
- explicit_user_selection_required: true
- full_project_certification_allowed: false

## Candidate Order

$($candidateLines -join "`n")

## Command Gates

$($stepLines -join "`n")

## Boundary

$($record.certification_boundary)

## Evidence

- $($record.source_closure_rollup)
- $($record.runtime_queue)
- $($record.active_lanes)
- $($record.git_checkpoint_gate)
- $($record.s3_transfer_readiness)
"@
[System.IO.File]::WriteAllText($markdownResolved, $markdown + [Environment]::NewLine, $utf8NoBom)

$record | ConvertTo-Json -Depth 30
exit 0
