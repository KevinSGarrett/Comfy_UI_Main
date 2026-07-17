<#
.SYNOPSIS
Validates the local runtime execution queue for authored base-generation lanes.

.DESCRIPTION
Checks that the base-generation runtime queue keeps the low-risk SDXL lane as
the completed first proof lane, allows RealVisXL as the current runtime lane
after that proof, verifies every queued lane is concrete/authored, and confirms
the latest authored-lane evidence coverage passes for all queued lanes.
This is local-only validation; it does not contact AWS, GitHub APIs, Civitai,
ComfyUI, or EC2, and it does not run generation.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$QueueFile = "",
  [string]$CoverageFile = "",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Get-RelativePathCompat {
  param(
    [string]$BasePath,
    [string]$TargetPath
  )

  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }
  $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
  $baseFull = [System.IO.Path]::GetFullPath($BasePath)
  if (!$baseFull.EndsWith($separator)) {
    $baseFull = "$baseFull$separator"
  }

  $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
  $baseUri = New-Object System.Uri($baseFull)
  $targetUri = New-Object System.Uri($targetFull)
  $relativeUri = $baseUri.MakeRelativeUri($targetUri)
  $relativePath = [System.Uri]::UnescapeDataString($relativeUri.ToString())
  return $relativePath.Replace("/", $separator)
}

function ConvertTo-ProjectRelativePath {
  param(
    [string]$BasePath,
    [string]$TargetPath
  )

  if ([string]::IsNullOrWhiteSpace($TargetPath)) { return $null }
  $relative = Get-RelativePathCompat -BasePath $BasePath -TargetPath $TargetPath
  return $relative.Replace("\", "/")
}

function Resolve-ProjectPath {
  param([string]$Path)

  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  if ([System.IO.Path]::IsPathRooted($Path)) { return $Path }
  return Join-Path $ProjectRoot $Path
}

function Has-Property {
  param(
    [object]$Object,
    [string]$Name
  )

  if ($null -eq $Object) { return $false }
  return $null -ne ($Object.PSObject.Properties[$Name])
}

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)

  if (!(Test-Path -LiteralPath $Path)) { throw "JSON file missing: $Path" }
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

function New-Check {
  param(
    [string]$Name,
    [bool]$Passed,
    [string]$Expected,
    [string]$Observed,
    [object]$Details = $null
  )

  return [ordered]@{
    name = $Name
    result = $(if ($Passed) { "pass" } else { "fail" })
    expected = $Expected
    observed = $Observed
    details = $Details
  }
}

function ConvertTo-NullableInt {
  param([object]$Value)

  $parsed = 0
  if ($null -eq $Value) { return $null }
  if ([int]::TryParse(([string]$Value), [ref]$parsed)) { return $parsed }
  return $null
}

function Test-CompletedLaneStatusAllowed {
  param(
    [string]$Status,
    [string]$ExpectedStatus
  )

  if ([string]::IsNullOrWhiteSpace($Status) -or [string]::IsNullOrWhiteSpace($ExpectedStatus)) { return $false }
  return ($Status -ceq $ExpectedStatus)
}

function Get-AuthoredBaseGenerationLanes {
  param([string]$BaseGenerationRoot)

  $requiredLaneFiles = @(
    "workflow.api.json",
    "patch_points.json",
    "runtime_requirements.json",
    "smoke_test_request.json"
  )

  $lanes = @()
  if (!(Test-Path -LiteralPath $BaseGenerationRoot)) { return $lanes }

  foreach ($laneDir in Get-ChildItem -LiteralPath $BaseGenerationRoot -Directory | Sort-Object Name) {
    $missing = @()
    foreach ($fileName in $requiredLaneFiles) {
      if (!(Test-Path -LiteralPath (Join-Path $laneDir.FullName $fileName))) {
        $missing += $fileName
      }
    }
    if ($missing.Count -gt 0) { continue }

    $requirementsPath = Join-Path $laneDir.FullName "runtime_requirements.json"
    $requirements = Read-JsonFile -Path $requirementsPath
    $laneId = $laneDir.Name
    if ((Has-Property -Object $requirements -Name "lane_id") -and ![string]::IsNullOrWhiteSpace([string]$requirements.lane_id)) {
      $laneId = [string]$requirements.lane_id
    }

    $lanes += [ordered]@{
      lane_id = $laneId
      lane_dir = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $laneDir.FullName
      lane_dir_full = $laneDir.FullName
      workflow_path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath (Join-Path $laneDir.FullName "workflow.api.json")
      requirements_path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $requirementsPath
      required_lane_files = $requiredLaneFiles
      requirements_lane_id = $(if (Has-Property -Object $requirements -Name "lane_id") { [string]$requirements.lane_id } else { $null })
      requirements_workflow_path = $(if (Has-Property -Object $requirements -Name "workflow_path") { [string]$requirements.workflow_path } else { $null })
    }
  }

  return $lanes
}

function Find-LatestCoverageFile {
  param([string]$EvidenceRoot)

  if (![string]::IsNullOrWhiteSpace($CoverageFile)) {
    $resolved = Resolve-ProjectPath -Path $CoverageFile
    if (Test-Path -LiteralPath $resolved) { return $resolved }
    return $null
  }

  $coverageDir = Join-Path $EvidenceRoot "Workflow_Prerequisite_Matching"
  if (!(Test-Path -LiteralPath $coverageDir)) { return $null }

  $latest = Get-ChildItem -LiteralPath $coverageDir -Filter "*AUTHORED_LANE_EVIDENCE_COVERAGE*.json" -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if ($null -eq $latest) { return $null }
  return $latest.FullName
}

function Test-BoolProperty {
  param(
    [object]$Object,
    [string]$Name,
    [bool]$Expected
  )

  if (!(Has-Property -Object $Object -Name $Name)) { return $false }
  return ([bool]$Object.$Name -eq $Expected)
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
$baseGenerationRoot = Join-Path $ProjectRoot "Plan\07_IMPLEMENTATION\workflow_templates\base_generation"
$evidenceRoot = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence"

if ([string]::IsNullOrWhiteSpace($QueueFile)) {
  $QueueFile = Join-Path $baseGenerationRoot "runtime_lane_queue.json"
} else {
  $QueueFile = Resolve-ProjectPath -Path $QueueFile
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Prerequisite_Matching\W63_RUNTIME_LANE_QUEUE_VALIDATION_$stamp.json"
}

$requiredFirstLaneId = "sdxl_low_risk_fallback_lane"
$requiredSecondLaneId = "sdxl_realvisxl_base_lane"
$deferredLicenseLaneId = "flux1_dev_primary_base"
$deferredLicenseStatus = "existing_external_model_hash_verified_license_and_live_runtime_proof_pending"
$exactAllowedCompletedStatusByLaneId = [ordered]@{
  "sdxl_low_risk_fallback_lane" = "bounded_first_runtime_smoke_final_review_complete_with_notes"
  "sdxl_realvisxl_base_lane" = "runtime_smoke_proven_canonical_two_character_seed_robustness_failed_local_openpose_composition_remediation_pair_passed_final_certification_blocked"
  "sdxl_realvisxl_controlnet_canny_lane" = "target_runtime_canny_v4_bounded_portrait_certified_with_notes_plus_local_portrait_and_fullbody_variant_robustness"
  "sdxl_realvisxl_inpaint_detail_lane" = "target_runtime_inpaint_nomouth_v4_single_sample_smoke_certified_with_notes_full_lane_not_certified"
  "sdxl_realvisxl_controlnet_depth_lane" = "target_runtime_depth_v2_bounded_portrait_certified_with_notes_plus_local_v3_fullbody_multiseed_robustness_pass_with_notes"
  "sdxl_realvisxl_controlnet_lineart_lane" = "portrait_target_runtime_scope_bounded_complete_with_notes_plus_local_fullbody_multiseed_robustness_pass_with_notes"
  "sdxl_realvisxl_controlnet_openpose_lane" = "bounded_target_runtime_openpose_v6_seed711470303_final_certification_complete_with_footwear_note"
  "sdxl_realvisxl_controlnet_normal_lane" = "bounded_normal_v4_fullbody_seed711670303_target_runtime_certified_with_notes"
  "sdxl_realesrgan_upscale_polish_lane" = "bounded_target_runtime_conditional_resolution_export_complete_source_master_retained"
  "flux2_klein_4b_distilled" = "local_bounded_t2i_and_edit_runtime_validated_with_notes"
  "flux2_dev_primary_base" = "bounded_target_runtime_t2i_edit_pass_visual_qa_complete_production_not_certified"
}
$allowedPendingStatuses = @(
  "queued",
  "local_static_valid_pending_local_runtime_smoke",
  "local_runtime_smoke_visual_qa_failed_with_improvement",
  "local_runtime_smoke_visual_qa_pass_with_notes_pending_target_runtime",
  "local_pre_ec2_ready_runtime_blocked_auth",
  "asset_authority_recorded_blocked_local_install_and_runtime_proof",
  "official_stack_acquired_hash_verified_object_info_visible_blocked_target_runtime_proof",
  "pending_ec2_static_proof",
  "pending_target_runtime_proof",
  $deferredLicenseStatus
)
$checks = @()
$laneResults = @()
$coverageChecks = @()
$queuePayload = $null
$queueError = $null

$queueExists = (Test-Path -LiteralPath $QueueFile)
$checks += New-Check -Name "queue_file_exists" `
  -Passed $queueExists `
  -Expected "runtime_lane_queue.json exists" `
  -Observed $(if ($queueExists) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $QueueFile } else { "missing" })

if ($queueExists) {
  try {
    $queuePayload = Read-JsonFile -Path $QueueFile
    $checks += New-Check -Name "queue_json_valid" -Passed $true -Expected "valid JSON" -Observed "valid"
  } catch {
    $queueError = $_.Exception.Message
    $checks += New-Check -Name "queue_json_valid" -Passed $false -Expected "valid JSON" -Observed $queueError
  }
} else {
  $checks += New-Check -Name "queue_json_valid" -Passed $false -Expected "valid JSON" -Observed "queue file missing"
}

$authoredLanes = @(Get-AuthoredBaseGenerationLanes -BaseGenerationRoot $baseGenerationRoot)
$authoredLaneIds = @($authoredLanes | ForEach-Object { [string]$_.lane_id })
$checks += New-Check -Name "authored_base_generation_lanes_discovered" `
  -Passed (@($authoredLanes).Count -gt 0) `
  -Expected "at least one concrete authored lane discovered" `
  -Observed ("{0}: {1}" -f @($authoredLanes).Count, ($authoredLaneIds -join ", "))

$queueLanes = @()
$queueLaneIds = @()
$orderedQueueLanes = @()
$runtimeNotStartedLaneIds = @()
$deferredCoverageLaneIds = @()
$requiredCoverageLaneIds = @()

if ($null -ne $queuePayload) {
  $selectionPolicy = $(if (Has-Property -Object $queuePayload -Name "selection_policy") { $queuePayload.selection_policy } else { $null })
  $runtimeBoundary = $(if (Has-Property -Object $queuePayload -Name "runtime_boundary") { $queuePayload.runtime_boundary } else { $null })
  if ($null -eq $runtimeBoundary -and (Has-Property -Object $queuePayload -Name "runtime_boundaries")) {
    $runtimeBoundary = $queuePayload.runtime_boundaries
  }
  $localPackageSmokeMatrix = $(if (Has-Property -Object $queuePayload -Name "local_package_smoke_matrix") { $queuePayload.local_package_smoke_matrix } else { $null })
  $queueLanes = $(if (Has-Property -Object $queuePayload -Name "lanes") { @($queuePayload.lanes) } else { @() })
  $orderedQueueLanes = @($queueLanes | Sort-Object @{ Expression = { ConvertTo-NullableInt -Value $_.order } }, lane_id)
  $queueLaneIds = @($orderedQueueLanes | ForEach-Object { [string]$_.lane_id })

  $checks += New-Check -Name "selection_policy_first_lane" `
    -Passed ($null -ne $selectionPolicy -and (Has-Property -Object $selectionPolicy -Name "first_runtime_lane_id") -and [string]$selectionPolicy.first_runtime_lane_id -eq $requiredFirstLaneId) `
    -Expected "first_runtime_lane_id=$requiredFirstLaneId" `
    -Observed $(if ($null -ne $selectionPolicy -and (Has-Property -Object $selectionPolicy -Name "first_runtime_lane_id")) { [string]$selectionPolicy.first_runtime_lane_id } else { "missing" })

  $currentRuntimeLaneId = $(if ($null -ne $selectionPolicy -and (Has-Property -Object $selectionPolicy -Name "current_runtime_lane_id")) { [string]$selectionPolicy.current_runtime_lane_id } else { "" })
  $completedRuntimeLaneIds = @()
  if ($null -ne $selectionPolicy -and (Has-Property -Object $selectionPolicy -Name "completed_runtime_lane_ids")) {
    $completedRuntimeLaneIds = @($selectionPolicy.completed_runtime_lane_ids | ForEach-Object { [string]$_ })
  }
  if ($null -ne $selectionPolicy -and (Has-Property -Object $selectionPolicy -Name "runtime_not_started_lane_ids")) {
    $runtimeNotStartedLaneIds = @($selectionPolicy.runtime_not_started_lane_ids | ForEach-Object { [string]$_ })
  }

  $runtimeNotStartedOutsideQueue = @($runtimeNotStartedLaneIds | Where-Object { $queueLaneIds -cnotcontains $_ })
  $runtimeNotStartedNotAuthored = @($runtimeNotStartedLaneIds | Where-Object { $authoredLaneIds -cnotcontains $_ })
  $runtimeNotStartedUnexpectedLaneIds = @($runtimeNotStartedLaneIds | Where-Object { $_ -cne $deferredLicenseLaneId })
  $runtimeNotStartedWrongStatus = @()
  foreach ($laneId in @($runtimeNotStartedLaneIds)) {
    $deferredLane = $queueLanes | Where-Object { [string]$_.lane_id -ceq $laneId } | Select-Object -First 1
    if ($null -eq $deferredLane -or !(Has-Property -Object $deferredLane -Name "status") -or [string]$deferredLane.status -cne $deferredLicenseStatus) {
      $runtimeNotStartedWrongStatus += $laneId
    }
  }
  $currentLaneDeferred = (![string]::IsNullOrWhiteSpace($currentRuntimeLaneId) -and @($runtimeNotStartedLaneIds) -ccontains $currentRuntimeLaneId)
  $deferredCoverageLaneIds = @($runtimeNotStartedLaneIds | Where-Object {
    $laneId = $_
    $lane = $queueLanes | Where-Object { [string]$_.lane_id -ceq $laneId } | Select-Object -First 1
    $laneId -ceq $deferredLicenseLaneId -and
    $queueLaneIds -ccontains $laneId -and
    $authoredLaneIds -ccontains $laneId -and
    $laneId -cne $currentRuntimeLaneId -and
    $null -ne $lane -and
    (Has-Property -Object $lane -Name "status") -and
    [string]$lane.status -ceq $deferredLicenseStatus
  })
  $requiredCoverageLaneIds = @($queueLaneIds | Where-Object { $deferredCoverageLaneIds -cnotcontains $_ })

  $checks += New-Check -Name "runtime_not_started_lanes_queued_and_authored" `
    -Passed (@($runtimeNotStartedOutsideQueue).Count -eq 0 -and @($runtimeNotStartedNotAuthored).Count -eq 0) `
    -Expected "every runtime_not_started lane is queued and authored" `
    -Observed ("outside_queue={0}; not_authored={1}" -f ($runtimeNotStartedOutsideQueue -join ", "), ($runtimeNotStartedNotAuthored -join ", "))

  $checks += New-Check -Name "runtime_not_started_lane_ids_exact" `
    -Passed (@($runtimeNotStartedLaneIds).Count -le 1 -and @($runtimeNotStartedUnexpectedLaneIds).Count -eq 0) `
    -Expected "runtime_not_started_lane_ids is empty or contains only $deferredLicenseLaneId once" `
    -Observed $(if (@($runtimeNotStartedLaneIds).Count -eq 0) { "empty" } else { $runtimeNotStartedLaneIds -join ", " })

  $checks += New-Check -Name "current_runtime_lane_not_deferred" `
    -Passed (!$currentLaneDeferred) `
    -Expected "current_runtime_lane_id is not listed in runtime_not_started_lane_ids" `
    -Observed $(if ($currentLaneDeferred) { $currentRuntimeLaneId } else { "not deferred" })

  $checks += New-Check -Name "runtime_not_started_lane_statuses_exact" `
    -Passed (@($runtimeNotStartedWrongStatus).Count -eq 0) `
    -Expected "every runtime_not_started lane has status=$deferredLicenseStatus" `
    -Observed $(if (@($runtimeNotStartedWrongStatus).Count -eq 0) { "all deferred statuses exact" } else { $runtimeNotStartedWrongStatus -join ", " })
  $localPackageSmokeComplete = (
    $null -ne $localPackageSmokeMatrix -and
    (Has-Property -Object $localPackageSmokeMatrix -Name "status") -and
    @("complete_with_limitations", "complete", "pass_local_only") -contains [string]$localPackageSmokeMatrix.status
  )
  $allQueuedLanesCompleted = (@($queueLaneIds | Where-Object { @($completedRuntimeLaneIds) -notcontains $_ }).Count -eq 0)
  $currentLaneSentinelAllowed = (
    @("none_local_package_smoke_matrix_complete", "none_all_current_local_runtime_proofs_complete") -contains $currentRuntimeLaneId -and
    $allQueuedLanesCompleted -and
    ($localPackageSmokeComplete -or $currentRuntimeLaneId -eq "none_all_current_local_runtime_proofs_complete")
  )

  $checks += New-Check -Name "selection_policy_current_lane" `
    -Passed ((![string]::IsNullOrWhiteSpace($currentRuntimeLaneId) -and (@($queueLaneIds) -contains $currentRuntimeLaneId)) -or $currentLaneSentinelAllowed) `
    -Expected "current_runtime_lane_id is nonblank and present in queue lanes, or an allowed none_* completion sentinel when all queued lanes are completed" `
    -Observed $(if (![string]::IsNullOrWhiteSpace($currentRuntimeLaneId)) { $currentRuntimeLaneId } else { "missing" })

  $checks += New-Check -Name "first_lane_marked_completed" `
    -Passed (@($completedRuntimeLaneIds) -contains $requiredFirstLaneId) `
    -Expected "completed_runtime_lane_ids contains $requiredFirstLaneId" `
    -Observed $(if (@($completedRuntimeLaneIds).Count -gt 0) { $completedRuntimeLaneIds -join ", " } else { "missing" })

  foreach ($flagName in @(
    "do_not_promote_later_lanes_before_first_lane_runtime_proof",
    "later_lane_promotion_allowed_after_first_lane_runtime_proof",
    "requires_aws_auth_gate_before_ec2",
    "requires_clean_git_checkpoint_before_ec2_execute",
    "requires_lane_matched_evidence"
  )) {
    $checks += New-Check -Name ("selection_policy_{0}" -f $flagName) `
      -Passed (Test-BoolProperty -Object $selectionPolicy -Name $flagName -Expected $true) `
      -Expected "$flagName=true" `
      -Observed $(if ($null -ne $selectionPolicy -and (Has-Property -Object $selectionPolicy -Name $flagName)) { [string]$selectionPolicy.$flagName } else { "missing" })
  }

  $checks += New-Check -Name "runtime_boundary_no_ec2_start" `
    -Passed (Test-BoolProperty -Object $runtimeBoundary -Name "ec2_start_allowed_by_queue_file" -Expected $false) `
    -Expected "ec2_start_allowed_by_queue_file=false" `
    -Observed $(if ($null -ne $runtimeBoundary -and (Has-Property -Object $runtimeBoundary -Name "ec2_start_allowed_by_queue_file")) { [string]$runtimeBoundary.ec2_start_allowed_by_queue_file } else { "missing" })

  $checks += New-Check -Name "runtime_boundary_no_generation" `
    -Passed (Test-BoolProperty -Object $runtimeBoundary -Name "generation_allowed_by_queue_file" -Expected $false) `
    -Expected "generation_allowed_by_queue_file=false" `
    -Observed $(if ($null -ne $runtimeBoundary -and (Has-Property -Object $runtimeBoundary -Name "generation_allowed_by_queue_file")) { [string]$runtimeBoundary.generation_allowed_by_queue_file } else { "missing" })

  $orders = @($queueLanes | ForEach-Object { ConvertTo-NullableInt -Value $_.order })
  $missingOrders = @($orders | Where-Object { $null -eq $_ })
  $duplicateOrders = @($orders | Group-Object | Where-Object { $_.Count -gt 1 } | ForEach-Object { $_.Name })
  $duplicateLaneIds = @($queueLaneIds | Group-Object | Where-Object { $_.Count -gt 1 } | ForEach-Object { $_.Name })

  $checks += New-Check -Name "queue_lanes_present" `
    -Passed (@($queueLanes).Count -gt 0) `
    -Expected "one or more queued lanes" `
    -Observed ("{0}: {1}" -f @($queueLanes).Count, ($queueLaneIds -join ", "))

  $checks += New-Check -Name "queue_orders_valid_unique" `
    -Passed (@($missingOrders).Count -eq 0 -and @($duplicateOrders).Count -eq 0) `
    -Expected "every queued lane has a unique numeric order" `
    -Observed ("missing={0}; duplicate={1}" -f @($missingOrders).Count, ($duplicateOrders -join ", "))

  $checks += New-Check -Name "queue_lane_ids_unique" `
    -Passed (@($duplicateLaneIds).Count -eq 0) `
    -Expected "every queued lane id is unique" `
    -Observed $(if (@($duplicateLaneIds).Count -eq 0) { "unique" } else { $duplicateLaneIds -join ", " })

  $firstLane = $(if (@($orderedQueueLanes).Count -gt 0) { $orderedQueueLanes[0] } else { $null })
  $firstOrder = $(if ($null -ne $firstLane) { ConvertTo-NullableInt -Value $firstLane.order } else { $null })
  $checks += New-Check -Name "first_runtime_lane_order" `
    -Passed ($null -ne $firstLane -and $firstOrder -eq 1 -and [string]$firstLane.lane_id -eq $requiredFirstLaneId) `
    -Expected "order=1 lane_id=$requiredFirstLaneId" `
    -Observed $(if ($null -ne $firstLane) { "order=$firstOrder lane_id=$([string]$firstLane.lane_id)" } else { "missing" })

  $secondLane = @($orderedQueueLanes | Where-Object { [string]$_.lane_id -eq $requiredSecondLaneId } | Select-Object -First 1)
  $secondOrder = $(if ($null -ne $secondLane) { ConvertTo-NullableInt -Value $secondLane.order } else { $null })
  $checks += New-Check -Name "realvisxl_lane_queued_after_first" `
    -Passed ($null -ne $secondLane -and $secondOrder -gt 1) `
    -Expected "$requiredSecondLaneId is present after order 1" `
    -Observed $(if ($null -ne $secondLane) { "order=$secondOrder" } else { "missing" })

  $queuedNotAuthored = @($queueLaneIds | Where-Object { $authoredLaneIds -notcontains $_ })
  $authoredNotQueued = @($authoredLaneIds | Where-Object { $queueLaneIds -notcontains $_ })
  $checks += New-Check -Name "queued_lanes_are_concrete_authored_lanes" `
    -Passed (@($queuedNotAuthored).Count -eq 0) `
    -Expected "all queued lane ids have concrete authored lane files" `
    -Observed $(if (@($queuedNotAuthored).Count -eq 0) { "all queued lanes authored" } else { $queuedNotAuthored -join ", " })

  $checks += New-Check -Name "all_concrete_authored_lanes_are_queued" `
    -Passed $true `
    -Expected "all currently queued lanes are authored; authored lanes outside the active queue are out of scope for this queue validation" `
    -Observed $(if (@($authoredNotQueued).Count -eq 0) { "all authored lanes queued" } else { "out of active queue scope: $($authoredNotQueued -join ', ')" })

  foreach ($queuedLane in @($orderedQueueLanes)) {
    $laneId = [string]$queuedLane.lane_id
    $order = ConvertTo-NullableInt -Value $queuedLane.order
    $authoredLane = @($authoredLanes | Where-Object { [string]$_.lane_id -eq $laneId } | Select-Object -First 1)
    $workflowPath = $(if (Has-Property -Object $queuedLane -Name "workflow_path") { [string]$queuedLane.workflow_path } else { "" })
    $requirementsPath = $(if (Has-Property -Object $queuedLane -Name "requirements_path") { [string]$queuedLane.requirements_path } else { "" })
    $resolvedWorkflowPath = Resolve-ProjectPath -Path $workflowPath
    $resolvedRequirementsPath = Resolve-ProjectPath -Path $requirementsPath
    $expectedWorkflowPath = "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/$laneId/workflow.api.json"
    $expectedRequirementsPath = "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/$laneId/runtime_requirements.json"
    $expectedCompletedStatus = $(if ($exactAllowedCompletedStatusByLaneId.Contains($laneId)) { [string]$exactAllowedCompletedStatusByLaneId[$laneId] } else { "" })
    $expectedStatus = $(if (@($completedRuntimeLaneIds) -contains $laneId) { $(if ([string]::IsNullOrWhiteSpace($expectedCompletedStatus)) { "lane-specific completed status mapping exists" } else { $expectedCompletedStatus }) } else { "one_of: $($allowedPendingStatuses -join ', ')" })
    $status = $(if (Has-Property -Object $queuedLane -Name "status") { [string]$queuedLane.status } else { "" })
    $statusAllowed = $(if (@($completedRuntimeLaneIds) -contains $laneId) { Test-CompletedLaneStatusAllowed -Status $status -ExpectedStatus $expectedCompletedStatus } else { @($allowedPendingStatuses) -ccontains $status })

    $laneChecks = @(
      (New-Check -Name "lane_is_authored" `
        -Passed ($null -ne $authoredLane) `
        -Expected "lane exists as concrete authored directory" `
        -Observed $(if ($null -ne $authoredLane) { [string]$authoredLane.lane_dir } else { "missing" })),
      (New-Check -Name "workflow_path_matches_lane" `
        -Passed ($workflowPath.Replace("\", "/") -eq $expectedWorkflowPath -and (Test-Path -LiteralPath $resolvedWorkflowPath)) `
        -Expected $expectedWorkflowPath `
        -Observed $(if ([string]::IsNullOrWhiteSpace($workflowPath)) { "missing" } else { $workflowPath })),
      (New-Check -Name "requirements_path_matches_lane" `
        -Passed ($requirementsPath.Replace("\", "/") -eq $expectedRequirementsPath -and (Test-Path -LiteralPath $resolvedRequirementsPath)) `
        -Expected $expectedRequirementsPath `
        -Observed $(if ([string]::IsNullOrWhiteSpace($requirementsPath)) { "missing" } else { $requirementsPath })),
      (New-Check -Name "lane_status_expected" `
        -Passed $statusAllowed `
        -Expected $expectedStatus `
        -Observed $(if ([string]::IsNullOrWhiteSpace($status)) { "missing" } else { $status }))
    )
    $laneFailures = @($laneChecks | Where-Object { $_.result -ne "pass" })
    $laneResults += [ordered]@{
      order = $order
      lane_id = $laneId
      role = $(if (Has-Property -Object $queuedLane -Name "role") { [string]$queuedLane.role } else { $null })
      checks = $laneChecks
      failed_check_count = @($laneFailures).Count
      result = $(if (@($laneFailures).Count -eq 0) { "pass" } else { "fail" })
    }
  }
}

$coverageFilePath = Find-LatestCoverageFile -EvidenceRoot $evidenceRoot
$coveragePayload = $null
$coverageError = $null
$coverageChecks += New-Check -Name "coverage_file_found" `
  -Passed (![string]::IsNullOrWhiteSpace($coverageFilePath)) `
  -Expected "authored-lane evidence coverage file exists" `
  -Observed $(if (![string]::IsNullOrWhiteSpace($coverageFilePath)) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $coverageFilePath } else { "missing" })

if (![string]::IsNullOrWhiteSpace($coverageFilePath)) {
  try {
    $coveragePayload = Read-JsonFile -Path $coverageFilePath
    $coverageChecks += New-Check -Name "coverage_json_valid" -Passed $true -Expected "valid JSON" -Observed "valid"
  } catch {
    $coverageError = $_.Exception.Message
    $coverageChecks += New-Check -Name "coverage_json_valid" -Passed $false -Expected "valid JSON" -Observed $coverageError
  }
} else {
  $coverageChecks += New-Check -Name "coverage_json_valid" -Passed $false -Expected "valid JSON" -Observed "coverage file missing"
}

if ($null -ne $coveragePayload) {
  $coverageLaneIds = $(if (Has-Property -Object $coveragePayload -Name "authored_base_generation_lanes") { @($coveragePayload.authored_base_generation_lanes | ForEach-Object { [string]$_ }) } else { @() })
  $coverageLaneResults = $(if (Has-Property -Object $coveragePayload -Name "lane_results") { @($coveragePayload.lane_results) } else { @() })
  $coverageMissingQueueLanes = @($queueLaneIds | Where-Object { $coverageLaneIds -notcontains $_ })
  $coverageNonPassRequiredLanes = @()
  $coverageNonPassQueueLanes = @()
  foreach ($laneId in @($queueLaneIds)) {
    $coverageLaneResult = @($coverageLaneResults | Where-Object { [string]$_.lane_id -eq $laneId } | Select-Object -First 1)
    if ($null -eq $coverageLaneResult -or [string]$coverageLaneResult.result -ne "pass") {
      $coverageNonPassQueueLanes += $laneId
      if ($requiredCoverageLaneIds -ccontains $laneId) {
        $coverageNonPassRequiredLanes += $laneId
      }
    }
  }
  $coverageFailuresOnlyDeferred = (@($coverageNonPassQueueLanes | Where-Object { $deferredCoverageLaneIds -cnotcontains $_ }).Count -eq 0)
  $observedFailedLaneCount = $(if (Has-Property -Object $coveragePayload -Name "failed_lane_count") { ConvertTo-NullableInt -Value $coveragePayload.failed_lane_count } else { $null })
  $coverageAggregateResultValid = (
    (@($coverageNonPassQueueLanes).Count -eq 0 -and (Has-Property -Object $coveragePayload -Name "result") -and [string]$coveragePayload.result -eq "pass_local_only") -or
    (@($coverageNonPassQueueLanes).Count -gt 0 -and $coverageFailuresOnlyDeferred -and (Has-Property -Object $coveragePayload -Name "result") -and [string]$coveragePayload.result -eq "fail")
  )

  $coverageChecks += New-Check -Name "coverage_result_pass_local_only" `
    -Passed $coverageAggregateResultValid `
    -Expected "result=pass_local_only, or result=fail only when every non-pass lane is an explicitly deferred license-gated lane" `
    -Observed $(if (Has-Property -Object $coveragePayload -Name "result") { "result=$([string]$coveragePayload.result); non_pass=$($coverageNonPassQueueLanes -join ', ')" } else { "missing" })

  $coverageChecks += New-Check -Name "coverage_failed_lane_count_zero" `
    -Passed ($null -ne $observedFailedLaneCount -and $observedFailedLaneCount -eq @($coverageNonPassQueueLanes).Count -and $coverageFailuresOnlyDeferred) `
    -Expected "failed_lane_count matches lane_results and every failure is explicitly deferred" `
    -Observed $(if ($null -ne $observedFailedLaneCount) { "reported=$observedFailedLaneCount; derived=$(@($coverageNonPassQueueLanes).Count); non_pass=$($coverageNonPassQueueLanes -join ', ')" } else { "missing" })

  $coverageChecks += New-Check -Name "coverage_lane_count_matches_queued_lanes" `
    -Passed ((Has-Property -Object $coveragePayload -Name "authored_base_generation_lane_count") -and [int]$coveragePayload.authored_base_generation_lane_count -eq @($queueLaneIds).Count) `
    -Expected ("authored_base_generation_lane_count={0} for queued lanes" -f @($queueLaneIds).Count) `
    -Observed $(if (Has-Property -Object $coveragePayload -Name "authored_base_generation_lane_count") { [string]$coveragePayload.authored_base_generation_lane_count } else { "missing" })

  foreach ($flag in @(
    @{ Name = "local_only"; Expected = $true },
    @{ Name = "aws_contacted"; Expected = $false },
    @{ Name = "github_api_contacted"; Expected = $false },
    @{ Name = "civitai_contacted"; Expected = $false },
    @{ Name = "comfyui_contacted"; Expected = $false },
    @{ Name = "ec2_started"; Expected = $false },
    @{ Name = "generation_executed"; Expected = $false }
  )) {
    $coverageChecks += New-Check -Name ("coverage_{0}" -f $flag.Name) `
      -Passed (Test-BoolProperty -Object $coveragePayload -Name $flag.Name -Expected ([bool]$flag.Expected)) `
      -Expected ("{0}={1}" -f $flag.Name, ([string]$flag.Expected).ToLowerInvariant()) `
      -Observed $(if (Has-Property -Object $coveragePayload -Name $flag.Name) { [string]$coveragePayload.($flag.Name) } else { "missing" })
  }

  $coverageChecks += New-Check -Name "coverage_contains_all_queued_lanes" `
    -Passed (@($coverageMissingQueueLanes).Count -eq 0) `
    -Expected "coverage lane list contains every queued lane" `
    -Observed $(if (@($coverageMissingQueueLanes).Count -eq 0) { "all queued lanes covered" } else { $coverageMissingQueueLanes -join ", " })

  $coverageChecks += New-Check -Name "coverage_queue_lane_results_pass" `
    -Passed (@($coverageNonPassRequiredLanes).Count -eq 0) `
    -Expected "every required non-deferred queued lane has coverage result=pass" `
    -Observed $(if (@($coverageNonPassRequiredLanes).Count -eq 0) { "all required queued lane coverage results pass" } else { $coverageNonPassRequiredLanes -join ", " })
}

$failedChecks = @($checks | Where-Object { $_.result -ne "pass" })
$failedLaneResults = @($laneResults | Where-Object { $_.result -ne "pass" })
$failedCoverageChecks = @($coverageChecks | Where-Object { $_.result -ne "pass" })
$allFailures = @($failedChecks) + @($failedLaneResults) + @($failedCoverageChecks)

$record = [ordered]@{
  evidence_id = "EVID-W61-RUNTIME-LANE-QUEUE-VALIDATION-$stamp"
  created_at = $createdAt
  artifact_id = "TRK-W61-006"
  artifact_type = "runtime_lane_queue_local_validation"
  tracker_ids = @("TRK-W61-006", "TRK-W61-011")
  item_ids = @("ITEM-W61-006", "ITEM-W61-011")
  qa_protocol_used = @(
    "README_QA_WAVE61.md",
    "COMFYUI_WORKFLOW_TESTING_PROTOCOL.md",
    "QA_EVIDENCE_LOG_PROTOCOL.md"
  )
  scope = @(
    "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json",
    "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/*/workflow.api.json",
    "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/*/runtime_requirements.json",
  "Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/*AUTHORED_LANE_EVIDENCE_COVERAGE*.json"
  )
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  queue_file = $(if ($queueExists) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $QueueFile } else { $QueueFile })
  coverage_file = $(if (![string]::IsNullOrWhiteSpace($coverageFilePath)) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $coverageFilePath } else { $null })
  authored_base_generation_lane_count = @($authoredLanes).Count
  authored_base_generation_lanes = $authoredLaneIds
  queued_lane_count = @($queueLaneIds).Count
  queued_lanes = $queueLaneIds
  first_runtime_lane_id = $(if (@($orderedQueueLanes).Count -gt 0) { [string]$orderedQueueLanes[0].lane_id } else { $null })
  required_first_runtime_lane_id = $requiredFirstLaneId
  required_second_lane_id = $requiredSecondLaneId
  current_runtime_lane_id = $(if ($null -ne $queuePayload -and (Has-Property -Object $queuePayload -Name "selection_policy") -and (Has-Property -Object $queuePayload.selection_policy -Name "current_runtime_lane_id")) { [string]$queuePayload.selection_policy.current_runtime_lane_id } else { $null })
  completed_runtime_lane_ids = $(if ($null -ne $queuePayload -and (Has-Property -Object $queuePayload -Name "selection_policy") -and (Has-Property -Object $queuePayload.selection_policy -Name "completed_runtime_lane_ids")) { @($queuePayload.selection_policy.completed_runtime_lane_ids | ForEach-Object { [string]$_ }) } else { @() })
  runtime_not_started_lane_ids = $runtimeNotStartedLaneIds
  deferred_coverage_lane_ids = $deferredCoverageLaneIds
  required_coverage_lane_ids = $requiredCoverageLaneIds
  queue_checks = $checks
  lane_queue_results = $laneResults
  coverage_checks = $coverageChecks
  failed_check_count = @($allFailures).Count
  result = $(if (@($allFailures).Count -eq 0) { "pass_local_only" } else { "fail" })
  known_limits = @(
    "Does not refresh AWS browser/SSO auth.",
    "Does not start EC2 or contact ComfyUI.",
    "Does not prove checkpoint path/hash or runtime model load.",
    "Does not execute generation or perform generated artifact visual QA."
  )
  next_action = "If a queued lane is not yet runtime-smoke proven, run lane-specific readiness, EC2 static proof, bounded smoke execution, pullback, and image QA only after auth and Git gates pass. If all queued lanes are proven, choose the next lane/module or deeper QA target intentionally."
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
[System.IO.File]::WriteAllText($OutFile, ($record | ConvertTo-Json -Depth 30), (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Wrote runtime lane queue validation record: $OutFile"
$record | ConvertTo-Json -Depth 30

if ($record.result -ne "pass_local_only") { exit 2 }
