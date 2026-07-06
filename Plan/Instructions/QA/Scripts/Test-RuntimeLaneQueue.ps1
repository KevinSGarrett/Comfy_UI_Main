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

  $latest = Get-ChildItem -LiteralPath $coverageDir -Filter "W61_AUTHORED_LANE_EVIDENCE_COVERAGE*.json" -File |
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
$requiredCurrentLaneId = "sdxl_realvisxl_base_lane"
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

if ($null -ne $queuePayload) {
  $selectionPolicy = $(if (Has-Property -Object $queuePayload -Name "selection_policy") { $queuePayload.selection_policy } else { $null })
  $runtimeBoundary = $(if (Has-Property -Object $queuePayload -Name "runtime_boundary") { $queuePayload.runtime_boundary } else { $null })
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

  $checks += New-Check -Name "selection_policy_current_lane" `
    -Passed ($currentRuntimeLaneId -eq $requiredCurrentLaneId) `
    -Expected "current_runtime_lane_id=$requiredCurrentLaneId" `
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
    -Passed (@($authoredNotQueued).Count -eq 0) `
    -Expected "every concrete authored base-generation lane is represented in the runtime queue" `
    -Observed $(if (@($authoredNotQueued).Count -eq 0) { "all authored lanes queued" } else { $authoredNotQueued -join ", " })

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
    $expectedStatus = $(if ($laneId -eq $requiredFirstLaneId) { "runtime_smoke_proven" } elseif ($laneId -eq $requiredSecondLaneId) { "current_runtime_blocked_required_checkpoint_missing" } else { "queued" })
    $status = $(if (Has-Property -Object $queuedLane -Name "status") { [string]$queuedLane.status } else { "" })

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
        -Passed ($status -eq $expectedStatus) `
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
  $coverageNonPassQueueLanes = @()
  foreach ($laneId in @($queueLaneIds)) {
    $coverageLaneResult = @($coverageLaneResults | Where-Object { [string]$_.lane_id -eq $laneId } | Select-Object -First 1)
    if ($null -eq $coverageLaneResult -or [string]$coverageLaneResult.result -ne "pass") {
      $coverageNonPassQueueLanes += $laneId
    }
  }

  $coverageChecks += New-Check -Name "coverage_result_pass_local_only" `
    -Passed ((Has-Property -Object $coveragePayload -Name "result") -and [string]$coveragePayload.result -eq "pass_local_only") `
    -Expected "result=pass_local_only" `
    -Observed $(if (Has-Property -Object $coveragePayload -Name "result") { [string]$coveragePayload.result } else { "missing" })

  $coverageChecks += New-Check -Name "coverage_failed_lane_count_zero" `
    -Passed ((Has-Property -Object $coveragePayload -Name "failed_lane_count") -and [int]$coveragePayload.failed_lane_count -eq 0) `
    -Expected "failed_lane_count=0" `
    -Observed $(if (Has-Property -Object $coveragePayload -Name "failed_lane_count") { [string]$coveragePayload.failed_lane_count } else { "missing" })

  $coverageChecks += New-Check -Name "coverage_lane_count_matches_authored_lanes" `
    -Passed ((Has-Property -Object $coveragePayload -Name "authored_base_generation_lane_count") -and [int]$coveragePayload.authored_base_generation_lane_count -eq @($authoredLanes).Count) `
    -Expected ("authored_base_generation_lane_count={0}" -f @($authoredLanes).Count) `
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
    -Passed (@($coverageNonPassQueueLanes).Count -eq 0) `
    -Expected "every queued lane has coverage result=pass" `
    -Observed $(if (@($coverageNonPassQueueLanes).Count -eq 0) { "all queued lane coverage results pass" } else { $coverageNonPassQueueLanes -join ", " })
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
    "Plan/Instructions/QA/Evidence/Workflow_Prerequisite_Matching/W61_AUTHORED_LANE_EVIDENCE_COVERAGE*.json"
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
  next_action = "Provision the current runtime lane model if missing, then run lane-specific readiness, EC2 static proof, bounded smoke execution, pullback, and image QA only after auth and Git gates pass."
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
$record | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $OutFile -Encoding UTF8
Write-Host "Wrote runtime lane queue validation record: $OutFile"
$record | ConvertTo-Json -Depth 30

if ($record.result -ne "pass_local_only") { exit 2 }
