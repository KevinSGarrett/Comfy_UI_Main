<#
.SYNOPSIS
Validates EC2 start-failure classification and workflow-smoke fail-fast wiring.

.DESCRIPTION
Runs local-only classifier cases and source-contract assertions. It never calls
AWS, starts EC2, or runs ComfyUI.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$classifier = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\EC2StartFailureClassification.ps1"
$workflowSmoke = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Invoke-EC2WorkflowSmokeRun.ps1"
$laneStaticProof = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Invoke-EC2LaneStaticProof.ps1"
$modelInstaller = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Install-EC2ModelFromS3.ps1"
$inputInstaller = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Install-EC2InputAssetFromS3.ps1"
$gpuStarter = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Start-ComfyUIGpuServer.ps1"
if (!(Test-Path -LiteralPath $classifier -PathType Leaf)) { throw "Classifier missing: $classifier" }
if (!(Test-Path -LiteralPath $workflowSmoke -PathType Leaf)) { throw "Workflow smoke helper missing: $workflowSmoke" }
if (!(Test-Path -LiteralPath $laneStaticProof -PathType Leaf)) { throw "Lane static proof helper missing: $laneStaticProof" }
foreach ($path in @($modelInstaller, $inputInstaller, $gpuStarter)) {
  if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw "EC2 start call site missing: $path" }
}
. $classifier

$cases = @(
  [ordered]@{ name = "success"; exit_code = 0; output = ""; expected = $null },
  [ordered]@{ name = "capacity"; exit_code = 255; output = "An error occurred (InsufficientInstanceCapacity)"; expected = "ec2_insufficient_instance_capacity" },
  [ordered]@{ name = "expired_auth"; exit_code = 255; output = "ExpiredToken: The security token included in the request is expired"; expected = "aws_auth_or_authorization_failed" },
  [ordered]@{ name = "authorization"; exit_code = 254; output = "UnauthorizedOperation: You are not authorized"; expected = "aws_auth_or_authorization_failed" },
  [ordered]@{ name = "throttle"; exit_code = 253; output = "RequestLimitExceeded"; expected = "ec2_start_throttled" },
  [ordered]@{ name = "generic"; exit_code = 2; output = "unknown native failure"; expected = "ec2_start_failed" }
)

$caseResults = @()
foreach ($case in $cases) {
  $observed = Get-EC2StartFailureCategory -ExitCode $case.exit_code -OutputText $case.output
  $passed = if ($null -eq $case.expected) { $null -eq $observed } else { [string]$observed -eq [string]$case.expected }
  $caseResults += [ordered]@{
    name = $case.name
    expected = $case.expected
    observed = $observed
    result = $(if ($passed) { "pass" } else { "fail" })
  }
}

$source = Get-Content -LiteralPath $workflowSmoke -Raw
$sourceChecks = @(
  [ordered]@{ name = "captures_start_output"; pattern = [regex]::Escape('$startOutput = @(aws ec2 start-instances'); required = $true },
  [ordered]@{ name = "captures_start_exit_code"; pattern = [regex]::Escape('$record.start_exit_code = $LASTEXITCODE'); required = $true },
  [ordered]@{ name = "uses_shared_classifier"; pattern = [regex]::Escape('Get-EC2StartFailureCategory -ExitCode $record.start_exit_code'); required = $true },
  [ordered]@{ name = "sets_started_only_after_success"; pattern = [regex]::Escape('$record.ec2_started = $true'); required = $true },
  [ordered]@{ name = "guards_stop_call"; pattern = [regex]::Escape('$shouldStopInstance ='); required = $true },
  [ordered]@{ name = "records_start_failed_result"; pattern = [regex]::Escape('workflow_smoke_start_failed'); required = $true }
  [ordered]@{ name = "execute_errors_cannot_remain_ready"; pattern = [regex]::Escape('workflow_smoke_preflight_or_start_failed'); required = $true }
)
foreach ($check in $sourceChecks) {
  $check.observed = [regex]::IsMatch($source, $check.pattern)
  $check.result = $(if ($check.observed -eq $check.required) { "pass" } else { "fail" })
}

$staticProofSource = Get-Content -LiteralPath $laneStaticProof -Raw
$staticProofSourceChecks = @(
  [ordered]@{ name = "guards_native_start_stderr"; pattern = '(?s)\$previousErrorActionPreference\s*=\s*\$ErrorActionPreference\s*\r?\n\s*\$ErrorActionPreference\s*=\s*"Continue"\s*\r?\n\s*try\s*\{\s*\r?\n\s*\$startOutput\s*=\s*@\(aws ec2 start-instances'; required = $true },
  [ordered]@{ name = "captures_static_start_exit_code"; pattern = [regex]::Escape('$startExitCode = $LASTEXITCODE'); required = $true },
  [ordered]@{ name = "restores_error_action_preference"; pattern = '(?s)\$startExitCode\s*=\s*\$LASTEXITCODE\s*\r?\n\s*\}\s*finally\s*\{\s*\r?\n\s*\$ErrorActionPreference\s*=\s*\$previousErrorActionPreference'; required = $true },
  [ordered]@{ name = "records_static_start_exit_code"; pattern = [regex]::Escape('start_exit_code = $startExitCode'); required = $true },
  [ordered]@{ name = "records_static_start_output_tail"; pattern = [regex]::Escape('start_output_tail = $startOutputTail'); required = $true },
  [ordered]@{ name = "uses_static_shared_classifier"; pattern = [regex]::Escape('Get-EC2StartFailureCategory -ExitCode $startExitCode'); required = $true }
)
foreach ($check in $staticProofSourceChecks) {
  $check.observed = [regex]::IsMatch($staticProofSource, $check.pattern)
  $check.result = $(if ($check.observed -eq $check.required) { "pass" } else { "fail" })
}

$siblingSourceChecks = @()
foreach ($spec in @(
  [ordered]@{ script = "Install-EC2ModelFromS3.ps1"; path = $modelInstaller; exit_field = '$record.start_exit_code = $LASTEXITCODE'; classifier_call = 'Get-EC2StartFailureCategory -ExitCode $record.start_exit_code'; failure_result = 'model_install_start_failed'; stop_guard = '$shouldStopInstance =' },
  [ordered]@{ script = "Install-EC2InputAssetFromS3.ps1"; path = $inputInstaller; exit_field = '$record.start_exit_code = $LASTEXITCODE'; classifier_call = 'Get-EC2StartFailureCategory -ExitCode $record.start_exit_code'; failure_result = 'input_asset_install_start_failed'; stop_guard = '$shouldStopInstance =' },
  [ordered]@{ script = "Start-ComfyUIGpuServer.ps1"; path = $gpuStarter; exit_field = '$startExitCode = $LASTEXITCODE'; classifier_call = 'Get-EC2StartFailureCategory -ExitCode $startExitCode'; failure_result = 'EC2 start failed [$failureCategory]'; stop_guard = 'exit 2' }
)) {
  $scriptSource = Get-Content -LiteralPath $spec.path -Raw
  foreach ($literal in @(
    '$startOutput = @(aws ec2 start-instances',
    $spec.exit_field,
    $spec.classifier_call,
    $spec.failure_result,
    $spec.stop_guard
  )) {
    $observed = $scriptSource.Contains($literal)
    $siblingSourceChecks += [ordered]@{
      script = $spec.script
      contract = $literal
      required = $true
      observed = $observed
      result = $(if ($observed) { "pass" } else { "fail" })
    }
  }
  $oldDiscardPatternPresent = [regex]::IsMatch($scriptSource, 'aws ec2 start-instances[^\r\n]+\| Out-Null')
  $siblingSourceChecks += [ordered]@{
    script = $spec.script
    contract = "discarded_start_output_absent"
    required = $true
    observed = (-not $oldDiscardPatternPresent)
    result = $(if (-not $oldDiscardPatternPresent) { "pass" } else { "fail" })
  }
}

$failures = @($caseResults | Where-Object result -ne "pass") + @($sourceChecks | Where-Object result -ne "pass") + @($staticProofSourceChecks | Where-Object result -ne "pass") + @($siblingSourceChecks | Where-Object result -ne "pass")
$stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_EC2_WORKFLOW_SMOKE_START_FAILURE_REGRESSION_$stamp.json"
}
$record = [ordered]@{
  evidence_id = "W66-EC2-WORKFLOW-SMOKE-START-FAILURE-REGRESSION-$stamp"
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  result = $(if ($failures.Count -eq 0) { "pass_local_only" } else { "fail" })
  local_only = $true
  aws_contacted = $false
  ec2_started = $false
  generation_executed = $false
  classifier_cases = $caseResults
  workflow_source_contract_checks = $sourceChecks
  static_proof_source_contract_checks = $staticProofSourceChecks
  sibling_source_contract_checks = $siblingSourceChecks
  failure_count = $failures.Count
  failures = @($failures)
  next_action = $(if ($failures.Count -eq 0) { "Use the hardened workflow-smoke helper in the next intentionally gated live window." } else { "Repair failed classifier or source-contract checks before live workflow smoke." })
}
$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) { $null = New-Item -ItemType Directory -Force -Path $outDir }
$record | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $OutFile -Encoding UTF8
$record | ConvertTo-Json -Depth 12
if ($failures.Count -gt 0) { exit 2 }
