<#
.SYNOPSIS
Validates local pre-EC2 evidence coverage for authored base-generation lanes.

.DESCRIPTION
Discovers base-generation lane directories that contain the concrete workflow,
patch point, runtime requirement, and smoke request contracts. For each authored
lane, it verifies the latest lane-matched local static validation, workflow
smoke dry-run, smoke request body, and lane runtime readiness records. This is
local-only evidence coverage; it does not contact ComfyUI, AWS, Civitai, GitHub,
or EC2, and it does not claim generated artifact QA.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$QueueFile = "",
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

function Test-JsonMatchesLane {
  param(
    [object]$Payload,
    [string]$ExpectedLaneId
  )

  if ($null -eq $Payload -or [string]::IsNullOrWhiteSpace($ExpectedLaneId)) { return $false }
  if ((Has-Property -Object $Payload -Name "lane_id") -and [string]$Payload.lane_id -eq $ExpectedLaneId) {
    return $true
  }
  foreach ($name in @("lane_dir", "workflow_path")) {
    if (Has-Property -Object $Payload -Name $name) {
      $value = ([string]$Payload.$name).Replace("\", "/").TrimEnd("/")
      if ($value -match "/$([regex]::Escape($ExpectedLaneId))(/|$)") {
        return $true
      }
    }
  }
  return $false
}

function Find-LatestEvidence {
  param(
    [string[]]$Directories,
    [string]$ExpectedLaneId,
    [scriptblock]$Predicate
  )

  $files = @()
  foreach ($directory in @($Directories)) {
    if (Test-Path -LiteralPath $directory) {
      $files += @(Get-ChildItem -LiteralPath $directory -Filter "*.json" -File)
    }
  }

  foreach ($file in @($files | Sort-Object LastWriteTime -Descending)) {
    try {
      $payload = Read-JsonFile -Path $file.FullName
      if (!(Test-JsonMatchesLane -Payload $payload -ExpectedLaneId $ExpectedLaneId)) {
        continue
      }
      if (& $Predicate $payload) {
        return [ordered]@{
          path = $file.FullName
          payload = $payload
        }
      }
    } catch {
      continue
    }
  }
  return $null
}

function New-MissingCheck {
  param(
    [string]$Name,
    [string]$Expected
  )

  return [ordered]@{
    name = $Name
    path = $null
    found = $false
    passed = $false
    expected = $Expected
    observed = "missing"
    details = [ordered]@{}
  }
}

function Test-WorkflowStaticEvidence {
  param(
    [string]$LaneId,
    [string[]]$Directories
  )

  $match = Find-LatestEvidence -Directories $Directories -ExpectedLaneId $LaneId -Predicate {
    param($payload)
    return ((Has-Property -Object $payload -Name "qa_status") -and [string]$payload.qa_status -eq "pass")
  }
  if ($null -eq $match) {
    return New-MissingCheck -Name "workflow_static_validation" -Expected "lane-matched qa_status=pass"
  }

  $payload = $match.payload
  $passed = ((Has-Property -Object $payload -Name "qa_status") -and [string]$payload.qa_status -eq "pass")
  return [ordered]@{
    name = "workflow_static_validation"
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $match.path
    found = $true
    passed = $passed
    expected = "qa_status=pass"
    observed = $(if (Has-Property -Object $payload -Name "qa_status") { [string]$payload.qa_status } else { "missing" })
    details = [ordered]@{
      lane_match = (Test-JsonMatchesLane -Payload $payload -ExpectedLaneId $LaneId)
      workflow_path = $(if (Has-Property -Object $payload -Name "workflow_path") { [string]$payload.workflow_path } else { $null })
      node_count = $(if (Has-Property -Object $payload -Name "node_count") { [int]$payload.node_count } else { $null })
      defect_count = $(if (Has-Property -Object $payload -Name "defects") { @($payload.defects).Count } else { $null })
    }
  }
}

function Test-WorkflowSmokeDryRunEvidence {
  param(
    [string]$LaneId,
    [string[]]$Directories
  )

  $match = Find-LatestEvidence -Directories $Directories -ExpectedLaneId $LaneId -Predicate {
    param($payload)
    return (
      (Has-Property -Object $payload -Name "mode") -and [string]$payload.mode -eq "dry_run" -and
      (Has-Property -Object $payload -Name "request_body_written") -and [bool]$payload.request_body_written -and
      (Has-Property -Object $payload -Name "execution_allowed") -and -not [bool]$payload.execution_allowed -and
      (Has-Property -Object $payload -Name "generation_executed") -and -not [bool]$payload.generation_executed
    )
  }
  if ($null -eq $match) {
    return New-MissingCheck -Name "workflow_smoke_dry_run" -Expected "lane-matched dry_run with request_body_written=true, execution_allowed=false, generation_executed=false"
  }

  $payload = $match.payload
  $requestPath = $null
  if (Has-Property -Object $payload -Name "request_body_path") {
    $requestPath = Resolve-ProjectPath -Path ([string]$payload.request_body_path)
  }
  if ([string]::IsNullOrWhiteSpace($requestPath) -and (Has-Property -Object $payload -Name "smoke_request")) {
    $smokeRequest = $payload.smoke_request
    if (Has-Property -Object $smokeRequest -Name "request_file") {
      $requestPath = Resolve-ProjectPath -Path ([string]$smokeRequest.request_file)
    }
  }

  $requestExists = (![string]::IsNullOrWhiteSpace($requestPath) -and (Test-Path -LiteralPath $requestPath))
  $requestJsonValid = $false
  $requestHasPrompt = $false
  $requestError = $null
  if ($requestExists) {
    try {
      $requestPayload = Read-JsonFile -Path $requestPath
      $requestJsonValid = $true
      $requestHasPrompt = (Has-Property -Object $requestPayload -Name "prompt")
    } catch {
      $requestError = $_.Exception.Message
    }
  }

  $passed = (
    (Has-Property -Object $payload -Name "mode") -and [string]$payload.mode -eq "dry_run" -and
    (Has-Property -Object $payload -Name "request_body_written") -and [bool]$payload.request_body_written -and
    (Has-Property -Object $payload -Name "execution_allowed") -and -not [bool]$payload.execution_allowed -and
    (Has-Property -Object $payload -Name "generation_executed") -and -not [bool]$payload.generation_executed -and
    $requestExists -and $requestJsonValid -and $requestHasPrompt
  )

  return [ordered]@{
    name = "workflow_smoke_dry_run"
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $match.path
    found = $true
    passed = $passed
    expected = "dry_run; request body exists; execution_allowed=false; generation_executed=false"
    observed = "mode=$([string]$payload.mode); request_body_written=$([string]$payload.request_body_written); execution_allowed=$([string]$payload.execution_allowed); generation_executed=$([string]$payload.generation_executed)"
    details = [ordered]@{
      lane_match = (Test-JsonMatchesLane -Payload $payload -ExpectedLaneId $LaneId)
      request_body_path = $(if ($requestExists) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $requestPath } else { $requestPath })
      request_body_exists = $requestExists
      request_body_json_valid = $requestJsonValid
      request_body_has_prompt = $requestHasPrompt
      request_body_error = $requestError
    }
  }
}

function Test-LaneReadinessEvidence {
  param(
    [string]$LaneId,
    [string[]]$Directories
  )

  $match = Find-LatestEvidence -Directories $Directories -ExpectedLaneId $LaneId -Predicate {
    param($payload)
    return (
      (Has-Property -Object $payload -Name "local_pre_ec2_ready") -and [bool]$payload.local_pre_ec2_ready -and
      (Has-Property -Object $payload -Name "result") -and @("local_pre_ec2_ready_runtime_blocked_auth", "ready_for_ec2_static_proof", "ready_for_generation") -contains [string]$payload.result
    )
  }
  if ($null -eq $match) {
    return New-MissingCheck -Name "lane_runtime_readiness" -Expected "lane-matched local_pre_ec2_ready=true with recognized readiness result"
  }

  $payload = $match.payload
  $passed = (
    (Has-Property -Object $payload -Name "local_pre_ec2_ready") -and [bool]$payload.local_pre_ec2_ready -and
    (Has-Property -Object $payload -Name "result") -and @("local_pre_ec2_ready_runtime_blocked_auth", "ready_for_ec2_static_proof", "ready_for_generation") -contains [string]$payload.result
  )

  return [ordered]@{
    name = "lane_runtime_readiness"
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $match.path
    found = $true
    passed = $passed
    expected = "local_pre_ec2_ready=true; recognized readiness result"
    observed = "result=$([string]$payload.result); local_pre_ec2_ready=$([string]$payload.local_pre_ec2_ready)"
    details = [ordered]@{
      lane_match = (Test-JsonMatchesLane -Payload $payload -ExpectedLaneId $LaneId)
      failure_category = $(if (Has-Property -Object $payload -Name "failure_category") { [string]$payload.failure_category } else { $null })
      ready_for_ec2_static_proof = $(if (Has-Property -Object $payload -Name "ready_for_ec2_static_proof") { [bool]$payload.ready_for_ec2_static_proof } else { $null })
      ready_for_generation = $(if (Has-Property -Object $payload -Name "ready_for_generation") { [bool]$payload.ready_for_generation } else { $null })
      ec2_started = $(if (Has-Property -Object $payload -Name "ec2_started") { [bool]$payload.ec2_started } else { $null })
      generation_executed = $(if (Has-Property -Object $payload -Name "generation_executed") { [bool]$payload.generation_executed } else { $null })
    }
  }
}

function Find-LatestLocalPackageSmokeMatrix {
  param([string]$Directory)

  if (!(Test-Path -LiteralPath $Directory)) { return $null }
  foreach ($file in @(Get-ChildItem -LiteralPath $Directory -Filter "BASE_GENERATION_REPAIRED_PACKAGE_LOCAL_SMOKE_MATRIX_COMPLETION_*.json" -File | Sort-Object LastWriteTime -Descending)) {
    try {
      $payload = Read-JsonFile -Path $file.FullName
      if (
        (Has-Property -Object $payload -Name "decision") -and
        [string]$payload.decision -eq "base_generation_repaired_package_local_smoke_matrix_complete" -and
        (Has-Property -Object $payload -Name "lanes")
      ) {
        return [ordered]@{
          path = $file.FullName
          payload = $payload
        }
      }
    } catch {
      continue
    }
  }
  return $null
}

function Test-LocalPackageSmokeMatrixEvidence {
  param(
    [string]$LaneId,
    [object]$MatrixMatch
  )

  if ($null -eq $MatrixMatch) {
    return New-MissingCheck -Name "local_package_smoke_matrix" -Expected "latest repaired package-smoke matrix lists lane"
  }

  $payload = $MatrixMatch.payload
  $lanesPassed = @($payload.lanes | Where-Object { [string]$_.decision -eq "local_package_smoke_passed" } | ForEach-Object { [string]$_.lane_id })
  $passed = @($lanesPassed) -contains $LaneId
  return [ordered]@{
    name = "local_package_smoke_matrix"
    path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $MatrixMatch.path
    found = $true
    passed = $passed
    expected = "lane is listed in repaired local package-smoke matrix"
    observed = $(if ($passed) { "lane_passed_with_limitations" } else { "lane_not_listed" })
    details = [ordered]@{
      matrix_decision = [string]$payload.decision
      claim_boundaries = $(if (Has-Property -Object $payload -Name "claim_boundaries") { @($payload.claim_boundaries | ForEach-Object { [string]$_ }) } else { @("local package smoke only") })
    }
  }
}

function Test-LocalRuntimeVisualQaEvidence {
  param(
    [string]$LaneId,
    [string]$RuntimeDirectory,
    [string]$ImageQaDirectory
  )

  $runtimeMatch = Find-LatestEvidence -Directories @($RuntimeDirectory) -ExpectedLaneId $LaneId -Predicate {
    param($payload)
    return (
      (Has-Property -Object $payload -Name "result") -and [string]$payload.result -like "pass*" -and
      (Has-Property -Object $payload -Name "local_only") -and [bool]$payload.local_only -and
      (Has-Property -Object $payload -Name "aws_contacted") -and -not [bool]$payload.aws_contacted -and
      (Has-Property -Object $payload -Name "ec2_started") -and -not [bool]$payload.ec2_started -and
      (Has-Property -Object $payload -Name "generation_executed") -and [bool]$payload.generation_executed
    )
  }
  $imageQaMatch = Find-LatestEvidence -Directories @($ImageQaDirectory) -ExpectedLaneId $LaneId -Predicate {
    param($payload)
    $qaValue = ""
    if (Has-Property -Object $payload -Name "qa_result") {
      $qaValue = [string]$payload.qa_result
    } elseif (Has-Property -Object $payload -Name "result") {
      $qaValue = [string]$payload.result
    }
    return (
      $qaValue -like "pass*" -and
      (Has-Property -Object $payload -Name "local_only") -and [bool]$payload.local_only -and
      (Has-Property -Object $payload -Name "aws_contacted") -and -not [bool]$payload.aws_contacted -and
      (Has-Property -Object $payload -Name "ec2_started") -and -not [bool]$payload.ec2_started
    )
  }

  $runtimePassed = ($null -ne $runtimeMatch)
  $imageQaPassed = ($null -ne $imageQaMatch)
  return [ordered]@{
    name = "local_runtime_visual_qa"
    path = $(if ($imageQaPassed) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $imageQaMatch.path } elseif ($runtimePassed) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $runtimeMatch.path } else { $null })
    found = ($runtimePassed -or $imageQaPassed)
    passed = ($runtimePassed -and $imageQaPassed)
    expected = "lane-matched local runtime generation pass plus local visual QA pass"
    observed = "runtime=$runtimePassed; image_qa=$imageQaPassed"
    details = [ordered]@{
      runtime_evidence = $(if ($runtimePassed) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $runtimeMatch.path } else { $null })
      image_qa_evidence = $(if ($imageQaPassed) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $imageQaMatch.path } else { $null })
      claim_boundary = "Local runtime and visual QA evidence only; not target-runtime EC2 proof, final certification, gold body-mask proof, or Wave71 activation."
    }
  }
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
$baseGenerationRoot = Join-Path $ProjectRoot "Plan\07_IMPLEMENTATION\workflow_templates\base_generation"
$workflowStaticDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Static_Validation"
$workflowRuntimeDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Runtime"
$imageQaDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Image_Artifact_QA"
$runtimeReadinessDir = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Runtime_Readiness"
$localPackageSmokeMatrix = Find-LatestLocalPackageSmokeMatrix -Directory $workflowRuntimeDir
if ([string]::IsNullOrWhiteSpace($QueueFile)) {
  $QueueFile = Join-Path $baseGenerationRoot "runtime_lane_queue.json"
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Workflow_Prerequisite_Matching\W61_AUTHORED_LANE_EVIDENCE_COVERAGE_$stamp.json"
}

$requiredLaneFiles = @(
  "workflow.api.json",
  "patch_points.json",
  "runtime_requirements.json",
  "smoke_test_request.json"
)

$laneResults = @()
$queueLaneIds = @()
$excludedAuthoredLaneIds = @()
if (Test-Path -LiteralPath $QueueFile) {
  try {
    $queuePayload = Read-JsonFile -Path $QueueFile
    if (Has-Property -Object $queuePayload -Name "lanes") {
      $queueLaneIds = @($queuePayload.lanes | ForEach-Object { [string]$_.lane_id } | Where-Object { ![string]::IsNullOrWhiteSpace($_) })
    }
  } catch {
    $queueLaneIds = @()
  }
}
if (Test-Path -LiteralPath $baseGenerationRoot) {
  foreach ($laneDir in Get-ChildItem -LiteralPath $baseGenerationRoot -Directory | Sort-Object Name) {
    $missingLaneFiles = @()
    foreach ($fileName in $requiredLaneFiles) {
      if (!(Test-Path -LiteralPath (Join-Path $laneDir.FullName $fileName))) {
        $missingLaneFiles += $fileName
      }
    }
    if ($missingLaneFiles.Count -gt 0) {
      continue
    }

    $laneId = $laneDir.Name
    if (@($queueLaneIds).Count -gt 0 -and @($queueLaneIds) -notcontains $laneId) {
      $excludedAuthoredLaneIds += $laneId
      continue
    }
    $workflowStaticCheck = Test-WorkflowStaticEvidence -LaneId $laneId -Directories @($workflowStaticDir)
    $workflowSmokeDryRunCheck = Test-WorkflowSmokeDryRunEvidence -LaneId $laneId -Directories @($workflowStaticDir, $workflowRuntimeDir)
    $laneReadinessCheck = Test-LaneReadinessEvidence -LaneId $laneId -Directories @($runtimeReadinessDir)
    $localPackageSmokeCheck = Test-LocalPackageSmokeMatrixEvidence -LaneId $laneId -MatrixMatch $localPackageSmokeMatrix
    $localRuntimeVisualQaCheck = Test-LocalRuntimeVisualQaEvidence -LaneId $laneId -RuntimeDirectory $workflowRuntimeDir -ImageQaDirectory $imageQaDir
    $checks = @(
      $workflowStaticCheck,
      $workflowSmokeDryRunCheck,
      $laneReadinessCheck,
      $localPackageSmokeCheck,
      $localRuntimeVisualQaCheck
    )
    $legacyPreEc2CoveragePassed = ([bool]$workflowSmokeDryRunCheck.passed -and [bool]$laneReadinessCheck.passed)
    $localPackageSmokeCoveragePassed = [bool]$localPackageSmokeCheck.passed
    $localRuntimeVisualQaPassed = [bool]$localRuntimeVisualQaCheck.passed
    $lanePassed = ([bool]$workflowStaticCheck.passed -and ($legacyPreEc2CoveragePassed -or $localPackageSmokeCoveragePassed -or $localRuntimeVisualQaPassed))
    $failures = $(if ($lanePassed) { @() } else { @($checks | Where-Object { -not [bool]$_.passed }) })

    $laneResults += [ordered]@{
      lane_id = $laneId
      lane_dir = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $laneDir.FullName
      authored_contract_files = @($requiredLaneFiles)
      coverage_mode = $(if ($legacyPreEc2CoveragePassed) { "legacy_pre_ec2_readiness" } elseif ($localPackageSmokeCoveragePassed) { "local_package_smoke_matrix" } elseif ($localRuntimeVisualQaPassed) { "local_runtime_visual_qa" } else { "insufficient" })
      required_evidence_checks = $checks
      required_evidence_failures = @($failures).Count
      result = $(if ($lanePassed) { "pass" } else { "fail" })
    }
  }
}

$failedLanes = @($laneResults | Where-Object { $_.result -ne "pass" })
$record = [ordered]@{
  evidence_id = "EVID-W61-AUTHORED-LANE-EVIDENCE-COVERAGE-$stamp"
  created_at = $createdAt
  artifact_id = "TRK-W61-006"
  artifact_type = "authored_lane_local_pre_ec2_evidence_coverage"
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
    "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/*/patch_points.json",
    "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/*/runtime_requirements.json",
    "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/*/smoke_test_request.json",
    "Plan/Instructions/QA/Evidence/Workflow_Static_Validation/*.json",
    "Plan/Instructions/QA/Evidence/Workflow_Runtime/*.json",
    "Plan/Instructions/QA/Evidence/Image_Artifact_QA/*.json",
    "Plan/Instructions/QA/Evidence/Runtime_Readiness/*.json"
  )
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  queue_file = $(if (Test-Path -LiteralPath $QueueFile) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $QueueFile } else { $QueueFile })
  scoped_to_runtime_queue = @($queueLaneIds).Count -gt 0
  queued_lane_count = @($queueLaneIds).Count
  queued_lanes = $queueLaneIds
  excluded_authored_lanes_not_in_queue = $excludedAuthoredLaneIds
  local_package_smoke_matrix = $(if ($null -ne $localPackageSmokeMatrix) { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $localPackageSmokeMatrix.path } else { $null })
  authored_base_generation_lane_count = @($laneResults).Count
  authored_base_generation_lanes = @($laneResults | ForEach-Object { $_.lane_id })
  lane_results = $laneResults
  failed_lane_count = @($failedLanes).Count
  result = $(if (@($laneResults).Count -gt 0 -and @($failedLanes).Count -eq 0) { "pass_local_only" } else { "fail" })
  known_limits = @(
    "Does not prove ComfyUI object_info compatibility.",
    "Does not prove checkpoint path/hash on EC2.",
    "Does not load models or execute generation.",
    "Does not perform new generated artifact visual QA.",
    "When coverage_mode is local_package_smoke_matrix, the lane is covered only by repaired local package-smoke evidence with limitations; this is not final quality certification or target-runtime EC2 proof."
    "When coverage_mode is local_runtime_visual_qa, the lane is covered by existing local runtime and image QA evidence only; this is not target-runtime EC2 proof, final certification, or gold mask proof."
  )
  next_action = "Use this queued-lane coverage with runtime lane queue validation before any future EC2 proof; nonqueued authored lanes require explicit queue selection and their own evidence coverage."
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
[System.IO.File]::WriteAllText($OutFile, ($record | ConvertTo-Json -Depth 20), (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Wrote authored lane evidence coverage record: $OutFile"
$record | ConvertTo-Json -Depth 20

if ($record.result -ne "pass_local_only") { exit 2 }
