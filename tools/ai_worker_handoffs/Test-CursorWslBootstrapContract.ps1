[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$wrapperPath = Join-Path $PSScriptRoot "cursor\Invoke-CursorAgentHandoff.ps1"
$wrapper = Get-Content -Raw -LiteralPath $wrapperPath
$checks = [ordered]@{
  bounded_bootstrap_retry_function = ($wrapper -match 'function Invoke-WslBootstrapWithRetry' -and $wrapper -match '\[ValidateRange\(1,5\)\]\[int\]\$MaxAttempts = 3')
  transient_createinstance_classification = ($wrapper -match 'CreateInstance\|E_FAIL\|Wsl/Service')
  exponential_backoff = ($wrapper -match 'Start-Sleep -Seconds \(\[math\]::Pow\(2, \$attempt\)\)')
  no_automatic_wsl_shutdown = ($wrapper -notmatch 'wsl(?:\.exe)?\s+--(?:shutdown|terminate)')
  attempts_recorded = ($wrapper -match 'wsl_bootstrap_attempt_count' -and $wrapper -match 'wsl_bootstrap_attempts')
  exact_failure_classification = ($wrapper -match 'CURSOR_WSL_BOOTSTRAP_FAILED')
}
$failed = @($checks.GetEnumerator() | Where-Object { -not $_.Value } | ForEach-Object { $_.Key })
[ordered]@{
  status = $(if ($failed.Count) { "FAIL" } else { "PASS" })
  classification = "CURSOR_WSL_BOOTSTRAP_RESILIENCE_CONTRACT"
  checks = $checks
  failed = $failed
} | ConvertTo-Json -Depth 5
if ($failed.Count) { exit 1 }
