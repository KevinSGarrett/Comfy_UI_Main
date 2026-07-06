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
  [string]$OutFile = "",
  [string]$MarkdownOutFile = ""
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

function Read-JsonEvidence {
  param([string]$Path)

  if ([string]::IsNullOrWhiteSpace($Path) -or !(Test-Path -LiteralPath $Path)) {
    return $null
  }
  return (Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json)
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

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")

$qaRoot = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence"
$runtimeReadinessDir = Join-Path $qaRoot "Runtime_Readiness"
$projectReadinessDir = Join-Path $qaRoot "Project_Readiness"
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
  lane_readiness = Find-LatestFile -Directory $runtimeReadinessDir -Filter "W61_LANE_RUNTIME_READINESS*.json"
  project_readiness = Find-LatestFile -Directory $projectReadinessDir -Filter "W61_PROJECT_READINESS_SNAPSHOT*.json"
  operations_validation = Find-LatestFile -Directory $operationsValidationDir -Filter "W60_OPERATIONS_HELPER_CURRENT_VALIDATION*.json"
  qa_validation = Find-LatestFile -Directory $qaValidationDir -Filter "W61_QA_HELPER_CURRENT_VALIDATION*.json"
  index_validation = Find-LatestFile -Directory $indexValidationDir -Filter "W59_LIVE_INDEX_REFRESH*.json"
}

$authJson = Read-JsonEvidence -Path $latest.auth_gate
$profileJson = Read-JsonEvidence -Path $latest.profile_matrix
$readinessJson = Read-JsonEvidence -Path $latest.lane_readiness
$projectJson = Read-JsonEvidence -Path $latest.project_readiness
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
  local_pre_ec2_ready = Get-BoolPropertyValue -Object $readinessJson -Name "local_pre_ec2_ready" -Default $false
  ready_for_ec2_static_proof = Get-BoolPropertyValue -Object $readinessJson -Name "ready_for_ec2_static_proof" -Default $false
  ready_for_generation = Get-BoolPropertyValue -Object $readinessJson -Name "ready_for_generation" -Default $false
}

$projectSummary = [ordered]@{
  evidence = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $latest.project_readiness
  result = [string](Get-PropertyValue -Object $projectJson -Name "result" -Default "missing_project_readiness")
  failure_category = Get-PropertyValue -Object $projectJson -Name "failure_category" -Default "missing_project_readiness"
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

$result = "handoff_failed_local_readiness"
$failureCategory = "local_project_readiness_failed"
$nextRequiredAction = "inspect_local_readiness_evidence"
if ($projectSummary.local_ready -and -not $authSummary.safe_to_start_ec2) {
  $result = "handoff_ready_runtime_blocked_auth"
  $failureCategory = $(if (![string]::IsNullOrWhiteSpace([string]$authSummary.failure_category)) { [string]$authSummary.failure_category } else { "aws_auth_blocked" })
  $nextRequiredAction = "complete_aws_browser_sso_login"
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
  (New-CommandStep -Name "lane_readiness_recheck" -Gate "auth_gate_safe_to_start_ec2_true" -Command "powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Test-LaneRuntimeReadiness.ps1 -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_<timestamp>.json" -ExpectedEvidence "local_pre_ec2_ready=true and ready_for_ec2_static_proof=true before EC2 static proof." -WhenToRun "Only after auth gate reports safe_to_start_ec2=true."),
  (New-CommandStep -Name "ec2_static_proof" -Gate "ready_for_ec2_static_proof_true" -Command "powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1 -Execute -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W61_EC2_LANE_STATIC_PROOF_<timestamp>.json" -ExpectedEvidence "Object-info node availability, checkpoint path, checkpoint size/hash, and EC2 stop verification." -WhenToRun "Only after readiness reports ready_for_ec2_static_proof=true."),
  (New-CommandStep -Name "bounded_workflow_smoke" -Gate "static_proof_generation_allowed" -Command "powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1 -Execute -StaticProofFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Static_Validation\W61_EC2_LANE_STATIC_PROOF_<timestamp>.json -ReadinessFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Runtime_Readiness\W61_LANE_RUNTIME_READINESS_<timestamp>.json -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Workflow_Runtime\W61_EC2_WORKFLOW_SMOKE_RUN_EXECUTION_<timestamp>.json" -ExpectedEvidence "Bounded prompt execution, remote artifact manifest, pullback route, and EC2 stop verification." -WhenToRun "Only after EC2 static proof permits generation."),
  (New-CommandStep -Name "artifact_pullback_record" -Gate "generated_artifacts_pulled_back" -Command "powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Operations\Scripts\New-EC2PullbackRecord.ps1 -RunId <run_id> -LocalDestination C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts\<run_id> -RemoteManifestFile C:\Comfy_UI_Main\Plan\Instructions\Operations\Pulled_Back_Artifacts\<run_id>\REMOTE_ARTIFACT_MANIFEST.json" -ExpectedEvidence "PULLBACK_RECORD.json with count/hash match and QA routing." -WhenToRun "After generated artifacts and remote manifest exist locally."),
  (New-CommandStep -Name "image_artifact_qa" -Gate "pullback_hashes_verified" -Command "powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\QA\Scripts\New-ImageArtifactQARecord.ps1 -ImagePath <pulled-back-image> -OutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W61_IMAGE_QA_<timestamp>.json -ChecklistOutFile C:\Comfy_UI_Main\Plan\Instructions\QA\Evidence\Image_Artifact_QA\W61_IMAGE_QA_CHECKLIST_<timestamp>.md" -ExpectedEvidence "Image technical QA record and human/visual review checklist." -WhenToRun "After pullback hashes are verified.")
)

$safetyInvariants = [ordered]@{
  approved_instance_id = "i-0560bf8d143f93bb1"
  expected_aws_account = "029530099913"
  expected_idle_state = "stopped"
  do_not_start_ec2_unless_auth_safe = "Test-AwsAuthGate.ps1 must report ec2_work_allowed=true and safe_to_start_ec2=true."
  do_not_start_ec2_unless_lane_ready = "Test-LaneRuntimeReadiness.ps1 must report ready_for_ec2_static_proof=true."
  do_not_run_generation_without_static_proof = "Invoke-EC2LaneStaticProof.ps1 -Execute must record object-info/path/hash proof before workflow smoke generation."
  stop_ec2_after_runtime_work = "Any EC2 runtime action must stop instance i-0560bf8d143f93bb1 and verify stopped."
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
  lane_id = "sdxl_low_risk_fallback_lane"
  result = $result
  failure_category = $failureCategory
  next_required_action = $nextRequiredAction
  latest_evidence = [ordered]@{
    auth_gate = $authSummary.evidence
    profile_matrix = $profileSummary.evidence
    lane_readiness = $laneSummary.evidence
    project_readiness = $projectSummary.evidence
    operations_validation = $helperSummary.operations_validation.evidence
    qa_validation = $helperSummary.qa_validation.evidence
    index_validation = $helperSummary.index_validation.evidence
  }
  gate_summary = [ordered]@{
    auth_gate = $authSummary
    profile_matrix = $profileSummary
    lane_readiness = $laneSummary
    project_readiness = $projectSummary
    helper_validation = $helperSummary
  }
  safety_invariants = $safetyInvariants
  command_sequence = $commandSequence
  markdown_path = $markdownPathForRecord
  markdown_written = $false
  known_issues = @(
    "This is a local handoff only and does not refresh AWS auth.",
    "AWS auth remains the runtime blocker if safe_to_start_ec2 is false.",
    "This handoff does not prove EC2 object-info/path/hash, generation, artifact pullback, or media QA."
  )
}

$markdownCommands = ($commandSequence | ForEach-Object {
  @"
### $($_.name)

Gate: $($_.gate)

```powershell
$($_.command)
```

Expected evidence: $($_.expected_evidence)

"@
}) -join "`n"

$markdown = @"
# Runtime Unblock Handoff

- created_at: $createdAt
- result: $result
- failure_category: $failureCategory
- next_required_action: $nextRequiredAction
- lane: sdxl_low_risk_fallback_lane
- local_only: true
- aws_contacted: false
- ec2_started: false
- generation_executed: false

## Current Gate Summary

- Auth gate: $($authSummary.result), safe_to_start_ec2=$($authSummary.safe_to_start_ec2), account_match=$($authSummary.account_match), failure_category=$($authSummary.failure_category)
- Profile matrix: $($profileSummary.result), matching profiles=$($profileSummary.profiles_matching_expected_count), expected account=$($profileSummary.expected_account)
- Lane readiness: $($laneSummary.result), local_pre_ec2_ready=$($laneSummary.local_pre_ec2_ready), ready_for_ec2_static_proof=$($laneSummary.ready_for_ec2_static_proof), ready_for_generation=$($laneSummary.ready_for_generation)
- Project readiness: $($projectSummary.result), local_ready=$($projectSummary.local_ready), ec2_start_allowed=$($projectSummary.ec2_start_allowed), generation_allowed=$($projectSummary.generation_allowed), scan_hit_count=$($projectSummary.scan_hit_count)

## Safety Invariants

- Start only EC2 instance `i-0560bf8d143f93bb1`.
- Expected AWS account is `029530099913`.
- Do not start EC2 unless auth gate reports `ec2_work_allowed=true` and `safe_to_start_ec2=true`.
- Do not run EC2 static proof unless lane readiness reports `ready_for_ec2_static_proof=true`.
- Do not run generation until object-info, checkpoint path, and checkpoint hash proof exists.
- Stop EC2 after runtime work and verify final state `stopped`.

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
