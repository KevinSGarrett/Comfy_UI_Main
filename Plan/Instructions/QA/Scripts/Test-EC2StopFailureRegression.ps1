<#
.SYNOPSIS
Validates EC2 stop-failure classification and shutdown evidence contracts.

.DESCRIPTION
Runs local classifier cases and source-contract assertions only. It never calls
AWS, stops EC2, or runs ComfyUI.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
$classifier = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\EC2StopFailureClassification.ps1"
if (!(Test-Path -LiteralPath $classifier -PathType Leaf)) { throw "Classifier missing: $classifier" }
. $classifier

$cases = @(
  [ordered]@{ name = "success"; exit_code = 0; output = ""; expected = $null },
  [ordered]@{ name = "expired_auth"; exit_code = 255; output = "ExpiredToken"; expected = "aws_auth_or_authorization_failed" },
  [ordered]@{ name = "authorization"; exit_code = 254; output = "UnauthorizedOperation"; expected = "aws_auth_or_authorization_failed" },
  [ordered]@{ name = "throttle"; exit_code = 253; output = "RequestLimitExceeded"; expected = "ec2_stop_throttled" },
  [ordered]@{ name = "invalid_state"; exit_code = 252; output = "IncorrectInstanceState"; expected = "ec2_stop_invalid_instance_state" },
  [ordered]@{ name = "generic"; exit_code = 2; output = "unknown native failure"; expected = "ec2_stop_failed" }
)
$caseResults = foreach ($case in $cases) {
  $observed = Get-EC2StopFailureCategory -ExitCode $case.exit_code -OutputText $case.output
  $passed = if ($null -eq $case.expected) { $null -eq $observed } else { [string]$observed -eq [string]$case.expected }
  [ordered]@{
    name = $case.name
    expected = $case.expected
    observed = $observed
    result = $(if ($passed) { "pass" } else { "fail" })
  }
}

$specs = @(
  [ordered]@{ script = "Invoke-EC2LaneStaticProof.ps1"; exit_field = '$stopExitCode = $LASTEXITCODE'; classifier_call = 'Get-EC2StopFailureCategory -ExitCode $stopExitCode'; failure_field = '$stopFailureCategory'; evidence_guard = 'Stop/final-state verification failed:' },
  [ordered]@{ script = "Invoke-EC2WorkflowSmokeRun.ps1"; exit_field = '$record.stop_exit_code = $LASTEXITCODE'; classifier_call = 'Get-EC2StopFailureCategory -ExitCode $record.stop_exit_code'; failure_field = '$record.stop_failure_category'; evidence_guard = 'Stop/final-state verification failed:' },
  [ordered]@{ script = "Install-EC2ModelFromS3.ps1"; exit_field = '$record.stop_exit_code = $LASTEXITCODE'; classifier_call = 'Get-EC2StopFailureCategory -ExitCode $record.stop_exit_code'; failure_field = '$record.stop_failure_category'; evidence_guard = 'Stop/final-state verification failed:' },
  [ordered]@{ script = "Install-EC2InputAssetFromS3.ps1"; exit_field = '$record.stop_exit_code = $LASTEXITCODE'; classifier_call = 'Get-EC2StopFailureCategory -ExitCode $record.stop_exit_code'; failure_field = '$record.stop_failure_category'; evidence_guard = 'Stop/final-state verification failed:' },
  [ordered]@{ script = "Stop-ComfyUIGpuServer.ps1"; exit_field = '$stopExitCode = $LASTEXITCODE'; classifier_call = 'Get-EC2StopFailureCategory -ExitCode $stopExitCode'; failure_field = 'EC2 stop failed [$failureCategory]'; evidence_guard = 'exit 2' }
)

$sourceChecks = @()
foreach ($spec in $specs) {
  $path = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\$($spec.script)"
  if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw "Stop call site missing: $path" }
  $source = Get-Content -LiteralPath $path -Raw
  foreach ($literal in @(
    '$stopOutput = @(aws ec2 stop-instances',
    $spec.exit_field,
    $spec.classifier_call,
    $spec.failure_field,
    $spec.evidence_guard
  )) {
    $observed = $source.Contains($literal)
    $sourceChecks += [ordered]@{
      script = $spec.script
      contract = $literal
      required = $true
      observed = $observed
      result = $(if ($observed) { "pass" } else { "fail" })
    }
  }
  $discarded = [regex]::IsMatch($source, 'aws ec2 stop-instances[^\r\n]+\| Out-Null')
  $sourceChecks += [ordered]@{
    script = $spec.script
    contract = "discarded_stop_output_absent"
    required = $true
    observed = (-not $discarded)
    result = $(if (-not $discarded) { "pass" } else { "fail" })
  }
}

$watchdog = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Start-EC2InstanceStopWatchdog.ps1"
$watchdogSource = Get-Content -LiteralPath $watchdog -Raw
foreach ($literal in @("2>/tmp/codex_ec2_stop_watchdog_stop.err || {", "sudo shutdown -h now")) {
  $observed = $watchdogSource.Contains($literal)
  $sourceChecks += [ordered]@{
    script = "Start-EC2InstanceStopWatchdog.ps1"
    contract = $literal
    required = $true
    observed = $observed
    result = $(if ($observed) { "pass" } else { "fail" })
  }
}

$failures = @($caseResults | Where-Object result -ne "pass") + @($sourceChecks | Where-Object result -ne "pass")
$stamp = Get-Date -Format "yyyyMMddTHHmmss-0500"
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Operations_Static_Validation\W66_EC2_STOP_FAILURE_REGRESSION_$stamp.json"
}
$record = [ordered]@{
  evidence_id = "W66-EC2-STOP-FAILURE-REGRESSION-$stamp"
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  result = $(if ($failures.Count -eq 0) { "pass_local_only" } else { "fail" })
  local_only = $true
  aws_contacted = $false
  ec2_stop_requested = $false
  generation_executed = $false
  classifier_cases = $caseResults
  stop_source_contract_checks = $sourceChecks
  direct_stop_callsites = $specs.Count
  watchdog_contract_checked = $true
  failure_count = $failures.Count
  failures = @($failures)
  next_action = $(if ($failures.Count -eq 0) { "Use classified shutdown paths during the next intentionally gated live window." } else { "Repair failed stop classifier or source contracts before live EC2 work." })
}
$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) { $null = New-Item -ItemType Directory -Force -Path $outDir }
$record | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $OutFile -Encoding UTF8
$record | ConvertTo-Json -Depth 12
if ($failures.Count -gt 0) { exit 2 }
