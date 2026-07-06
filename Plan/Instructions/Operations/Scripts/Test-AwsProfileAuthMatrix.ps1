<#
.SYNOPSIS
Builds a secret-safe AWS profile authentication matrix.

.DESCRIPTION
This helper checks whether any locally configured AWS CLI profile can resolve
the expected AWS account through STS. It is read-only: it never starts EC2,
stops EC2, changes AWS resources, or prints credential values.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$ExpectedAccount = "029530099913",
  [string]$OutFile = "",
  [int]$TimeoutSeconds = 15
)

$ErrorActionPreference = "Stop"

function Redact-SecretText {
  param([string]$Text)

  if ([string]::IsNullOrWhiteSpace($Text)) { return "" }

  $redacted = $Text
  $redacted = $redacted -replace 'https://\S*signin\.aws\.amazon\.com/\S+', '[REDACTED_AWS_AUTH_URL]'
  $redacted = $redacted -replace 'https://\S*\.awsapps\.com/\S*', '[REDACTED_AWS_SSO_URL]'
  $redacted = $redacted -replace '(?<![A-Za-z0-9])(?:AKIA|ASIA)[0-9A-Z]{16}(?![A-Za-z0-9])', '[REDACTED_AWS_ACCESS_KEY_ID]'
  $redacted = $redacted -replace '(?<![A-Za-z0-9_])(?:ghp_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]{40,})(?![A-Za-z0-9_])', '[REDACTED_GITHUB_TOKEN]'
  $redacted = $redacted -replace '(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{32,}(?![A-Za-z0-9_-])', '[REDACTED_TOKEN]'
  $redacted = $redacted -replace '(?<![A-Za-z0-9_])hf_[A-Za-z0-9_-]{30,}(?![A-Za-z0-9_-])', '[REDACTED_HF_TOKEN]'
  $redacted = $redacted -replace 'AWS_SECRET_ACCESS_KEY\s*=\s*\S+', '[REDACTED_AWS_SECRET_ACCESS_KEY]'
  $redacted = $redacted -replace 'CIVITAI_(API_)?(TOKEN|KEY)\s*=\s*\S+', '[REDACTED_CIVITAI_TOKEN]'
  return $redacted
}

function Get-AuthFailureCategory {
  param([string]$Text)

  if ([string]::IsNullOrWhiteSpace($Text)) { return "unknown_failure" }
  if ($Text -match 'session has expired|ExpiredToken|RequestExpired|Please reauthenticate') { return "expired_session" }
  if ($Text -match 'SSO|sso|login') { return "sso_login_required" }
  if ($Text -match 'Unable to locate credentials|could not be found|No credentials|profile .* could not be found') { return "missing_credentials" }
  if ($Text -match 'AccessDenied|Unauthorized|not authorized') { return "unauthorized" }
  return "aws_cli_failure"
}

function Invoke-AwsCli {
  param(
    [string[]]$Arguments,
    [int]$TimeoutSecondsValue = 15
  )

  $processInfo = New-Object System.Diagnostics.ProcessStartInfo
  $processInfo.FileName = "aws"
  $processInfo.UseShellExecute = $false
  $processInfo.RedirectStandardOutput = $true
  $processInfo.RedirectStandardError = $true
  $processInfo.RedirectStandardInput = $true

  $quotedArgs = @()
  foreach ($argument in $Arguments) {
    if ($argument -match '[\s"]') {
      $quotedArgs += '"' + ($argument -replace '"', '\"') + '"'
    } else {
      $quotedArgs += $argument
    }
  }
  $processInfo.Arguments = ($quotedArgs -join " ")

  $process = New-Object System.Diagnostics.Process
  $process.StartInfo = $processInfo
  $null = $process.Start()
  $process.StandardInput.Close()
  $stdout = $process.StandardOutput.ReadToEnd()
  $stderr = $process.StandardError.ReadToEnd()
  if (-not $process.WaitForExit($TimeoutSecondsValue * 1000)) {
    try { $process.Kill() } catch {}
    $text = Redact-SecretText -Text (($stdout, $stderr, "Timed out waiting for aws command.") -join "`n")
    return [ordered]@{
      exit_code = 124
      output = $text.Trim()
    }
  }

  $text = Redact-SecretText -Text (($stdout, $stderr) -join "`n")
  return [ordered]@{
    exit_code = $process.ExitCode
    output = $text.Trim()
  }
}

function Get-SafeOutputTail {
  param([string]$Text)

  if ([string]::IsNullOrWhiteSpace($Text)) { return "" }
  $clean = Redact-SecretText -Text $Text
  if ($clean.Length -gt 500) {
    return $clean.Substring($clean.Length - 500)
  }
  return $clean
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$createdAt = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
$envLoader = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Load-ComfyEnv.ps1"

$record = [ordered]@{
  evidence_id = "AWS-PROFILE-AUTH-MATRIX-$stamp"
  timestamp = $createdAt
  project_root = $ProjectRoot
  expected_account = $ExpectedAccount
  env_loader_found = (Test-Path -LiteralPath $envLoader)
  aws_cli_found = [bool](Get-Command aws -ErrorAction SilentlyContinue)
  active_env_profile_name = $null
  profile_count = 0
  profiles_matching_expected_count = 0
  profiles_matching_expected = @()
  profile_results = @()
  ec2_work_allowed = $false
  safe_to_start_ec2 = $false
  generation_allowed = $false
  secrets_printed = $false
  auth_url_recorded = $false
  result = "blocked_no_valid_profile"
  next_action = ""
}

if ($record.env_loader_found) {
  . $envLoader -ProjectRoot $ProjectRoot -Quiet
}
$record.active_env_profile_name = $env:AWS_PROFILE

if (-not $record.aws_cli_found) {
  $record.result = "blocked_aws_cli_missing"
  $record.next_action = "Install or expose AWS CLI, then rerun the auth matrix before EC2 work."
} else {
  $profileCommand = Invoke-AwsCli -Arguments @("configure", "list-profiles") -TimeoutSecondsValue $TimeoutSeconds
  if ($profileCommand.exit_code -ne 0) {
    $record.result = "blocked_profile_list_failed"
    $record.next_action = "Fix AWS CLI profile discovery, then rerun the auth matrix before EC2 work."
      $profileDiscoveryOutput = Get-SafeOutputTail -Text ([string]$profileCommand.output)
      $record.profile_results += [ordered]@{
        profile = "[profile_discovery]"
        status = "failed"
        account_actual = $null
        account_match = $false
        failure_category = Get-AuthFailureCategory -Text ([string]$profileCommand.output)
        output_summary = $profileDiscoveryOutput
      }
  } else {
    $profiles = @(([string]$profileCommand.output -split "\r?\n") | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne "" } | Sort-Object -Unique)
    $record.profile_count = $profiles.Count

    foreach ($profile in $profiles) {
      $sts = Invoke-AwsCli -Arguments @("sts", "get-caller-identity", "--profile", $profile, "--query", "Account", "--output", "text") -TimeoutSecondsValue $TimeoutSeconds
      $output = ([string]$sts.output).Trim()
      $entry = [ordered]@{
        profile = $profile
        exit_code = $sts.exit_code
        status = "failed"
        account_actual = $null
        account_match = $false
        failure_category = $null
        output_summary = ""
      }

      if ($sts.exit_code -eq 0 -and $output -match '^\d{12}$') {
        $entry.status = "pass"
        $entry.account_match = ($output -eq $ExpectedAccount)
        $entry.account_actual = $(if ($entry.account_match) { $ExpectedAccount } else { "[OTHER_ACCOUNT]" })
        if ($entry.account_match) {
          $record.profiles_matching_expected += $profile
        } else {
          $entry.failure_category = "other_account"
        }
      } elseif ($sts.exit_code -eq 124) {
        $entry.failure_category = "timeout"
        $entry.output_summary = Get-SafeOutputTail -Text $output
      } else {
        $entry.failure_category = Get-AuthFailureCategory -Text $output
        $entry.output_summary = Get-SafeOutputTail -Text $output
      }

      if ($entry.output_summary -match 'https://') {
        $record.auth_url_recorded = $true
      }
      $record.profile_results += $entry
    }

    $record.profiles_matching_expected_count = @($record.profiles_matching_expected).Count
    if ($record.profiles_matching_expected_count -gt 0) {
      $record.ec2_work_allowed = $true
      $record.safe_to_start_ec2 = $true
      $record.generation_allowed = $true
      $record.result = "pass_profile_available"
      $record.next_action = "Set AWS_PROFILE to a matching profile, rerun Test-AwsAuthGate.ps1, then run selected-lane readiness before EC2 static proof."
    } else {
      $record.next_action = "Complete AWS browser/SSO login for the expected account, rerun Test-AwsAuthGate.ps1, then rerun selected-lane readiness before EC2 static proof."
    }
  }
}

if (![string]::IsNullOrWhiteSpace($OutFile)) {
  $outDir = Split-Path -Parent $OutFile
  if (![string]::IsNullOrWhiteSpace($outDir)) {
    $null = New-Item -ItemType Directory -Force -Path $outDir
  }
  $record | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $OutFile -Encoding UTF8
  Write-Host "Wrote AWS profile auth matrix record: $OutFile"
}

$record | ConvertTo-Json -Depth 20
if (-not $record.ec2_work_allowed) { exit 2 }
