<#
.SYNOPSIS
Creates a local-only runtime unblock handoff from the latest gate evidence.

.DESCRIPTION
Reads the latest local auth/profile/readiness/project-readiness evidence and
writes a JSON plus Markdown handoff containing the exact post-auth command
sequence and EC2 safety gates. This script does not contact AWS, GitHub,
Civitai, ComfyUI, or EC2.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LaneId = "sdxl_low_risk_fallback_lane",
  [string]$OutFile = "",
  [string]$MarkdownOutFile = "",
  [string]$RunPackageManifestFile = ""
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
  try {
    $rootFull = [System.IO.Path]::GetFullPath($BasePath).TrimEnd("\", "/")
    $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
    $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
    if ($targetFull.Equals($rootFull, [System.StringComparison]::OrdinalIgnoreCase) -or
        $targetFull.StartsWith("$rootFull$separator", [System.StringComparison]::OrdinalIgnoreCase)) {
      $relative = Get-RelativePathCompat -BasePath $BasePath -TargetPath $TargetPath
      return $relative.Replace("\", "/")
    }
  } catch {
    return $TargetPath
  }
  return $TargetPath
}

function Resolve-ProjectPath {
  param([string]$Path)

  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  if ([System.IO.Path]::IsPathRooted($Path)) {
    return [System.IO.Path]::GetFullPath($Path)
  }
  return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Path.Replace("/", "\")))
}

function Has-Property {
  param(
    [object]$Object,
    [string]$Name
  )

  if ($null -eq $Object) { return $false }
  return ($null -ne $Object.PSObject.Properties[$Name])
}

function Get-PropertyValue {
  param(
    [object]$Object,
    [string]$Name,
    [object]$Default = $null
  )

  if (Has-Property -Object $Object -Name $Name) { return $Object.$Name }
  return $Default
}

function Get-BoolPropertyValue {
  param(
    [object]$Object,
    [string]$Name,
    [bool]$Default = $false
  )

  if (Has-Property -Object $Object -Name $Name) { return [bool]$Object.$Name }
  return $Default
}

function Get-FileSha256Lower {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path) -or !(Test-Path -LiteralPath $Path)) { return $null }
  return (Get-FileHash -Algorithm SHA256 -LiteralPath $Path).Hash.ToLowerInvariant()
}

function Find-LatestFile {
  param(
    [string]$Directory,
    [string]$Filter
  )

  if (!(Test-Path -LiteralPath $Directory)) { return $null }
  $file = Get-ChildItem -LiteralPath $Directory -Filter $Filter -File |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1
  if ($null -eq $file) { return $null }
  return $file.FullName
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
  if (Has-Property -Object $Payload -Name "lane_dir") {
    $laneDirText = ([string]$Payload.lane_dir).Replace("\", "/").TrimEnd("/")
    return $laneDirText.EndsWith("/$ExpectedLaneId", [System.StringComparison]::OrdinalIgnoreCase)
  }
  return $false
}

function Find-LatestJsonByLaneId {
  param(
    [string]$Directory,
    [string]$Filter,
    [string]$ExpectedLaneId
  )

  if (!(Test-Path -LiteralPath $Directory)) { return $null }
  foreach ($file in @(Get-ChildItem -LiteralPath $Directory -Filter $Filter -File | Sort-Object LastWriteTime -Descending)) {
    try {
      $payload = Read-JsonEvidence -Path $file.FullName
      if (Test-JsonMatchesLane -Payload $payload -ExpectedLaneId $ExpectedLaneId) {
        return $file.FullName
      }
    } catch {
      continue
    }
  }
  return $null
}

function Find-LatestJsonByLaneIdAndResult {
  param(
    [string]$Directory,
    [string]$Filter,
    [string]$ExpectedLaneId,
    [string[]]$AcceptableResults
  )

  if (!(Test-Path -LiteralPath $Directory)) { return $null }
  foreach ($file in @(Get-ChildItem -LiteralPath $Directory -Filter $Filter -File | Sort-Object LastWriteTime -Descending)) {
    try {
      $payload = Read-JsonEvidence -Path $file.FullName
      if ((Test-JsonMatchesLane -Payload $payload -ExpectedLaneId $ExpectedLaneId) -and
          (Has-Property -Object $payload -Name "result") -and
          @($AcceptableResults) -contains [string]$payload.result) {
        return $file.FullName
      }
    } catch {
      continue
    }
  }
  return $null
}

function Find-LatestJsonByResult {
  param(
    [string]$Directory,
    [string]$Filter,
    [string[]]$AcceptableResults
  )

  if (!(Test-Path -LiteralPath $Directory)) { return $null }
  foreach ($file in @(Get-ChildItem -LiteralPath $Directory -Filter $Filter -File | Sort-Object LastWriteTime -Descending)) {
    try {
      $payload = Read-JsonEvidence -Path $file.FullName
      if ((Has-Property -Object $payload -Name "result") -and @($AcceptableResults) -contains [string]$payload.result) {
        return $file.FullName
      }
    } catch {
      continue
    }
  }
  return $null
}

function Find-LatestImageQaByRunId {
  param(
    [string]$Directory,
    [string]$Filter,
    [string]$RunId
  )

  if ([string]::IsNullOrWhiteSpace($RunId) -or !(Test-Path -LiteralPath $Directory)) { return $null }
  foreach ($file in @(Get-ChildItem -LiteralPath $Directory -Filter $Filter -File | Sort-Object LastWriteTime -Descending)) {
    try {
      $payload = Read-JsonEvidence -Path $file.FullName
      $candidateText = @(
        [string](Get-PropertyValue -Object $payload -Name "artifact_id" -Default ""),
        [string](Get-PropertyValue -Object $payload -Name "image_path" -Default ""),
        [string](Get-PropertyValue -Object $payload -Name "workflow_reference" -Default "")
      )
      if ((Has-Property -Object $payload -Name "image") -and $null -ne $payload.image) {
        $candidateText += [string](Get-PropertyValue -Object $payload.image -Name "display_path" -Default "")
        $candidateText += [string](Get-PropertyValue -Object $payload.image -Name "supplied_path" -Default "")
      }
      if (Has-Property -Object $payload -Name "evidence_paths") {
        $candidateText += @($payload.evidence_paths | ForEach-Object { [string]$_ })
      }
      if ((($candidateText -join "`n") -like "*$RunId*")) {
        return $file.FullName
      }
    } catch {
      continue
    }
  }
  return $null
}

function Read-JsonEvidence {
  param([string]$Path)

  if ([string]::IsNullOrWhiteSpace($Path) -or !(Test-Path -LiteralPath $Path)) {
    return $null
  }
  return (Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json)
}

function Get-RunPackageSummary {
  param([string]$Path)

  $summary = [ordered]@{
    supplied = $false
    evidence = $null
    found = $false
    valid = $false
    errors = @()
    run_id = $null
    result = $null
    lane_id = $null
    lane_match = $false
    prompt_profile = [ordered]@{
      supplied = $false
      applied = $false
      profile_id = $null
      path = $null
    }
    prompt_request = [ordered]@{
      path = $null
      expected_sha256 = $null
      actual_sha256 = $null
      hash_match = $false
      json_valid = $false
      node_count = 0
    }
  }

  if ([string]::IsNullOrWhiteSpace($Path)) {
    return $summary
  }

  $summary.supplied = $true
  $manifestPath = Resolve-ProjectPath -Path $Path
  $summary.evidence = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $manifestPath
  if (!(Test-Path -LiteralPath $manifestPath)) {
    $summary.errors += "Run package manifest not found: $Path"
    return $summary
  }
  $summary.found = $true

  try {
    $manifest = Read-JsonEvidence -Path $manifestPath
  } catch {
    $summary.errors += "Run package manifest JSON parse failed: $($_.Exception.Message)"
    return $summary
  }

  $summary.run_id = [string](Get-PropertyValue -Object $manifest -Name "run_id" -Default "")
  $summary.result = [string](Get-PropertyValue -Object $manifest -Name "result" -Default "")
  $summary.lane_id = [string](Get-PropertyValue -Object $manifest -Name "lane_id" -Default "")
  $summary.lane_match = ([string]$summary.lane_id -eq [string]$LaneId)
  if (!$summary.lane_match) {
    $summary.errors += "Run package lane_id '$($summary.lane_id)' does not match selected lane '$LaneId'."
  }
  if ([string]$summary.result -ne "pass_local_only") {
    $summary.errors += "Run package result is '$($summary.result)', not pass_local_only."
  }
  if ((Has-Property -Object $manifest -Name "ec2_started") -and [bool]$manifest.ec2_started) {
    $summary.errors += "Run package records ec2_started=true."
  }
  if ((Has-Property -Object $manifest -Name "generation_executed") -and [bool]$manifest.generation_executed) {
    $summary.errors += "Run package records generation_executed=true."
  }

  if ((Has-Property -Object $manifest -Name "prompt_profile") -and $null -ne $manifest.prompt_profile) {
    $summary.prompt_profile.supplied = Get-BoolPropertyValue -Object $manifest.prompt_profile -Name "supplied" -Default $false
    $summary.prompt_profile.applied = Get-BoolPropertyValue -Object $manifest.prompt_profile -Name "applied" -Default $false
    $summary.prompt_profile.profile_id = [string](Get-PropertyValue -Object $manifest.prompt_profile -Name "profile_id" -Default "")
    $summary.prompt_profile.path = [string](Get-PropertyValue -Object $manifest.prompt_profile -Name "path" -Default "")
  }

  $promptRequestPath = $null
  $expectedHash = $null
  if (Has-Property -Object $manifest -Name "generated_files") {
    $promptGenerated = @($manifest.generated_files | Where-Object { [string]$_.path -match '(^|/)prompt_request\.json$' } | Select-Object -First 1)
    if ($promptGenerated.Count -gt 0) {
      $promptRequestPath = [string]$promptGenerated[0].path
      $expectedHash = ([string](Get-PropertyValue -Object $promptGenerated[0] -Name "sha256" -Default "")).ToLowerInvariant()
    }
  }
  if ([string]::IsNullOrWhiteSpace($promptRequestPath) -and
      (Has-Property -Object $manifest -Name "package_dir") -and
      ![string]::IsNullOrWhiteSpace([string]$manifest.package_dir)) {
    $promptRequestPath = ([string]$manifest.package_dir).TrimEnd("/", "\") + "/prompt_request.json"
  }
  if ([string]::IsNullOrWhiteSpace($expectedHash) -and
      (Has-Property -Object $manifest -Name "prompt_request") -and
      $null -ne $manifest.prompt_request) {
    $expectedHash = ([string](Get-PropertyValue -Object $manifest.prompt_request -Name "sha256" -Default "")).ToLowerInvariant()
  }

  if ([string]::IsNullOrWhiteSpace($promptRequestPath)) {
    $summary.errors += "Run package manifest does not identify prompt_request.json."
    return $summary
  }

  $promptFullPath = Resolve-ProjectPath -Path $promptRequestPath
  $summary.prompt_request.path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $promptFullPath
  $summary.prompt_request.expected_sha256 = $expectedHash
  if (!(Test-Path -LiteralPath $promptFullPath)) {
    $summary.errors += "Run package prompt_request.json not found: $promptRequestPath"
    return $summary
  }

  $actualHash = Get-FileSha256Lower -Path $promptFullPath
  $summary.prompt_request.actual_sha256 = $actualHash
  $summary.prompt_request.hash_match = (![string]::IsNullOrWhiteSpace($expectedHash) -and $actualHash -eq $expectedHash)
  if (![string]::IsNullOrWhiteSpace($expectedHash) -and !$summary.prompt_request.hash_match) {
    $summary.errors += "Run package prompt_request.json sha256 does not match manifest."
  }

  try {
    $request = Read-JsonEvidence -Path $promptFullPath
    $summary.prompt_request.json_valid = $true
    if ((Has-Property -Object $request -Name "prompt") -and $null -ne $request.prompt) {
      $summary.prompt_request.node_count = @($request.prompt.PSObject.Properties).Count
    } else {
      $summary.errors += "Run package prompt_request.json has no prompt object."
    }
  } catch {
    $summary.errors += "Run package prompt_request.json parse failed: $($_.Exception.Message)"
  }

  $summary.valid = ($summary.errors.Count -eq 0)
  return $summary
}

function New-CommandStep {
  param(
    [string]$Name,
    [string]$Gate,
    [string]$Command,
    [string]$ExpectedEvidence,
    [string]$WhenToRun
  )

  return [ordered]@{
    name = $Name
    gate = $Gate
    command = $Command
    expected_evidence = $ExpectedEvidence
    when_to_run = $WhenToRun
  }
}

function New-MarkdownCode {
  param([string]$Text)

  $tick = [string][char]96
  return ("{0}{1}{0}" -f $tick, $Text)
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")

$qaRoot = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence"
$runtimeReadinessDir = Join-Path $qaRoot "Runtime_Readiness"
$projectReadinessDir = Join-Path $qaRoot "Project_Readiness"
$workflowPrerequisiteDir = Join-Path $qaRoot "Workflow_Prerequisite_Matching"
$workflowRuntimeDir = Join-Path $qaRoot "Workflow_Runtime"
$modelRegistryCoverageDir = Join-Path $qaRoot "Model_Registry"
$imageArtifactQaDir = Join-Path $qaRoot "Image_Artifact_QA"
$operationsValidationDir = Join-Path $qaRoot "Operations_Static_Validation"
$qaValidationDir = Join-Path $qaRoot "QA_Helper_Static_Validation"
$indexValidationDir = Join-Path $qaRoot "Index_Validation"

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $runtimeReadinessDir "W61_RUNTIME_UNBLOCK_HANDOFF_$stamp.json"
}
if ([string]::IsNullOrWhiteSpace($MarkdownOutFile)) {
  $MarkdownOutFile = [System.IO.Path]::ChangeExtension($OutFile, ".md")
}

$latest = [ordered]@{
  auth_gate = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W60_W61_AWS_AUTH_GATE*.json"
  profile_matrix = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W60_W61_AWS_PROFILE_AUTH_MATRIX*.json"
  lane_readiness = Find-LatestJsonByLaneId -Directory $runtimeReadinessDir -Filter "*LANE_RUNTIME_READINESS*.json" -ExpectedLaneId $LaneId
  project_readiness = Find-LatestJsonByLaneIdAndResult -Directory $projectReadinessDir -Filter "*PROJECT_READINESS*.json" -ExpectedLaneId $LaneId -AcceptableResults @("pass_local_ready_runtime_blocked_auth", "pass_local_ready_runtime_blocked", "pass_local_ready_for_ec2_static_proof", "pass_ready_for_generation", "pass_runtime_smoke_qa_complete")
  runtime_lane_queue = Find-LatestFile -Directory $workflowPrerequisiteDir -Filter "*RUNTIME_LANE_QUEUE*.json"
  model_registry_coverage = Find-LatestFile -Directory $modelRegistryCoverageDir -Filter "*MODEL_REGISTRY_COVERAGE*.json"
  workflow_smoke = Find-LatestJsonByLaneIdAndResult -Directory $workflowRuntimeDir -Filter "*EC2_WORKFLOW_SMOKE*.json" -ExpectedLaneId $LaneId -AcceptableResults @("workflow_smoke_generation_complete")
  operations_validation = Find-LatestJsonByResult -Directory $operationsValidationDir -Filter "W60_OPERATIONS_HELPER_CURRENT_VALIDATION*.json" -AcceptableResults @("pass_local_only")
  qa_validation = Find-LatestJsonByResult -Directory $qaValidationDir -Filter "W61_QA_HELPER_CURRENT_VALIDATION*.json" -AcceptableResults @("pass_local_only")
  index_validation = Find-LatestJsonByResult -Directory $indexValidationDir -Filter "W59_LIVE_INDEX_REFRESH*.json" -AcceptableResults @("pass")
}

$authJson = Read-JsonEvidence -Path $latest.auth_gate
$profileJson = Read-JsonEvidence -Path $latest.profile_matrix
$readinessJson = Read-JsonEvidence -Path $latest.lane_readiness
$projectJson = Read-JsonEvidence -Path $latest.project_readiness
$queueJson = Read-JsonEvidence -Path $latest.runtime_lane_queue
$modelRegistryCoverageJson = Read-JsonEvidence -Path $latest.model_registry_coverage
$workflowSmokeJson = Read-JsonEvidence -Path $latest.workflow_smoke
$operationsJson = Read-JsonEvidence -Path $latest.operations_validation
$qaJson = Read-JsonEvidence -Path $latest.qa_validation
$indexJson = Read-JsonEvidence -Path $latest.index_validation

$authSummary = [ordered]@{
  evidence = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.auth_gate
  result = [string](Get-PropertyValue -Object $authJson -Name "result" -Default "missing_auth_gate")
  failure_category = Get-PropertyValue -Object $authJson -Name "failure_category" -Default "missing_auth_gate"
  account_match = Get-BoolPropertyValue -Object $authJson -Name "account_match" -Default $false
  remote_login_status = [string](Get-PropertyValue -Object $authJson -Name "remote_login_status" -Default "missing_auth_gate")
  ec2_work_allowed = Get-BoolPropertyValue -Object $authJson -Name "ec2_work_allowed" -Default $false
  safe_to_start_ec2 = Get-BoolPropertyValue -Object $authJson -Name "safe_to_start_ec2" -Default $false
  generation_allowed = Get-BoolPropertyValue -Object $authJson -Name "generation_allowed" -Default $false
}

$profileSummary = [ordered]@{
  evidence = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.profile_matrix
  result = [string](Get-PropertyValue -Object $profileJson -Name "result" -Default "missing_profile_matrix")
  expected_account = [string](Get-PropertyValue -Object $profileJson -Name "expected_account" -Default "029530099913")
  profile_count = Get-PropertyValue -Object $profileJson -Name "profile_count" -Default $null
  profiles_matching_expected_count = Get-PropertyValue -Object $profileJson -Name "profiles_matching_expected_count" -Default $null
  safe_to_start_ec2 = Get-BoolPropertyValue -Object $profileJson -Name "safe_to_start_ec2" -Default $false
}

$laneSummary = [ordered]@{
  evidence = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.lane_readiness
  result = [string](Get-PropertyValue -Object $readinessJson -Name "result" -Default "missing_lane_readiness")
  failure_category = Get-PropertyValue -Object $readinessJson -Name "failure_category" -Default "missing_lane_readiness"
  lane_id = [string](Get-PropertyValue -Object $readinessJson -Name "lane_id" -Default "")
  lane_match = ([string](Get-PropertyValue -Object $readinessJson -Name "lane_id" -Default "") -eq [string]$LaneId)
  local_pre_ec2_ready = Get-BoolPropertyValue -Object $readinessJson -Name "local_pre_ec2_ready" -Default $false
  ready_for_ec2_static_proof = Get-BoolPropertyValue -Object $readinessJson -Name "ready_for_ec2_static_proof" -Default $false
  ready_for_generation = Get-BoolPropertyValue -Object $readinessJson -Name "ready_for_generation" -Default $false
}

$projectSummary = [ordered]@{
  evidence = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.project_readiness
  result = [string](Get-PropertyValue -Object $projectJson -Name "result" -Default "missing_project_readiness")
  failure_category = Get-PropertyValue -Object $projectJson -Name "failure_category" -Default "missing_project_readiness"
  lane_id = [string](Get-PropertyValue -Object $projectJson -Name "lane_id" -Default "")
  lane_match = ([string](Get-PropertyValue -Object $projectJson -Name "lane_id" -Default "") -eq [string]$LaneId)
  local_ready = Get-BoolPropertyValue -Object $projectJson -Name "local_ready" -Default $false
  ec2_start_allowed = $false
  generation_allowed = $false
  scan_hit_count = $null
}
if (Has-Property -Object $projectJson -Name "runtime_gates") {
  $projectSummary.ec2_start_allowed = Get-BoolPropertyValue -Object $projectJson.runtime_gates -Name "ec2_start_allowed" -Default $false
  $projectSummary.generation_allowed = Get-BoolPropertyValue -Object $projectJson.runtime_gates -Name "generation_allowed" -Default $false
}
if (Has-Property -Object $projectJson -Name "secret_private_path_scan") {
  $projectSummary.scan_hit_count = Get-PropertyValue -Object $projectJson.secret_private_path_scan -Name "hit_count" -Default $null
}

$queueSummary = [ordered]@{
  evidence = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.runtime_lane_queue
  result = [string](Get-PropertyValue -Object $queueJson -Name "result" -Default "missing_runtime_lane_queue")
  queue_file = [string](Get-PropertyValue -Object $queueJson -Name "queue_file" -Default "")
  selected_lane_id = $LaneId
  selected_lane_in_queue = $false
  selected_lane_order = $null
  first_runtime_lane_id = [string](Get-PropertyValue -Object $queueJson -Name "first_runtime_lane_id" -Default "")
  first_runtime_lane_match = ([string](Get-PropertyValue -Object $queueJson -Name "first_runtime_lane_id" -Default "") -eq [string]$LaneId)
  current_runtime_lane_id = [string](Get-PropertyValue -Object $queueJson -Name "current_runtime_lane_id" -Default "")
  current_runtime_lane_match = ([string](Get-PropertyValue -Object $queueJson -Name "current_runtime_lane_id" -Default "") -eq [string]$LaneId)
  queued_lane_count = Get-PropertyValue -Object $queueJson -Name "queued_lane_count" -Default $null
  failed_check_count = Get-PropertyValue -Object $queueJson -Name "failed_check_count" -Default $null
  local_only = Get-BoolPropertyValue -Object $queueJson -Name "local_only" -Default $false
  aws_contacted = Get-BoolPropertyValue -Object $queueJson -Name "aws_contacted" -Default $true
  github_api_contacted = Get-BoolPropertyValue -Object $queueJson -Name "github_api_contacted" -Default $true
  civitai_contacted = Get-BoolPropertyValue -Object $queueJson -Name "civitai_contacted" -Default $true
  comfyui_contacted = Get-BoolPropertyValue -Object $queueJson -Name "comfyui_contacted" -Default $true
  ec2_started = Get-BoolPropertyValue -Object $queueJson -Name "ec2_started" -Default $true
  generation_executed = Get-BoolPropertyValue -Object $queueJson -Name "generation_executed" -Default $true
  queue_allows_selected_lane_ec2_static_proof = $false
}
if (Has-Property -Object $queueJson -Name "queued_lanes") {
  $queuedLaneIds = @($queueJson.queued_lanes | ForEach-Object { [string]$_ })
  $queueSummary.selected_lane_in_queue = @($queuedLaneIds) -contains [string]$LaneId
}
if (Has-Property -Object $queueJson -Name "lane_queue_results") {
  $selectedQueueLaneMatches = @($queueJson.lane_queue_results | Where-Object { [string]$_.lane_id -eq [string]$LaneId } | Select-Object -First 1)
  if (@($selectedQueueLaneMatches).Count -gt 0) {
    $selectedQueueLane = $selectedQueueLaneMatches[0]
    $queueSummary.selected_lane_in_queue = $true
    if (Has-Property -Object $selectedQueueLane -Name "order") {
      $queueSummary.selected_lane_order = [int]$selectedQueueLane.order
    }
  }
}
$queueSummary.queue_allows_selected_lane_ec2_static_proof = (
  $queueSummary.result -eq "pass_local_only" -and
  $queueSummary.failed_check_count -eq 0 -and
  $queueSummary.local_only -eq $true -and
  $queueSummary.aws_contacted -eq $false -and
  $queueSummary.github_api_contacted -eq $false -and
  $queueSummary.civitai_contacted -eq $false -and
  $queueSummary.comfyui_contacted -eq $false -and
  $queueSummary.ec2_started -eq $false -and
  $queueSummary.generation_executed -eq $false -and
  $queueSummary.selected_lane_in_queue -eq $true -and
  $queueSummary.current_runtime_lane_match -eq $true
)

$modelRegistryCoverageSummary = [ordered]@{
  evidence = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.model_registry_coverage
  result = [string](Get-PropertyValue -Object $modelRegistryCoverageJson -Name "result" -Default "missing_model_registry_coverage")
  selected_lane_id = $LaneId
  selected_lane_covered = $false
  selected_lane_result = $null
  active_lane_ids = @()
  failed_check_count = Get-PropertyValue -Object $modelRegistryCoverageJson -Name "failed_check_count" -Default $null
  registry_record_count = Get-PropertyValue -Object $modelRegistryCoverageJson -Name "registry_record_count" -Default $null
  runtime_validation_queue_row_count = Get-PropertyValue -Object $modelRegistryCoverageJson -Name "runtime_validation_queue_row_count" -Default $null
  local_only = Get-BoolPropertyValue -Object $modelRegistryCoverageJson -Name "local_only" -Default $false
  aws_contacted = Get-BoolPropertyValue -Object $modelRegistryCoverageJson -Name "aws_contacted" -Default $true
  github_api_contacted = Get-BoolPropertyValue -Object $modelRegistryCoverageJson -Name "github_api_contacted" -Default $true
  civitai_contacted = Get-BoolPropertyValue -Object $modelRegistryCoverageJson -Name "civitai_contacted" -Default $true
  comfyui_contacted = Get-BoolPropertyValue -Object $modelRegistryCoverageJson -Name "comfyui_contacted" -Default $true
  ec2_started = Get-BoolPropertyValue -Object $modelRegistryCoverageJson -Name "ec2_started" -Default $true
  generation_executed = Get-BoolPropertyValue -Object $modelRegistryCoverageJson -Name "generation_executed" -Default $true
  coverage_allows_selected_lane_ec2_static_proof = $false
}
if (Has-Property -Object $modelRegistryCoverageJson -Name "active_lane_ids") {
  $coverageLaneIds = @($modelRegistryCoverageJson.active_lane_ids | ForEach-Object { [string]$_ })
  $modelRegistryCoverageSummary.active_lane_ids = $coverageLaneIds
  $modelRegistryCoverageSummary.selected_lane_covered = @($coverageLaneIds) -contains [string]$LaneId
}
if (Has-Property -Object $modelRegistryCoverageJson -Name "lane_results") {
  $selectedCoverageLaneMatches = @($modelRegistryCoverageJson.lane_results | Where-Object { [string]$_.lane_id -eq [string]$LaneId } | Select-Object -First 1)
  if (@($selectedCoverageLaneMatches).Count -gt 0) {
    $modelRegistryCoverageSummary.selected_lane_covered = $true
    if (Has-Property -Object $selectedCoverageLaneMatches[0] -Name "result") {
      $modelRegistryCoverageSummary.selected_lane_result = [string]$selectedCoverageLaneMatches[0].result
    }
  }
}
$modelRegistryCoverageSummary.coverage_allows_selected_lane_ec2_static_proof = (
  $modelRegistryCoverageSummary.result -eq "pass_local_only" -and
  $modelRegistryCoverageSummary.failed_check_count -eq 0 -and
  $modelRegistryCoverageSummary.local_only -eq $true -and
  $modelRegistryCoverageSummary.aws_contacted -eq $false -and
  $modelRegistryCoverageSummary.github_api_contacted -eq $false -and
  $modelRegistryCoverageSummary.civitai_contacted -eq $false -and
  $modelRegistryCoverageSummary.comfyui_contacted -eq $false -and
  $modelRegistryCoverageSummary.ec2_started -eq $false -and
  $modelRegistryCoverageSummary.generation_executed -eq $false -and
  $modelRegistryCoverageSummary.selected_lane_covered -eq $true -and
  $modelRegistryCoverageSummary.selected_lane_result -eq "pass"
)

$workflowSmokeSummary = [ordered]@{
  evidence = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.workflow_smoke
  result = [string](Get-PropertyValue -Object $workflowSmokeJson -Name "result" -Default "missing_workflow_smoke")
  lane_id = [string](Get-PropertyValue -Object $workflowSmokeJson -Name "lane_id" -Default "")
  lane_match = $false
  run_id = [string](Get-PropertyValue -Object $workflowSmokeJson -Name "run_id" -Default "")
  generation_executed = Get-BoolPropertyValue -Object $workflowSmokeJson -Name "generation_executed" -Default $false
  final_state = [string](Get-PropertyValue -Object $workflowSmokeJson -Name "final_state" -Default "")
  remote_artifact_root = [string](Get-PropertyValue -Object $workflowSmokeJson -Name "remote_artifact_root" -Default "")
  local_pullback_status = ""
  output_image_count = 0
  complete = $false
}
$workflowSmokeSummary.lane_match = ([string]$workflowSmokeSummary.lane_id -eq [string]$LaneId)
if (Has-Property -Object $workflowSmokeJson -Name "local_pullback") {
  $workflowSmokeSummary.local_pullback_status = [string](Get-PropertyValue -Object $workflowSmokeJson.local_pullback -Name "status" -Default "")
}
if (Has-Property -Object $workflowSmokeJson -Name "remote_result") {
  $workflowSmokeSummary.output_image_count = @($workflowSmokeJson.remote_result.output_images | Where-Object { [bool]$_.copied }).Count
}
$workflowSmokeSummary.complete = (
  [string]$workflowSmokeSummary.result -eq "workflow_smoke_generation_complete" -and
  [bool]$workflowSmokeSummary.lane_match -and
  [bool]$workflowSmokeSummary.generation_executed -and
  [string]$workflowSmokeSummary.final_state -eq "stopped" -and
  (($workflowSmokeSummary.output_image_count -as [int]) -gt 0)
)

$pullbackRecordPath = $null
if (![string]::IsNullOrWhiteSpace([string]$workflowSmokeSummary.run_id)) {
  $candidatePullbackRecord = Join-Path $ProjectRoot "Plan\Instructions\Operations\Pulled_Back_Artifacts\$($workflowSmokeSummary.run_id)\PULLBACK_RECORD.json"
  if (Test-Path -LiteralPath $candidatePullbackRecord) {
    $pullbackRecordPath = $candidatePullbackRecord
  }
}
$pullbackRecordJson = Read-JsonEvidence -Path $pullbackRecordPath
$pullbackSummary = [ordered]@{
  evidence = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $pullbackRecordPath
  run_id = [string](Get-PropertyValue -Object $pullbackRecordJson -Name "run_id" -Default "")
  run_match = ([string](Get-PropertyValue -Object $pullbackRecordJson -Name "run_id" -Default "") -eq [string]$workflowSmokeSummary.run_id)
  status = [string](Get-PropertyValue -Object $pullbackRecordJson -Name "status" -Default "missing_pullback_record")
  hashes_verified = Get-BoolPropertyValue -Object $pullbackRecordJson -Name "hashes_verified" -Default $false
  file_count_remote = Get-PropertyValue -Object $pullbackRecordJson -Name "file_count_remote" -Default $null
  file_count_local = Get-PropertyValue -Object $pullbackRecordJson -Name "file_count_local" -Default $null
  qa_required_count = 0
  complete = $false
}
if (Has-Property -Object $pullbackRecordJson -Name "qa_required_files") {
  $pullbackSummary.qa_required_count = @($pullbackRecordJson.qa_required_files).Count
}
$pullbackSummary.complete = (
  [bool]$pullbackSummary.run_match -and
  [string]$pullbackSummary.status -eq "pullback_hashes_verified" -and
  [bool]$pullbackSummary.hashes_verified -and
  ($pullbackSummary.file_count_remote -as [int]) -gt 0 -and
  ($pullbackSummary.file_count_remote -as [int]) -eq ($pullbackSummary.file_count_local -as [int])
)

$imageQaTechnicalPath = Find-LatestImageQaByRunId -Directory $imageArtifactQaDir -Filter "*IMAGE_QA_TECHNICAL*.json" -RunId $workflowSmokeSummary.run_id
$imageQaVisualPath = Find-LatestImageQaByRunId -Directory $imageArtifactQaDir -Filter "*IMAGE_QA_VISUAL*.json" -RunId $workflowSmokeSummary.run_id
$imageQaTechnicalJson = Read-JsonEvidence -Path $imageQaTechnicalPath
$imageQaVisualJson = Read-JsonEvidence -Path $imageQaVisualPath
$imageQaTechnicalSummary = [ordered]@{
  evidence = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $imageQaTechnicalPath
  artifact_id = [string](Get-PropertyValue -Object $imageQaTechnicalJson -Name "artifact_id" -Default "")
  qa_status = [string](Get-PropertyValue -Object $imageQaTechnicalJson -Name "qa_status" -Default "missing_image_technical_qa")
  technical_integrity = ""
  resolution_check = ""
  image_sha256 = $null
  width = $null
  height = $null
  complete = $false
}
if (Has-Property -Object $imageQaTechnicalJson -Name "scores") {
  $imageQaTechnicalSummary.technical_integrity = [string](Get-PropertyValue -Object $imageQaTechnicalJson.scores -Name "technical_integrity" -Default "")
  $imageQaTechnicalSummary.resolution_check = [string](Get-PropertyValue -Object $imageQaTechnicalJson.scores -Name "resolution_check" -Default "")
}
if (Has-Property -Object $imageQaTechnicalJson -Name "image") {
  $imageQaTechnicalSummary.image_sha256 = [string](Get-PropertyValue -Object $imageQaTechnicalJson.image -Name "sha256" -Default "")
  $imageQaTechnicalSummary.width = Get-PropertyValue -Object $imageQaTechnicalJson.image -Name "width" -Default $null
  $imageQaTechnicalSummary.height = Get-PropertyValue -Object $imageQaTechnicalJson.image -Name "height" -Default $null
}
$imageQaTechnicalSummary.complete = (
  [string]$imageQaTechnicalSummary.qa_status -eq "pending_visual_review" -and
  [string]$imageQaTechnicalSummary.technical_integrity -eq "pass" -and
  [string]$imageQaTechnicalSummary.resolution_check -eq "pass" -and
  ($imageQaTechnicalSummary.width -as [int]) -gt 0 -and
  ($imageQaTechnicalSummary.height -as [int]) -gt 0
)

$imageQaVisualSummary = [ordered]@{
  evidence = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $imageQaVisualPath
  artifact_id = [string](Get-PropertyValue -Object $imageQaVisualJson -Name "artifact_id" -Default "")
  result = [string](Get-PropertyValue -Object $imageQaVisualJson -Name "result" -Default "missing_image_visual_qa")
  qa_score = Get-PropertyValue -Object $imageQaVisualJson -Name "qa_score" -Default $null
  pass_threshold = Get-PropertyValue -Object $imageQaVisualJson -Name "pass_threshold" -Default $null
  decision = [string](Get-PropertyValue -Object $imageQaVisualJson -Name "decision" -Default "")
  complete = $false
}
$imageQaVisualSummary.complete = (
  ([string]$imageQaVisualSummary.result).StartsWith("pass", [System.StringComparison]::OrdinalIgnoreCase) -and
  ($imageQaVisualSummary.qa_score -as [int]) -ge ($imageQaVisualSummary.pass_threshold -as [int])
)

$runtimeSmokeQaComplete = (
  [bool]$workflowSmokeSummary.complete -and
  [bool]$pullbackSummary.complete -and
  [bool]$imageQaTechnicalSummary.complete -and
  [bool]$imageQaVisualSummary.complete
)

$helperSummary = [ordered]@{
  operations_validation = [ordered]@{
    evidence = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.operations_validation
    result = [string](Get-PropertyValue -Object $operationsJson -Name "result" -Default "missing_operations_validation")
  }
  qa_validation = [ordered]@{
    evidence = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.qa_validation
    result = [string](Get-PropertyValue -Object $qaJson -Name "result" -Default "missing_qa_validation")
  }
  index_validation = [ordered]@{
    evidence = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.index_validation
    result = [string](Get-PropertyValue -Object $indexJson -Name "result" -Default "missing_index_validation")
  }
}
$runPackageSummary = Get-RunPackageSummary -Path $RunPackageManifestFile
$runPackageCommandArg = ""
if ($runPackageSummary.supplied) {
  $runPackageCommandArg = " -RunPackageManifestFile `"$((Resolve-ProjectPath -Path $RunPackageManifestFile))`""
}

$result = "handoff_failed_local_readiness"
$failureCategory = "local_project_readiness_failed"
$nextRequiredAction = "inspect_local_readiness_evidence"
if ($runtimeSmokeQaComplete) {
  $result = "handoff_runtime_smoke_qa_complete"
  $failureCategory = $null
  $nextRequiredAction = "checkpoint_runtime_smoke_evidence_and_advance_next_goal"
} elseif ($workflowSmokeSummary.complete) {
  $result = "handoff_ready_for_pullback_qa"
  $failureCategory = "artifact_pullback_qa_pending"
  $nextRequiredAction = "complete_artifact_pullback_and_image_qa"
} elseif ($projectSummary.local_ready -and -not $authSummary.safe_to_start_ec2) {
  $result = "handoff_ready_runtime_blocked_auth"
  $failureCategory = $(if (![string]::IsNullOrWhiteSpace([string]$authSummary.failure_category)) { [string]$authSummary.failure_category } else { "aws_auth_blocked" })
  $nextRequiredAction = "complete_aws_browser_sso_login"
} elseif ($projectSummary.local_ready -and $authSummary.safe_to_start_ec2 -and -not $queueSummary.queue_allows_selected_lane_ec2_static_proof) {
  $result = "handoff_lane_queue_order_blocked"
  $failureCategory = "runtime_lane_queue_order_blocked"
  $nextRequiredAction = "inspect_runtime_lane_queue"
} elseif ($projectSummary.local_ready -and $authSummary.safe_to_start_ec2 -and -not $modelRegistryCoverageSummary.coverage_allows_selected_lane_ec2_static_proof) {
  $result = "handoff_model_registry_blocked"
  $failureCategory = "model_registry_coverage_blocked"
  $nextRequiredAction = "rerun_model_registry_coverage"
} elseif ($projectSummary.local_ready -and $authSummary.safe_to_start_ec2 -and -not $laneSummary.ready_for_ec2_static_proof) {
  $result = "handoff_auth_ready_lane_not_ready"
  $failureCategory = $(if (![string]::IsNullOrWhiteSpace([string]$laneSummary.failure_category)) { [string]$laneSummary.failure_category } else { "lane_readiness_blocked" })
  $nextRequiredAction = "rerun_lane_readiness_and_inspect_gate"
} elseif ($projectSummary.local_ready -and $laneSummary.ready_for_ec2_static_proof -and -not $laneSummary.ready_for_generation) {
  $result = "handoff_ready_for_ec2_static_proof"
  $failureCategory = "missing_ec2_static_proof"
  $nextRequiredAction = "run_ec2_static_proof"
} elseif ($projectSummary.local_ready -and $laneSummary.ready_for_generation) {
  $result = "handoff_ready_for_generation"
  $failureCategory = $null
  $nextRequiredAction = "run_bounded_workflow_smoke"
}

$commandSequence = @(
  (New-CommandStep -Name "aws_browser_sso_login" -Gate "external_interactive_browser_required" -Command "aws login --remote" -ExpectedEvidence "AWS CLI login refreshed for account 029530099913" -WhenToRun "Only while EC2 gates remain blocked by expired AWS auth."),
  (New-CommandStep -Name "auth_gate_recheck" -Gate "after_aws_login" -Command "powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-AwsAuthGate.ps1 -AttemptRemoteLogin -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W60_W61_AWS_AUTH_GATE_<timestamp>.json" -ExpectedEvidence "result=pass, ec2_work_allowed=true, safe_to_start_ec2=true, account_match=true" -WhenToRun "Immediately after AWS browser/SSO login."),
  (New-CommandStep -Name "profile_matrix_recheck" -Gate "after_auth_gate_or_for_diagnosis" -Command "powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-AwsProfileAuthMatrix.ps1 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W60_W61_AWS_PROFILE_AUTH_MATRIX_<timestamp>.json" -ExpectedEvidence "At least one profile authenticates to account 029530099913, or a clear diagnostic if not." -WhenToRun "After auth refresh or when account/profile mismatch is suspected."),
  (New-CommandStep -Name "runtime_lane_queue_recheck" -Gate "before_any_ec2_execute" -Command "powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\Test-RuntimeLaneQueue.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Prerequisite_Matching\W63_RUNTIME_LANE_QUEUE_VALIDATION_<timestamp>.json" -ExpectedEvidence "result=pass_local_only, current_runtime_lane_id=$LaneId, selected lane in queue, failed_check_count=0." -WhenToRun "Immediately before EC2 static proof if queue files or evidence changed."),
  (New-CommandStep -Name "model_registry_coverage_recheck" -Gate "before_any_ec2_execute" -Command "powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\Test-WorkflowModelRegistryCoverage.ps1 -ProjectRoot C:\Comfy_UI_Main -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Model_Registry\W61_MODEL_REGISTRY_COVERAGE_<timestamp>.json" -ExpectedEvidence "result=pass_local_only, selected lane $LaneId has result=pass, failed_check_count=0, registry records and runtime-validation queue rows exist." -WhenToRun "Immediately before EC2 static proof if model registry, runtime requirements, or queue files changed."),
  (New-CommandStep -Name "local_comfyui_dev_preflight" -Gate "before_optional_local_iteration" -Command "powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\Test-LocalComfyUIDevPreflight.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId $LaneId -LocalComfyRoot <path-to-local-ComfyUI>" -ExpectedEvidence "Local dev candidate status recorded without claiming EC2 equivalence." -WhenToRun "Use while EC2 is stopped for prompt or workflow iteration when a local ComfyUI checkout exists."),
  (New-CommandStep -Name "deploy_bundle_build" -Gate "before_ec2_sync_or_execute" -Command "powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\tools\New-EC2DeployBundle.ps1 -ProjectRoot C:\Comfy_UI_Main -LaneId $LaneId -RunPackageManifestFile <run-package-manifest>" -ExpectedEvidence "DEPLOY_BUNDLE_MANIFEST.json and bundle zip created while EC2 is stopped." -WhenToRun "After run package creation and before any EC2 runtime window."),
  (New-CommandStep -Name "deploy_bundle_s3_publish" -Gate "before_ec2_sync_or_execute" -Command "powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Publish-DeployBundleToS3.ps1 -BundleManifestFile <deploy-bundle-manifest> -S3BaseUri s3://<bucket>/<deploy-bundle-prefix>" -ExpectedEvidence "s3_bundle_uri and bundle_zip_sha256 recorded before EC2 starts." -WhenToRun "Add -Execute only after AWS auth and S3 bundle-prefix permissions are verified."),
  (New-CommandStep -Name "git_checkpoint_recheck" -Gate "before_any_ec2_execute" -Command "git -C C:\Comfy_UI_Main status --short --branch; git -C C:\Comfy_UI_Main rev-parse HEAD; git -C C:\Comfy_UI_Main rev-parse origin/main" -ExpectedEvidence "Working tree clean and local HEAD equals origin/main before any EC2 helper runs with -Execute." -WhenToRun "Immediately before EC2 static proof or workflow smoke execution."),
  (New-CommandStep -Name "emergency_stop_schedule" -Gate "before_any_ec2_execute" -Command "powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-EC2EmergencyStopSchedule.ps1 -SchedulerRoleArn arn:aws:iam::<account-id>:role/<scheduler-stop-role> -StopAfterMinutes 60 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W63_EC2_EMERGENCY_STOP_SCHEDULE_<timestamp>.json" -ExpectedEvidence "One-time EventBridge Scheduler stop created or explicit missing-role blocker recorded." -WhenToRun "Before a live EC2 window when the scheduler role exists."),
  (New-CommandStep -Name "realvisxl_model_s3_install" -Gate "before_realvisxl_static_proof" -Command "powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Install-EC2ModelFromS3.ps1 -SourceS3Uri s3://<bucket>/<model-cache-prefix>/realvisxlV50_v50Bakedvae.safetensors -ExpectedSha256 6A35A7855770AE9820A3C931D4964C3817B6D9E3C6F9C4DABB5B3A94E5643B80 -MaxEc2RuntimeMinutes 20 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Model_Registry\W63_EC2_REALVISXL_MODEL_INSTALL_<timestamp>.json" -ExpectedEvidence "result=install_model_hash_verified, final_state=stopped, generation_executed=false." -WhenToRun "For RealVisXL only, after the checkpoint exists in an approved S3 model-cache prefix."),
  (New-CommandStep -Name "lane_readiness_recheck" -Gate "auth_gate_safe_to_start_ec2_true" -Command "powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-LaneRuntimeReadiness.ps1 -LaneId $LaneId -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_<timestamp>.json" -ExpectedEvidence "local_pre_ec2_ready=true, lane_id=$LaneId, and ready_for_ec2_static_proof=true before EC2 static proof." -WhenToRun "Only after auth gate reports safe_to_start_ec2=true."),
  (New-CommandStep -Name "ec2_static_proof" -Gate "ready_for_ec2_static_proof_true" -Command "powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1 -LaneId $LaneId -Execute -SkipGitLfsPull -DeployBundleS3Uri s3://<bucket>/<deploy-bundle-prefix>/<run-id>/<commit>/<bundle>.zip -DeployBundleSha256 <bundle_sha256> -MaxEc2RuntimeMinutes 25 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W61_EC2_LANE_STATIC_PROOF_<timestamp>.json" -ExpectedEvidence "Object-info node availability, checkpoint path, checkpoint size/hash, LaneId match, S3 bundle hash verification when supplied, and EC2 stop verification." -WhenToRun "Only after readiness reports ready_for_ec2_static_proof=true."),
  (New-CommandStep -Name "bounded_workflow_smoke" -Gate "static_proof_generation_allowed" -Command "powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1 -LaneId $LaneId -Execute -SkipGitLfsPull -DeployBundleS3Uri s3://<bucket>/<deploy-bundle-prefix>/<run-id>/<commit>/<bundle>.zip -DeployBundleSha256 <bundle_sha256> -MaxEc2RuntimeMinutes 45 -StaticProofFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W61_EC2_LANE_STATIC_PROOF_<timestamp>.json -ReadinessFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_<timestamp>.json$runPackageCommandArg -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Runtime\W61_EC2_WORKFLOW_SMOKE_RUN_EXECUTION_<timestamp>.json" -ExpectedEvidence $(if ($runPackageSummary.supplied) { "Bounded prompt execution from validated run package $($runPackageSummary.run_id), LaneId-matched static proof/readiness, S3 deploy bundle preference, remote artifact manifest, pullback route, and EC2 stop verification." } else { "Bounded prompt execution, LaneId-matched static proof/readiness, S3 deploy bundle preference, remote artifact manifest, pullback route, and EC2 stop verification." }) -WhenToRun "Only after EC2 static proof permits generation."),
  (New-CommandStep -Name "artifact_pullback_record" -Gate "generated_artifacts_pulled_back" -Command "powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-EC2PullbackRecord.ps1 -RunId <run_id> -LocalDestination C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts\<run_id> -RemoteManifestFile C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts\<run_id>\REMOTE_ARTIFACT_MANIFEST.json" -ExpectedEvidence "PULLBACK_RECORD.json with count/hash match and QA routing." -WhenToRun "After generated artifacts and remote manifest exist locally."),
  (New-CommandStep -Name "image_artifact_qa" -Gate "pullback_hashes_verified" -Command "powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\New-ImageArtifactQARecord.ps1 -ImagePath <pulled-back-image> -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W61_IMAGE_QA_<timestamp>.json -ChecklistOutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W61_IMAGE_QA_CHECKLIST_<timestamp>.md" -ExpectedEvidence "Image technical QA record and human/visual review checklist." -WhenToRun "After pullback hashes are verified.")
)

$safetyInvariants = [ordered]@{
  approved_instance_id = "i-0560bf8d143f93bb1"
  expected_aws_account = "029530099913"
  expected_idle_state = "stopped"
  do_not_start_ec2_unless_auth_safe = "Test-AwsAuthGate.ps1 must report ec2_work_allowed=true and safe_to_start_ec2=true."
  do_not_start_ec2_unless_runtime_lane_queue_allows = "Test-RuntimeLaneQueue.ps1 must report current_runtime_lane_id=$LaneId, selected lane in queue, and failed_check_count=0."
  do_not_start_ec2_unless_model_registry_coverage_passes = "Test-WorkflowModelRegistryCoverage.ps1 must report result=pass_local_only, selected lane $LaneId result=pass, and failed_check_count=0."
  do_not_start_ec2_unless_git_checkpoint_clean = "EC2 execution helpers must see local HEAD equal origin/main with a clean working tree so remote git pull can reproduce the intended commit."
  do_not_start_ec2_unless_lane_ready = "Test-LaneRuntimeReadiness.ps1 must report lane_id=$LaneId and ready_for_ec2_static_proof=true."
  prepare_deploy_bundle_before_ec2 = "Build and upload a deploy bundle to S3 before EC2 starts whenever S3 is available; EC2 helpers should prefer -DeployBundleS3Uri and -DeployBundleSha256."
  do_not_use_git_lfs_for_model_binaries = "Model checkpoints must be provisioned through S3/model-cache or another approved non-Git path, never through Git LFS as the default."
  install_missing_realvisxl_before_generation = "For RealVisXL, Install-EC2ModelFromS3.ps1 must verify the expected SHA256 before workflow smoke generation."
  use_emergency_stop_for_live_windows = "Create an EventBridge Scheduler emergency stop and use the instance-side watchdog when permissions allow before live EC2 runtime windows."
  do_not_rerun_completed_runtime_smoke = "If workflow smoke, pullback hash verification, technical image QA, and visual image QA are complete for a lane, do not rerun EC2 for that same proof; checkpoint evidence and advance."
  do_not_run_generation_without_static_proof = "Invoke-EC2LaneStaticProof.ps1 -Execute must record object-info/path/hash proof before workflow smoke generation."
  stop_ec2_after_runtime_work = "Any EC2 runtime action must stop instance i-0560bf8d143f93bb1 and verify stopped."
}
if ($runPackageSummary.supplied) {
  $safetyInvariants["use_verified_run_package"] = "Invoke-EC2WorkflowSmokeRun.ps1 must use run package $($runPackageSummary.evidence), and run_package.valid must be true before generation."
}

$markdownPathForRecord = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $MarkdownOutFile
$record = [ordered]@{
  evidence_id = "W61-RUNTIME-UNBLOCK-HANDOFF-$stamp"
  created_at = $createdAt
  artifact_id = "TRK-W61-006"
  artifact_type = "runtime_unblock_handoff"
  tracker_ids = @("TRK-W61-006", "TRK-W61-007", "TRK-W60-010")
  qa_protocol_used = @(
    "README_OPERATIONS_WAVE60.md",
    "SECRETS_ENV_HANDLING_PROTOCOL.md",
    "QA_EVIDENCE_LOG_PROTOCOL.md"
  )
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  ec2_started = $false
  generation_executed = $false
  lane_id = $LaneId
  result = $result
  failure_category = $failureCategory
  next_required_action = $nextRequiredAction
  latest_evidence = [ordered]@{
    auth_gate = $authSummary.evidence
    profile_matrix = $profileSummary.evidence
    lane_readiness = $laneSummary.evidence
    project_readiness = $projectSummary.evidence
    runtime_lane_queue = $queueSummary.evidence
    model_registry_coverage = $modelRegistryCoverageSummary.evidence
    workflow_smoke = $workflowSmokeSummary.evidence
    pullback_record = $pullbackSummary.evidence
    image_qa_technical = $imageQaTechnicalSummary.evidence
    image_qa_visual = $imageQaVisualSummary.evidence
    run_package = $runPackageSummary.evidence
    operations_validation = $helperSummary.operations_validation.evidence
    qa_validation = $helperSummary.qa_validation.evidence
    index_validation = $helperSummary.index_validation.evidence
  }
  gate_summary = [ordered]@{
    auth_gate = $authSummary
    profile_matrix = $profileSummary
    lane_readiness = $laneSummary
    project_readiness = $projectSummary
    runtime_lane_queue = $queueSummary
    model_registry_coverage = $modelRegistryCoverageSummary
    workflow_smoke = $workflowSmokeSummary
    pullback_record = $pullbackSummary
    image_qa_technical = $imageQaTechnicalSummary
    image_qa_visual = $imageQaVisualSummary
    runtime_smoke_qa_complete = $runtimeSmokeQaComplete
    run_package = $runPackageSummary
    helper_validation = $helperSummary
  }
  safety_invariants = $safetyInvariants
  command_sequence = $commandSequence
  command_step_count = @($commandSequence).Count
  markdown_path = $markdownPathForRecord
  markdown_written = $false
  known_issues = @(
    "This is a local handoff only and does not refresh AWS auth.",
    "AWS auth remains the runtime blocker if safe_to_start_ec2 is false.",
    $(if ($runtimeSmokeQaComplete) { "Runtime smoke QA is complete for this lane, but this does not certify final portfolio quality or broader prompt coverage." } else { "This handoff does not yet prove artifact pullback and media QA." })
  )
}

$markdownFence = ([string][char]96) * 3
$markdownCommands = ($commandSequence | ForEach-Object {
  @(
    "### $($_.name)",
    "",
    "Gate: $($_.gate)",
    "",
    ("{0}powershell" -f $markdownFence),
    "$($_.command)",
    $markdownFence,
    "",
    "Expected evidence: $($_.expected_evidence)",
    ""
  ) -join "`n"
}) -join "`n"

$mdApprovedInstanceId = New-MarkdownCode "i-0560bf8d143f93bb1"
$mdExpectedAwsAccount = New-MarkdownCode "029530099913"
$mdAuthEc2Allowed = New-MarkdownCode "ec2_work_allowed=true"
$mdAuthSafeToStart = New-MarkdownCode "safe_to_start_ec2=true"
$mdCurrentRuntimeLane = New-MarkdownCode "current_runtime_lane_id=$LaneId"
$mdFailedCheckZero = New-MarkdownCode "0"
$mdCoverageResult = New-MarkdownCode "result=pass_local_only"
$mdCoverageLane = New-MarkdownCode $LaneId
$mdCoveragePass = New-MarkdownCode "pass"
$mdHead = New-MarkdownCode "HEAD"
$mdOriginMain = New-MarkdownCode "origin/main"
$mdLaneReadyId = New-MarkdownCode "lane_id=$LaneId"
$mdReadyForStaticProof = New-MarkdownCode "ready_for_ec2_static_proof=true"
$mdStopped = New-MarkdownCode "stopped"

$markdown = @"
# Runtime Unblock Handoff

- created_at: $createdAt
- result: $result
- failure_category: $failureCategory
- next_required_action: $nextRequiredAction
- lane: $LaneId
- local_only: true
- aws_contacted: false
- ec2_started: false
- generation_executed: false

## Current Gate Summary

- Auth gate: $($authSummary.result), safe_to_start_ec2=$($authSummary.safe_to_start_ec2), account_match=$($authSummary.account_match), failure_category=$($authSummary.failure_category)
- Profile matrix: $($profileSummary.result), matching profiles=$($profileSummary.profiles_matching_expected_count), expected account=$($profileSummary.expected_account)
- Lane readiness: $($laneSummary.result), lane_id=$($laneSummary.lane_id), lane_match=$($laneSummary.lane_match), local_pre_ec2_ready=$($laneSummary.local_pre_ec2_ready), ready_for_ec2_static_proof=$($laneSummary.ready_for_ec2_static_proof), ready_for_generation=$($laneSummary.ready_for_generation)
- Project readiness: $($projectSummary.result), lane_id=$($projectSummary.lane_id), lane_match=$($projectSummary.lane_match), local_ready=$($projectSummary.local_ready), ec2_start_allowed=$($projectSummary.ec2_start_allowed), generation_allowed=$($projectSummary.generation_allowed), scan_hit_count=$($projectSummary.scan_hit_count)
- Runtime lane queue: $($queueSummary.result), first_runtime_lane_id=$($queueSummary.first_runtime_lane_id), current_runtime_lane_id=$($queueSummary.current_runtime_lane_id), current_runtime_lane_match=$($queueSummary.current_runtime_lane_match), selected_lane_order=$($queueSummary.selected_lane_order), queue_allows_selected_lane_ec2_static_proof=$($queueSummary.queue_allows_selected_lane_ec2_static_proof)
- Model registry coverage: $($modelRegistryCoverageSummary.result), selected_lane_covered=$($modelRegistryCoverageSummary.selected_lane_covered), selected_lane_result=$($modelRegistryCoverageSummary.selected_lane_result), failed_check_count=$($modelRegistryCoverageSummary.failed_check_count), coverage_allows_selected_lane_ec2_static_proof=$($modelRegistryCoverageSummary.coverage_allows_selected_lane_ec2_static_proof)
- Workflow smoke: $($workflowSmokeSummary.result), run_id=$($workflowSmokeSummary.run_id), complete=$($workflowSmokeSummary.complete), final_state=$($workflowSmokeSummary.final_state), local_pullback_status=$($workflowSmokeSummary.local_pullback_status)
- Pullback record: $($pullbackSummary.status), hashes_verified=$($pullbackSummary.hashes_verified), complete=$($pullbackSummary.complete), file_count_remote=$($pullbackSummary.file_count_remote), file_count_local=$($pullbackSummary.file_count_local)
- Image QA technical: $($imageQaTechnicalSummary.qa_status), technical_integrity=$($imageQaTechnicalSummary.technical_integrity), resolution_check=$($imageQaTechnicalSummary.resolution_check), complete=$($imageQaTechnicalSummary.complete)
- Image QA visual: $($imageQaVisualSummary.result), qa_score=$($imageQaVisualSummary.qa_score), pass_threshold=$($imageQaVisualSummary.pass_threshold), complete=$($imageQaVisualSummary.complete)
- Run package: supplied=$($runPackageSummary.supplied), valid=$($runPackageSummary.valid), run_id=$($runPackageSummary.run_id), profile=$($runPackageSummary.prompt_profile.profile_id), prompt_hash_match=$($runPackageSummary.prompt_request.hash_match)

## Safety Invariants

- Start only EC2 instance $mdApprovedInstanceId.
- Expected AWS account is $mdExpectedAwsAccount.
- Do not start EC2 unless auth gate reports $mdAuthEc2Allowed and $mdAuthSafeToStart.
- Do not start EC2 unless runtime lane queue validation reports $mdCurrentRuntimeLane, selected lane in queue, and failed check count $mdFailedCheckZero.
- Do not start EC2 unless model registry coverage reports $mdCoverageResult, selected lane $mdCoverageLane result $mdCoveragePass, and failed check count $mdFailedCheckZero.
- Do not start EC2 unless local Git is clean and $mdHead equals $mdOriginMain.
- Do not run EC2 static proof unless lane readiness reports $mdLaneReadyId and $mdReadyForStaticProof.
- Do not run generation until object-info, checkpoint path, and checkpoint hash proof exists.
- Stop EC2 after runtime work and verify final state $mdStopped.
- If workflow smoke, pullback hashes, technical image QA, and visual image QA are complete for this lane, do not rerun EC2 for the same smoke proof; checkpoint evidence and advance.

## Command Sequence

$markdownCommands
## Runtime Boundary

This handoff was generated from local evidence only. It did not contact AWS, GitHub APIs, Civitai, ComfyUI, or EC2.
"@

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
$mdDir = Split-Path -Parent $MarkdownOutFile
if (![string]::IsNullOrWhiteSpace($mdDir)) {
  $null = New-Item -ItemType Directory -Force -Path $mdDir
}

$markdown | Set-Content -LiteralPath $MarkdownOutFile -Encoding UTF8
$record.markdown_written = (Test-Path -LiteralPath $MarkdownOutFile)
$record | ConvertTo-Json -Depth 30 | Set-Content -LiteralPath $OutFile -Encoding UTF8

Write-Host "Wrote runtime unblock handoff: $OutFile"
Write-Host "Wrote runtime unblock handoff markdown: $MarkdownOutFile"
$record | ConvertTo-Json -Depth 30
