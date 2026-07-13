<#
.SYNOPSIS
Exercises the fail-closed Normal runtime-window intent contract.

.DESCRIPTION
Uses project-local fixture copies and child PowerShell processes. No network,
AWS, queue mutation, EC2 action, SSM command, or generation is performed.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$CandidateReadinessFile = "Plan\Instructions\QA\Evidence\Runtime_Readiness\W64_NORMAL_TARGET_RUNTIME_CANDIDATE_LOCAL_READINESS_20260713T103230-0500.json",
  [string]$RuntimeLaneQueueFile = "Plan\07_IMPLEMENTATION\workflow_templates\base_generation\runtime_lane_queue.json",
  [string]$TtlWatchdogEvidenceFile = "Plan\Instructions\QA\Evidence\Wave64\ec2_ttl_watchdog.json",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"

function Resolve-ProjectPath {
  param([Parameter(Mandatory=$true)][string]$Path)
  if ([System.IO.Path]::IsPathRooted($Path)) { return [System.IO.Path]::GetFullPath($Path) }
  return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Path))
}

function Write-JsonNoBom {
  param([Parameter(Mandatory=$true)][string]$Path, [Parameter(Mandatory=$true)][object]$Payload)
  [System.IO.File]::WriteAllText($Path, ($Payload | ConvertTo-Json -Depth 40) + [Environment]::NewLine, (New-Object System.Text.UTF8Encoding($false)))
}

function New-Fixture {
  param([Parameter(Mandatory=$true)][string]$Name)
  $dir = Join-Path $tempRoot $Name
  [System.IO.Directory]::CreateDirectory($dir) | Out-Null
  $candidate = Get-Content -LiteralPath $candidateSource -Raw | ConvertFrom-Json
  $queue = Get-Content -LiteralPath $queueSource -Raw | ConvertFrom-Json
  $ttl = Get-Content -LiteralPath $ttlSource -Raw | ConvertFrom-Json
  $candidatePath = Join-Path $dir "candidate.json"
  $queuePath = Join-Path $dir "queue.json"
  $ttlPath = Join-Path $dir "ttl.json"
  return [pscustomobject]@{
    directory = $dir
    candidate = $candidate
    queue = $queue
    ttl = $ttl
    candidate_path = $candidatePath
    queue_path = $queuePath
    ttl_path = $ttlPath
  }
}

function Invoke-Case {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [scriptblock]$Mutate,
    [Parameter(Mandatory=$true)][int]$ExpectedExitCode,
    [Parameter(Mandatory=$true)][bool]$ExpectedStructuralValid,
    [string]$ExpectedFailurePattern = "",
    [string]$RuntimeWindowId = "",
    [string]$ExpectedRuntimeWindowId = "",
    [bool]$ExpectedBindingValid = $true
  )
  $fixture = New-Fixture -Name $Name
  if ($null -ne $Mutate) { & $Mutate $fixture }
  Write-JsonNoBom -Path $fixture.candidate_path -Payload $fixture.candidate
  Write-JsonNoBom -Path $fixture.queue_path -Payload $fixture.queue
  Write-JsonNoBom -Path $fixture.ttl_path -Payload $fixture.ttl
  $childOut = Join-Path $fixture.directory "contract.json"
  $childArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $helper, "-ProjectRoot", $ProjectRoot, "-CandidateReadinessFile", $fixture.candidate_path, "-RuntimeLaneQueueFile", $fixture.queue_path, "-TtlWatchdogEvidenceFile", $fixture.ttl_path)
  if (![string]::IsNullOrWhiteSpace($RuntimeWindowId)) { $childArgs += @("-RuntimeWindowId", $RuntimeWindowId) }
  $childArgs += @("-OutFile", $childOut)
  & powershell @childArgs *> $null
  $exitCode = $LASTEXITCODE
  $payload = if (Test-Path -LiteralPath $childOut) { Get-Content -LiteralPath $childOut -Raw | ConvertFrom-Json } else { $null }
  $failureText = if ($null -ne $payload) { ([string]$payload.failure_category) + "`n" + (@($payload.errors) -join "`n") } else { "child_output_missing" }
  $boundaryPass = (
    $null -ne $payload -and [bool]$payload.local_only -and
    -not [bool]$payload.permissions.execute_allowed_now -and
    -not [bool]$payload.permissions.schedule_create_allowed_now -and
    -not [bool]$payload.permissions.ssm_watchdog_send_allowed_now -and
    -not [bool]$payload.permissions.ec2_start_allowed_now -and
    -not [bool]$payload.permissions.generation_allowed_now -and
    -not [bool]$payload.permissions.queue_mutation_allowed -and
    -not [bool]$payload.safety_boundary.aws_contacted -and
    -not [bool]$payload.safety_boundary.scheduler_mutated -and
    -not [bool]$payload.safety_boundary.ssm_command_sent -and
    -not [bool]$payload.safety_boundary.ec2_started_or_stopped -and
    -not [bool]$payload.safety_boundary.generation_executed -and
    -not [bool]$payload.safety_boundary.queue_mutated -and
    -not [bool]$payload.safety_boundary.git_mutated
  )
  $bindingShapeValid = (
    $null -ne $payload -and [string]$payload.runtime_window_id -cmatch '^rw-normal-[0-9]{8}T[0-9]{6}[+-][0-9]{4}-[0-9a-f]{8}$' -and
    [string]$payload.future_schedule_runtime_window_id -eq [string]$payload.runtime_window_id -and
    [string]$payload.future_watchdog_runtime_window_id -eq [string]$payload.runtime_window_id -and
    ([string]::IsNullOrWhiteSpace($ExpectedRuntimeWindowId) -or [string]$payload.runtime_window_id -ceq $ExpectedRuntimeWindowId)
  )
  $bindingPass = (
    $null -ne $payload -and $bindingShapeValid -eq $ExpectedBindingValid -and
    [string]$payload.tracker_id -eq "TRK-W64-042" -and [string]$payload.item_id -eq "ITEM-W64-042" -and
    [string]$payload.runtime_window_id_source -ceq $(if ([string]::IsNullOrWhiteSpace($RuntimeWindowId)) { "generated" } else { "caller_supplied" })
  )
  $failurePass = [string]::IsNullOrWhiteSpace($ExpectedFailurePattern) -or $failureText -match $ExpectedFailurePattern
  $passed = (
    $exitCode -eq $ExpectedExitCode -and $null -ne $payload -and
    [bool]$payload.structural_consistency_valid -eq $ExpectedStructuralValid -and
    -not [bool]$payload.contract_valid -and -not [bool]$payload.execution_authorized -and
    $boundaryPass -and $bindingPass -and $failurePass
  )
  return [pscustomobject][ordered]@{
    name = $Name
    result = $(if ($passed) { "pass" } else { "fail" })
    exit_code = $exitCode
    expected_exit_code = $ExpectedExitCode
    structural_consistency_valid = $(if ($null -ne $payload) { [bool]$payload.structural_consistency_valid } else { $null })
    expected_structural_consistency_valid = $ExpectedStructuralValid
    contract_valid = $(if ($null -ne $payload) { [bool]$payload.contract_valid } else { $null })
    runtime_window_id = $(if ($null -ne $payload) { [string]$payload.runtime_window_id } else { $null })
    failure_category = $(if ($null -ne $payload) { [string]$payload.failure_category } else { $null })
    exact_blockers = $(if ($null -ne $payload) { @($payload.exact_blockers) } else { @("child_output_missing") })
    errors = $(if ($null -ne $payload) { @($payload.errors) } else { @("child_output_missing") })
  }
}

$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$candidateSource = Resolve-ProjectPath -Path $CandidateReadinessFile
$queueSource = Resolve-ProjectPath -Path $RuntimeLaneQueueFile
$ttlSource = Resolve-ProjectPath -Path $TtlWatchdogEvidenceFile
$helper = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\New-NormalRuntimeWindowContract.ps1"
foreach ($required in @($candidateSource, $queueSource, $ttlSource, $helper)) {
  if (!(Test-Path -LiteralPath $required -PathType Leaf)) { throw "Required regression input missing: $required" }
}
$tempRoot = Join-Path $ProjectRoot ("runtime_artifacts\regression_temp\normal_runtime_window_{0}" -f ([guid]::NewGuid().ToString("N")))
[System.IO.Directory]::CreateDirectory($tempRoot) | Out-Null

$tests = @()
$tests += Invoke-Case -Name "current_state_valid_blocked_contract" -ExpectedExitCode 0 -ExpectedStructuralValid $true
$preservedRuntimeWindowId = "rw-normal-20260713T105243-0500-57f1f908"
$tests += Invoke-Case -Name "caller_supplied_runtime_window_id_preserved" -ExpectedExitCode 0 -ExpectedStructuralValid $true -RuntimeWindowId $preservedRuntimeWindowId -ExpectedRuntimeWindowId $preservedRuntimeWindowId
$tests += Invoke-Case -Name "invalid_caller_supplied_runtime_window_id_rejected" -ExpectedExitCode 2 -ExpectedStructuralValid $false -ExpectedFailurePattern "runtime_window_id_invalid" -RuntimeWindowId "rw-normal-invalid" -ExpectedBindingValid $false
$tests += Invoke-Case -Name "uppercase_caller_supplied_runtime_window_id_rejected" -ExpectedExitCode 2 -ExpectedStructuralValid $false -ExpectedFailurePattern "runtime_window_id_invalid" -RuntimeWindowId "rw-normal-20260713T105243-0500-57F1F908" -ExpectedBindingValid $false
$tests += Invoke-Case -Name "candidate_lane_mismatch" -ExpectedExitCode 2 -ExpectedStructuralValid $false -ExpectedFailurePattern "candidate_lane_mismatch" -Mutate { param($f) $f.candidate.lane_id = "wrong_lane" }
$tests += Invoke-Case -Name "candidate_case_mismatch" -ExpectedExitCode 2 -ExpectedStructuralValid $false -ExpectedFailurePattern "candidate_lane_mismatch" -Mutate { param($f) $f.candidate.lane_id = "SDXL_REALVISXL_CONTROLNET_NORMAL_LANE" }
$tests += Invoke-Case -Name "candidate_not_selected" -ExpectedExitCode 2 -ExpectedStructuralValid $false -ExpectedFailurePattern "candidate_not_selected_for_runtime_window" -Mutate { param($f) $f.candidate.candidate_selected_for_next_bounded_runtime_window = $false }
$tests += Invoke-Case -Name "queue_candidate_missing" -ExpectedExitCode 2 -ExpectedStructuralValid $false -ExpectedFailurePattern "contract_internal_consistency_failed" -Mutate { param($f) $f.queue.lanes = @($f.queue.lanes | Where-Object { [string]$_.lane_id -cne "sdxl_realvisxl_controlnet_normal_lane" }) }
$tests += Invoke-Case -Name "ttl_identity_mismatch" -ExpectedExitCode 2 -ExpectedStructuralValid $false -ExpectedFailurePattern "ttl_watchdog_tracker_item_mismatch" -Mutate { param($f) $f.ttl.tracker_id = "TRK-W64-999" }
$tests += Invoke-Case -Name "ttl_schedule_claim_not_missing" -ExpectedExitCode 2 -ExpectedStructuralValid $false -ExpectedFailurePattern "ttl_watchdog_binding_evidence_missing" -Mutate { param($f) $f.ttl.live_readiness.live_schedule_present = $true }
$tests += Invoke-Case -Name "forged_full_readiness_never_authorizes" -ExpectedExitCode 2 -ExpectedStructuralValid $false -ExpectedFailurePattern "ttl_watchdog_binding_evidence_missing" -Mutate {
  param($f)
  $f.queue.selection_policy.current_runtime_lane_id = "sdxl_realvisxl_controlnet_normal_lane"
  $f.queue.runtime_boundary.ec2_start_allowed_by_queue_file = $true
  $f.queue.runtime_boundary.generation_allowed_by_queue_file = $true
  $f.ttl.live_readiness.live_schedule_present = $true
  $f.ttl.live_readiness.watchdog_proof_present = $true
  $f.ttl.live_readiness.blockers = @()
}

foreach ($inputFailure in @(
  [pscustomobject]@{ name = "invalid_candidate_json"; mode = "invalid_json"; expected = "invalid_json" },
  [pscustomobject]@{ name = "missing_candidate_file"; mode = "missing"; expected = "missing_required_input" }
)) {
  $fixture = New-Fixture -Name $inputFailure.name
  Write-JsonNoBom -Path $fixture.queue_path -Payload $fixture.queue
  Write-JsonNoBom -Path $fixture.ttl_path -Payload $fixture.ttl
  if ($inputFailure.mode -eq "invalid_json") {
    [System.IO.File]::WriteAllText($fixture.candidate_path, "{ invalid json", (New-Object System.Text.UTF8Encoding($false)))
  } else {
    $fixture.candidate_path = Join-Path $fixture.directory "does_not_exist.json"
  }
  $failureOut = Join-Path $fixture.directory "contract.json"
  & powershell -NoProfile -ExecutionPolicy Bypass -File $helper -ProjectRoot $ProjectRoot -CandidateReadinessFile $fixture.candidate_path -RuntimeLaneQueueFile $fixture.queue_path -TtlWatchdogEvidenceFile $fixture.ttl_path -OutFile $failureOut *> $null
  $failureExit = $LASTEXITCODE
  $failurePayload = if (Test-Path -LiteralPath $failureOut) { Get-Content -LiteralPath $failureOut -Raw | ConvertFrom-Json } else { $null }
  $failurePass = (
    $failureExit -eq 2 -and $null -ne $failurePayload -and
    -not [bool]$failurePayload.structural_consistency_valid -and
    -not [bool]$failurePayload.contract_valid -and -not [bool]$failurePayload.execution_authorized -and
    [string]$failurePayload.failure_category -match [string]$inputFailure.expected -and
    -not [bool]$failurePayload.permissions.execute_allowed_now -and
    -not [bool]$failurePayload.permissions.schedule_create_allowed_now -and
    -not [bool]$failurePayload.permissions.ssm_watchdog_send_allowed_now -and
    -not [bool]$failurePayload.permissions.ec2_start_allowed_now -and
    -not [bool]$failurePayload.permissions.generation_allowed_now -and
    -not [bool]$failurePayload.permissions.queue_mutation_allowed -and
    -not [bool]$failurePayload.safety_boundary.aws_contacted -and
    -not [bool]$failurePayload.safety_boundary.scheduler_mutated -and
    -not [bool]$failurePayload.safety_boundary.ssm_command_sent -and
    -not [bool]$failurePayload.safety_boundary.ec2_started_or_stopped -and
    -not [bool]$failurePayload.safety_boundary.generation_executed -and
    -not [bool]$failurePayload.safety_boundary.queue_mutated -and
    -not [bool]$failurePayload.safety_boundary.git_mutated
  )
  $tests += [pscustomobject][ordered]@{
    name = $inputFailure.name
    result = $(if ($failurePass) { "pass" } else { "fail" })
    exit_code = $failureExit
    expected_exit_code = 2
    structural_consistency_valid = $(if ($null -ne $failurePayload) { [bool]$failurePayload.structural_consistency_valid } else { $null })
    expected_structural_consistency_valid = $false
    contract_valid = $(if ($null -ne $failurePayload) { [bool]$failurePayload.contract_valid } else { $null })
    runtime_window_id = $(if ($null -ne $failurePayload) { [string]$failurePayload.runtime_window_id } else { $null })
    failure_category = $(if ($null -ne $failurePayload) { [string]$failurePayload.failure_category } else { $null })
    exact_blockers = $(if ($null -ne $failurePayload) { @($failurePayload.exact_blockers) } else { @("child_output_missing") })
    errors = $(if ($null -ne $failurePayload) { @($failurePayload.errors) } else { @("child_output_missing") })
  }
}

$first = $tests[0]
$uniqueFixture = New-Fixture -Name "runtime_window_uniqueness_second"
Write-JsonNoBom $uniqueFixture.candidate_path $uniqueFixture.candidate
Write-JsonNoBom $uniqueFixture.queue_path $uniqueFixture.queue
Write-JsonNoBom $uniqueFixture.ttl_path $uniqueFixture.ttl
$uniqueOut = Join-Path $uniqueFixture.directory "contract.json"
& powershell -NoProfile -ExecutionPolicy Bypass -File $helper -ProjectRoot $ProjectRoot -CandidateReadinessFile $uniqueFixture.candidate_path -RuntimeLaneQueueFile $uniqueFixture.queue_path -TtlWatchdogEvidenceFile $uniqueFixture.ttl_path -OutFile $uniqueOut *> $null
$uniqueExit = $LASTEXITCODE
$uniquePayload = if (Test-Path -LiteralPath $uniqueOut) { Get-Content -LiteralPath $uniqueOut -Raw | ConvertFrom-Json } else { $null }
$uniquePass = (
  $uniqueExit -eq 0 -and $null -ne $uniquePayload -and [bool]$uniquePayload.structural_consistency_valid -and
  -not [bool]$uniquePayload.contract_valid -and -not [bool]$uniquePayload.execution_authorized -and
  [string]$uniquePayload.runtime_window_id -ne [string]$first.runtime_window_id
)
$tests += [pscustomobject][ordered]@{
  name = "runtime_window_id_unique"
  result = $(if ($uniquePass) { "pass" } else { "fail" })
  exit_code = $uniqueExit
  expected_exit_code = 0
  structural_consistency_valid = $(if ($null -ne $uniquePayload) { [bool]$uniquePayload.structural_consistency_valid } else { $null })
  expected_structural_consistency_valid = $true
  contract_valid = $(if ($null -ne $uniquePayload) { [bool]$uniquePayload.contract_valid } else { $null })
  runtime_window_id = $(if ($null -ne $uniquePayload) { [string]$uniquePayload.runtime_window_id } else { $null })
  failure_category = $(if ($null -ne $uniquePayload) { [string]$uniquePayload.failure_category } else { $null })
  exact_blockers = $(if ($null -ne $uniquePayload) { @($uniquePayload.exact_blockers) } else { @("child_output_missing") })
  errors = $(if ($null -ne $uniquePayload) { @($uniquePayload.errors) } else { @("child_output_missing") })
}

$failed = @($tests | Where-Object { [string]$_.result -ne "pass" })
$record = [ordered]@{
  schema_version = "1.0"
  artifact_type = "normal_runtime_window_contract_regression"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  result = $(if ($failed.Count -eq 0) { "pass_local_only" } else { "fail" })
  local_only = $true
  aws_contacted = $false
  scheduler_mutated = $false
  ssm_command_sent = $false
  ec2_started_or_stopped = $false
  generation_executed = $false
  queue_mutated = $false
  git_mutated = $false
  test_count = $tests.Count
  passing_test_count = @($tests | Where-Object { [string]$_.result -eq "pass" }).Count
  failed_test_count = $failed.Count
  tests = $tests
}
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
  $OutFile = "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W64_NORMAL_RUNTIME_WINDOW_CONTRACT_REGRESSION_$stamp.json"
}
$outPath = Resolve-ProjectPath -Path $OutFile
[System.IO.Directory]::CreateDirectory((Split-Path -Parent $outPath)) | Out-Null
Write-JsonNoBom -Path $outPath -Payload $record

$tempBase = [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot "runtime_artifacts\regression_temp")).TrimEnd("\") + "\"
$tempResolved = [System.IO.Path]::GetFullPath($tempRoot)
if ($tempResolved.StartsWith($tempBase, [System.StringComparison]::OrdinalIgnoreCase)) {
  Remove-Item -LiteralPath $tempResolved -Recurse -Force
}

$record | ConvertTo-Json -Depth 30
if ($failed.Count -gt 0) { exit 1 }
exit 0
