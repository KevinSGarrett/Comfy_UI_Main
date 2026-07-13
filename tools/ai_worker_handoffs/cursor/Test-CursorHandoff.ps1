[CmdletBinding()]
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$WslDistribution = "Ubuntu-22.04",
  [switch]$IncludeLiveProbe
)
$ErrorActionPreference = "Stop"
$wrapper = Join-Path $PSScriptRoot "Invoke-CursorAgentHandoff.ps1"
$cursorAgentPath = "/home/kevin/.local/bin/cursor-agent"
$checks = [ordered]@{}
$checks.wrapper_exists = Test-Path -LiteralPath $wrapper
$checks.wrapper_parses = $false
$checks.wrapper_self_test = $false
$checks.cursor_agent_installed = $false
$checks.git_lfs_available = $false
$checks.git_lfs_preflight_pass = $false
$checks.default_models_available = $null
$checks.cursor_key_shape_equals = $null
$checks.cursor_key_loads = $null
$checks.wsl_key_bridge = $null
$checks.agent_write_guard = $false
$checks.broad_scope_guard = $false
$checks.long_timeout_guard = $false
$checks.read_only_script_execution_guard = $false
$checks.fast_model_guard = $false
$checks.scope_lane_and_byte_contract = $false
$checks.status_parser_contract = $false
$checks.credential_scrub_contract = $false
$checks.concurrent_drift_contract = $false
$checks.probe_pass = $null

if ($checks.wrapper_exists) {
  $tokens = $null
  $parseErrors = $null
  [System.Management.Automation.Language.Parser]::ParseFile($wrapper, [ref]$tokens, [ref]$parseErrors) | Out-Null
  $checks.wrapper_parses = ($parseErrors.Count -eq 0)
  if ($checks.wrapper_parses) {
    $selfTest = & $wrapper -TaskName "wrapper_self_test" -SelfTest | ConvertFrom-Json
    $checks.wrapper_self_test = ($selfTest.status -eq "PASS")
    $source = Get-Content -LiteralPath $wrapper -Raw
    $checks.scope_lane_and_byte_contract = ($source -match 'scope_packet_worker_lane' -and $source -match 'scope_packet_total_bytes' -and $source -match 'MaxScopeBytes')
    $checks.status_parser_contract = ($source -match 'Get-WorkerReportedStatus' -and $source -match 'CURSOR_HANDOFF_WORKER_REPORTED_BLOCKED' -and $source -match 'CURSOR_HANDOFF_INVALID_STATUS_LABEL')
    $checks.credential_scrub_contract = ($source -match 'credential_environment_scrubbed' -and $source -match 'wslenv_forward_allowlist' -and $source -match '"CURSOR_API_KEY/u"')
    $checks.concurrent_drift_contract = ($source -match 'CURSOR_CONCURRENT_WORKTREE_DRIFT_DETECTED' -and $source -match 'scope_mutation_paths')
    $checks.agent_write_guard = ($source -match 'CURSOR_MUTATION_MODE_DISABLED')
    $checks.broad_scope_guard = ($source -match 'Broad worker discovery requires')
    $checks.long_timeout_guard = ($source -match 'TimeoutSeconds above 600')
    $checks.read_only_script_execution_guard = ($source -match 'may not execute project scripts')
    $checks.fast_model_guard = ($source -match 'Fast Cursor models are prohibited' -and $source -match 'Only plain gpt-5.3-codex is allowed')
  }
}

$agentVersion = wsl.exe -d $WslDistribution -- bash -lc "$cursorAgentPath --version 2>/dev/null || true"
$checks.cursor_agent_installed = -not [string]::IsNullOrWhiteSpace(($agentVersion | Out-String).Trim())
$gitLfsVersion = wsl.exe -d $WslDistribution -- git lfs version 2>&1
$checks.git_lfs_available = ($LASTEXITCODE -eq 0 -and (($gitLfsVersion | Out-String).Trim() -match '(?i)^git-lfs/'))
$checks.git_lfs_preflight_pass = $checks.git_lfs_available

if ($IncludeLiveProbe -and $checks.wrapper_exists -and $checks.cursor_agent_installed) {
    $envPath = Join-Path $ProjectRoot ".env"
    $checks.cursor_key_shape_equals = $false
    if (Test-Path -LiteralPath $envPath) {
      $cursorLine = Select-String -LiteralPath $envPath -Pattern '^\s*CURSOR_API_KEY\s*=' | Select-Object -First 1
      $checks.cursor_key_shape_equals = $null -ne $cursorLine
    }
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
    $envLoader = Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Load-ComfyEnv.ps1"
    $checks.cursor_key_loads = $false
    $checks.wsl_key_bridge = $false
    $checks.default_models_available = $false
    if (Test-Path -LiteralPath $envLoader) {
      . $envLoader -ProjectRoot $ProjectRoot -Quiet
      $v = [Environment]::GetEnvironmentVariable("CURSOR_API_KEY", "Process")
      $checks.cursor_key_loads = -not [string]::IsNullOrWhiteSpace($v)
      $priorWslenv = [Environment]::GetEnvironmentVariable("WSLENV", "Process")
      try {
        [Environment]::SetEnvironmentVariable("WSLENV", "CURSOR_API_KEY/u", "Process")
        $bridge = wsl.exe -d $WslDistribution -- python3 -c "import os; v=os.environ.get('CURSOR_API_KEY'); print('yes' if v else 'no')"
        $checks.wsl_key_bridge = (($bridge | Out-String).Trim() -eq "yes")
      } finally {
        [Environment]::SetEnvironmentVariable("WSLENV", $priorWslenv, "Process")
      }
      if ($checks.wsl_key_bridge) {
        $models = wsl.exe -d $WslDistribution -- bash -lc "$cursorAgentPath models 2>/dev/null || true"
        $modelsText = ($models | Out-String)
        $modelLines = @($modelsText -split "\r?\n" | ForEach-Object { $_.Trim() })
        $checks.default_models_available = (($modelLines | Where-Object { $_ -like "gpt-5.3-codex *" }).Count -gt 0)
      }
    }
    if ($checks.cursor_key_loads -and $checks.wsl_key_bridge) {
    $probe = & $wrapper -ProjectRoot $ProjectRoot -TaskName "wrapper_transport_probe" -Mode ask -WslDistribution $WslDistribution -RequireGitLfs -TimeoutSeconds 120 -WorkOrderText "This is a transport-only probe. Do not inspect project files. Return exactly: status: pass; summary: CURSOR_HANDOFF_WRAPPER_READY; files inspected: none; blockers: none; confidence: high; recommended Codex follow-up: none."
    $probeObj = $probe | ConvertFrom-Json
    $checks.probe_pass = ($probeObj.status -eq "PASS" -and $probeObj.classification -eq "CURSOR_HANDOFF_COMPLETED" -and $probeObj.worker_reported_status -eq "pass" -and $probeObj.cursor_result_excerpt -match "CURSOR_HANDOFF_WRAPPER_READY")
    $checks.latest_probe_record = Join-Path $probeObj.run_dir "handoff_record.json"
    }
}

$result = [ordered]@{
  status = if (($checks.Values | Where-Object { $_ -eq $false }).Count -eq 0) { "PASS" } else { "FAIL" }
  live_probe_requested = [bool]$IncludeLiveProbe
  checks = $checks
  cursor_agent_version = (($agentVersion | Out-String).Trim())
  git_lfs_version = (($gitLfsVersion | Out-String).Trim())
}
$result | ConvertTo-Json -Depth 8
