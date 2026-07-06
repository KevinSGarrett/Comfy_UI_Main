<#
.SYNOPSIS
Checks whether AWS authentication is valid enough to permit EC2 work.

.DESCRIPTION
This helper is intentionally secret-safe. It loads .env into the current
process, checks the active AWS account, optionally attempts the remote browser
login flow, redacts any authorization URL from captured output, and writes a
machine-readable gate record. It never starts, stops, or modifies EC2.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$ExpectedAccount = "029530099913",
  [string]$OutFile = "",
  [switch]$AttemptRemoteLogin
)

$ErrorActionPreference = "Stop"

function Redact-SecretText {
  param([string]$Text)

  if ([string]::IsNullOrWhiteSpace($Text)) { return "" }

  $redacted = $Text
  $redacted = $redacted -replace 'https://\S*signin\.aws\.amazon\.com/\S+', '[REDACTED_AWS_AUTH_URL]'
  $redacted = $redacted -replace '(?<![A-Za-z0-9])(?:AKIA|ASIA)[0-9A-Z]{16}(?![A-Za-z0-9])', '[REDACTED_AWS_ACCESS_KEY_ID]'
  $redacted = $redacted -replace '(?<![A-Za-z0-9_])(?:ghp_[A-Za-z0-9_]{30,}|github_pat_[A-Za-z0-9_]{40,})(?![A-Za-z0-9_])', '[REDACTED_GITHUB_TOKEN]'
  $redacted = $redacted -replace '(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{32,}(?![A-Za-z0-9_-])', '[REDACTED_TOKEN]'
  $redacted = $redacted -replace '(?<![A-Za-z0-9_])hf_[A-Za-z0-9_-]{30,}(?![A-Za-z0-9_-])', '[REDACTED_HF_TOKEN]'
  $redacted = $redacted -replace 'AWS_SECRET_ACCESS_KEY\s*=\s*\S+', '[REDACTED_AWS_SECRET_ACCESS_KEY]'
  $redacted = $redacted -replace 'CIVITAI_(API_)?(TOKEN|KEY)\s*=\s*\S+', '[REDACTED_CIVITAI_TOKEN]'
  return $redacted
}

function Join-CommandOutput {
  param([object[]]$Output)

  if ($null -eq $Output) { return "" }
  return (($Output | ForEach-Object { $_.ToString() }) -join "`n").Trim()
}

function Invoke-AwsCli {
  param([string[]]$Arguments)

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
  if (-not $process.WaitForExit(120000)) {
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

function Get-AuthFailureCategory {
  param([string]$Text)

  if ([string]::IsNullOrWhiteSpace($Text)) { return "unknown_failure" }
  if ($Text -match 'session has expired|ExpiredToken|RequestExpired') { return "expired_session" }
  if ($Text -match 'Unable to locate credentials|could not be found|No credentials') { return "missing_credentials" }
  if ($Text -match 'AccessDenied|Unauthorized|not authorized') { return "unauthorized" }
  if ($Text -match 'EOF when reading a line') { return "noninteractive_authorization_code_missing" }
  return "aws_cli_failure"
}

function Convert-StsResult {
  param(
    [System.Collections.Specialized.OrderedDictionary]$CommandResult,
    [string]$ExpectedAccountValue
  )

  $account = $null
  $accountMatch = $false
  $category = $null
  $status = "failed"

  if ($CommandResult.exit_code -eq 0) {
    $candidate = ([string]$CommandResult.output).Trim()
    if ($candidate -match '^\d{12}$') {
      $account = $candidate
      $accountMatch = ($account -eq $ExpectedAccountValue)
      $status = $(if ($accountMatch) { "pass" } else { "account_mismatch" })
      if (-not $accountMatch) { $category = "account_mismatch" }
    } else {
      $category = "unexpected_sts_output"
    }
  } else {
    $category = Get-AuthFailureCategory -Text ([string]$CommandResult.output)
  }

  return [ordered]@{
    attempted = $true
    exit_code = $CommandResult.exit_code
    status = $status
    account_actual = $account
    account_expected = $ExpectedAccountValue
    account_match = $accountMatch
    failure_category = $category
    output_summary = $CommandResult.output
  }
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
$envLoader = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Load-ComfyEnv.ps1"

$record = [ordered]@{
  evidence_id = "AWS-AUTH-GATE-" + $stamp
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  project_root = $ProjectRoot
  expected_account = $ExpectedAccount
  env_loader_found = (Test-Path -LiteralPath $envLoader)
  aws_cli_found = [bool](Get-Command aws -ErrorAction SilentlyContinue)
  sts_before = $null
  remote_login = [ordered]@{
    attempted = $false
    status = "not_attempted"
  }
  sts_after = $null
  result = "not_evaluated"
  failure_category = $null
  account_actual = $null
  account_match = $false
  remote_login_status = "not_attempted"
  ec2_work_allowed = $false
  safe_to_start_ec2 = $false
  generation_allowed = $false
  secrets_printed = $false
  auth_url_recorded = $false
  next_action = ""
}

if ($record.env_loader_found) {
  . $envLoader -ProjectRoot $ProjectRoot -Quiet
}

if (-not $record.aws_cli_found) {
  $record.next_action = "Install or expose AWS CLI, then rerun this auth gate before EC2 work."
} else {
  $record.sts_before = Convert-StsResult -CommandResult (Invoke-AwsCli -Arguments @("sts", "get-caller-identity", "--query", "Account", "--output", "text")) -ExpectedAccountValue $ExpectedAccount

  if ([bool]$record.sts_before.account_match) {
    $record.ec2_work_allowed = $true
    $record.safe_to_start_ec2 = $true
    $record.generation_allowed = $true
    $record.next_action = "AWS auth is valid; run EC2 static lane proof before any generation."
  } elseif ($AttemptRemoteLogin) {
    $loginResult = Invoke-AwsCli -Arguments @("login", "--remote")
    $loginText = [string]$loginResult.output
    $record.remote_login = [ordered]@{
      attempted = $true
      exit_code = $loginResult.exit_code
      status = $(if ($loginResult.exit_code -eq 0) { "completed" } elseif ($loginText -match "EOF when reading a line") { "external_authorization_required_noninteractive" } else { "failed" })
      browser_authorization_required = ($loginText -match "\[REDACTED_AWS_AUTH_URL\]" -or $loginText -match "Enter the authorization code")
      authorization_code_prompted = ($loginText -match "Enter the authorization code")
      noninteractive_eof = ($loginText -match "EOF when reading a line")
      output_summary = $loginText
    }
    $record.sts_after = Convert-StsResult -CommandResult (Invoke-AwsCli -Arguments @("sts", "get-caller-identity", "--query", "Account", "--output", "text")) -ExpectedAccountValue $ExpectedAccount
    if ([bool]$record.sts_after.account_match) {
      $record.ec2_work_allowed = $true
      $record.safe_to_start_ec2 = $true
      $record.generation_allowed = $true
      $record.next_action = "AWS auth is valid after remote login; run EC2 static lane proof before any generation."
    } else {
      $record.next_action = "Complete aws login --remote in a browser-capable interactive shell, verify account 029530099913, then rerun this auth gate."
    }
  } else {
    $record.next_action = "Run with -AttemptRemoteLogin or complete aws login --remote, then verify account 029530099913 before EC2 work."
  }
}

$latestSts = $record.sts_before
if ($null -ne $record.sts_after) {
  $latestSts = $record.sts_after
}

if ($null -ne $latestSts) {
  $record.account_actual = $latestSts.account_actual
  $record.account_match = [bool]$latestSts.account_match
}

$record.remote_login_status = [string]$record.remote_login.status

if ([bool]$record.ec2_work_allowed -and [bool]$record.safe_to_start_ec2) {
  $record.result = "pass"
  $record.failure_category = $null
} else {
  if ($null -ne $latestSts -and ![string]::IsNullOrWhiteSpace([string]$latestSts.failure_category)) {
    $record.failure_category = [string]$latestSts.failure_category
  } elseif (-not $record.aws_cli_found) {
    $record.failure_category = "aws_cli_missing"
  } else {
    $record.failure_category = "unknown_failure"
  }
  $record.result = "blocked_$($record.failure_category)"
}

if (![string]::IsNullOrWhiteSpace($OutFile)) {
  $outDir = Split-Path -Parent $OutFile
  if (![string]::IsNullOrWhiteSpace($outDir)) {
    $null = New-Item -ItemType Directory -Force -Path $outDir
  }
  $record | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $OutFile -Encoding UTF8
  Write-Host "Wrote AWS auth gate record: $OutFile"
}

$record | ConvertTo-Json -Depth 20
if (-not $record.ec2_work_allowed) { exit 2 }
