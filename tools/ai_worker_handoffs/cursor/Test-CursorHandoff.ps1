[CmdletBinding()]
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$CredentialRoot = "",
  [string]$WslDistribution = "Ubuntu-22.04",
  [switch]$IncludeCredentialLoadProbe,
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
$checks.guarded_agent_contract = $false
$checks.broad_scope_guard = $false
$checks.long_timeout_guard = $false
$checks.read_only_script_execution_guard = $false
$checks.fast_model_guard = $false
$checks.scope_lane_and_byte_contract = $false
$checks.status_parser_contract = $false
$checks.credential_scrub_contract = $false
$checks.primary_worktree_credential_contract = $false
$checks.concurrent_drift_contract = $false
$checks.credential_load_probe_pass = $null
$checks.credential_value_absent_from_record = $null
$checks.credential_probe_workspace_preserved = $null
$checks.probe_pass = $null

function Invoke-BoundedWslProbe {
  param([string]$Distribution,[string]$LinuxArguments,[int]$TimeoutSeconds=20)
  $psi=New-Object Diagnostics.ProcessStartInfo;$psi.FileName=(Get-Command wsl.exe -ErrorAction Stop).Source;$psi.Arguments="-d $Distribution --exec $LinuxArguments";$psi.UseShellExecute=$false;$psi.CreateNoWindow=$true;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true
  $process=New-Object Diagnostics.Process;$process.StartInfo=$psi;[void]$process.Start();$stdoutTask=$process.StandardOutput.ReadToEndAsync();$stderrTask=$process.StandardError.ReadToEndAsync();$timedOut=-not$process.WaitForExit($TimeoutSeconds*1000)
  if($timedOut){try{&taskkill.exe /PID $process.Id /T /F|Out-Null}catch{};try{[void]$process.WaitForExit(5000)}catch{}}else{$process.WaitForExit()}
  return [pscustomobject]@{exit_code=$(if($timedOut){-1}else{$process.ExitCode});timed_out=$timedOut;stdout=$stdoutTask.Result;stderr=$stderrTask.Result}
}

if ($checks.wrapper_exists) {
  $tokens = $null
  $parseErrors = $null
  [System.Management.Automation.Language.Parser]::ParseFile($wrapper, [ref]$tokens, [ref]$parseErrors) | Out-Null
  $checks.wrapper_parses = ($parseErrors.Count -eq 0)
  if ($checks.wrapper_parses) {
    $selfTest = & $wrapper -ProjectRoot $ProjectRoot -CredentialRoot $CredentialRoot -TaskName "wrapper_self_test" -SelfTest | ConvertFrom-Json
    $checks.wrapper_self_test = ($selfTest.status -eq "PASS")
    $source = Get-Content -LiteralPath $wrapper -Raw
    $checks.scope_lane_and_byte_contract = ($source -match 'scope_packet_worker_lane' -and $source -match 'scope_packet_total_bytes' -and $source -match 'MaxScopeBytes')
    $checks.status_parser_contract = ($source -match 'Get-WorkerReportedStatus' -and $source -match 'CURSOR_HANDOFF_WORKER_REPORTED_BLOCKED' -and $source -match 'CURSOR_HANDOFF_INVALID_STATUS_LABEL')
    $checks.credential_scrub_contract = ($source -match 'credential_environment_scrubbed' -and $source -match 'wslenv_forward_allowlist' -and $source -match '"CURSOR_API_KEY/u"')
    $checks.primary_worktree_credential_contract = (
      $source -match 'Resolve-CursorCredentialRoot' -and
      $source -match 'PRIMARY_WORKTREE_FOR_PROJECT' -and
      $source -match 'PRIMARY_WORKTREE_ENV_LOADER' -and
      $selfTest.checks.credential_primary_worktree_resolved -and
      $selfTest.checks.credential_project_root_remains_requested -and
      $selfTest.checks.credential_root_is_primary_worktree -and
      $selfTest.checks.untrusted_credential_root_rejected
    )
    $checks.concurrent_drift_contract = ($source -match 'Repository-visible state changed outside the hash-bound scope' -and $source -match 'scope_mutation_paths' -and $source -match 'warnings')
    $checks.guarded_agent_contract = ($source -match 'CURSOR_AGENT_SCOPE_REQUIRED' -and $source -match 'CURSOR_AGENT_COMMANDS_REQUIRED' -and $source -match 'outside allowed write scope')
    $checks.broad_scope_guard = ($source -match 'Broad worker discovery requires')
    $checks.long_timeout_guard = ($source -match 'TimeoutSeconds above 600')
    $checks.read_only_script_execution_guard = ($source -match 'Test-RequestsProjectExecution' -and $selfTest.checks.negated_execution_not_rejected -and $selfTest.checks.explicit_execution_detected -and $selfTest.checks.polite_execution_detected)
    $checks.fast_model_guard = ($source -match 'Fast Cursor models are prohibited' -and $source -match 'Only plain gpt-5.3-codex is allowed')
  }
}

$agentProbe=Invoke-BoundedWslProbe -Distribution $WslDistribution -LinuxArguments "$cursorAgentPath --version"
$checks.cursor_agent_installed = (-not$agentProbe.timed_out-and$agentProbe.exit_code-eq0-and-not[string]::IsNullOrWhiteSpace([string]$agentProbe.stdout))
$gitLfsProbe=Invoke-BoundedWslProbe -Distribution $WslDistribution -LinuxArguments 'git lfs version'
$checks.git_lfs_available = (-not$gitLfsProbe.timed_out-and$gitLfsProbe.exit_code-eq0-and([string]$gitLfsProbe.stdout).Trim()-match'(?i)^git-lfs/')
$checks.git_lfs_preflight_pass = $checks.git_lfs_available

if ($IncludeCredentialLoadProbe -and $checks.wrapper_exists -and $checks.wrapper_self_test) {
  $handoffRoot = Join-Path ([System.IO.Path]::GetFullPath($ProjectRoot)) "runtime_artifacts\agent_handoffs\cursor"
  $beforeProbeDirs = @(Get-ChildItem -LiteralPath $handoffRoot -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.FullName })
  $probeFailure = ""
  try {
    & $wrapper -ProjectRoot $ProjectRoot -CredentialRoot $CredentialRoot -TaskName "credential_root_guard_probe" -Mode agent -AllowPrimaryWorktree -WorkOrderText "Return a proposed summary only." | Out-Null
  } catch {
    $probeFailure = $_.Exception.Message
  }
  $newProbeDirs = @(Get-ChildItem -LiteralPath $handoffRoot -Directory -ErrorAction SilentlyContinue | Where-Object { $beforeProbeDirs -notcontains $_.FullName })
  if ($newProbeDirs.Count -eq 1) {
    $probeRunDir = $newProbeDirs[0].FullName
    try {
      $probeRecordPath = Join-Path $probeRunDir "handoff_record.json"
      $probeRecordRaw = Get-Content -LiteralPath $probeRecordPath -Raw
      $probeRecord = $probeRecordRaw | ConvertFrom-Json
      $cursorKey = [Environment]::GetEnvironmentVariable("CURSOR_API_KEY", "Process")
      $checks.credential_value_absent_from_record = (-not [string]::IsNullOrWhiteSpace($cursorKey) -and -not $probeRecordRaw.Contains($cursorKey))
      $checks.credential_probe_workspace_preserved = ([System.IO.Path]::GetFullPath([string]$probeRecord.project_root).TrimEnd('\') -eq [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\'))
      $checks.credential_load_probe_pass = (
        $probeFailure -match '^CURSOR_AGENT_SCOPE_REQUIRED:' -and
        [bool]$probeRecord.cursor_credential_available -and
        [string]$probeRecord.credential_root_relation -eq "PRIMARY_WORKTREE_FOR_PROJECT" -and
        [string]$probeRecord.classification -eq "CURSOR_AGENT_SCOPE_REQUIRED"
      )
    } finally {
      $resolvedProbeRunDir = [System.IO.Path]::GetFullPath($probeRunDir)
      $expectedProbePrefix = [System.IO.Path]::GetFullPath($handoffRoot).TrimEnd('\') + '\'
      if (-not $resolvedProbeRunDir.StartsWith($expectedProbePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove an unexpected credential probe path: $resolvedProbeRunDir"
      }
      Remove-Item -LiteralPath $resolvedProbeRunDir -Recurse -Force
    }
  } else {
    $checks.credential_load_probe_pass = $false
    $checks.credential_value_absent_from_record = $false
    $checks.credential_probe_workspace_preserved = $false
  }
}

if ($IncludeLiveProbe -and $checks.wrapper_exists -and $checks.wrapper_self_test -and $checks.cursor_agent_installed) {
    $resolvedCredentialRoot = [string]$selfTest.credential_root
    $envPath = Join-Path $resolvedCredentialRoot ".env"
    $checks.cursor_key_shape_equals = $false
    if (Test-Path -LiteralPath $envPath) {
      $cursorLine = Select-String -LiteralPath $envPath -Pattern '^\s*CURSOR_API_KEY\s*=' | Select-Object -First 1
      $checks.cursor_key_shape_equals = $null -ne $cursorLine
    }
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
    $envLoader = Join-Path $resolvedCredentialRoot "Plan\Instructions\Operations\Scripts\Load-ComfyEnv.ps1"
    $checks.cursor_key_loads = $false
    $checks.wsl_key_bridge = $false
    $checks.default_models_available = $false
    if (Test-Path -LiteralPath $envLoader) {
      . $envLoader -ProjectRoot $resolvedCredentialRoot -Quiet
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
    $probe = & $wrapper -ProjectRoot $ProjectRoot -CredentialRoot $CredentialRoot -TaskName "wrapper_transport_probe" -Mode ask -WslDistribution $WslDistribution -RequireGitLfs -TimeoutSeconds 120 -WorkOrderText "This is a transport-only probe. Do not inspect project files. Return exactly: status: pass; summary: CURSOR_HANDOFF_WRAPPER_READY; files inspected: none; blockers: none; confidence: high; recommended Codex follow-up: none."
    $probeObj = $probe | ConvertFrom-Json
    $checks.probe_pass = ($probeObj.status -eq "PASS" -and $probeObj.classification -eq "CURSOR_HANDOFF_COMPLETED" -and $probeObj.worker_reported_status -eq "pass" -and $probeObj.cursor_result_excerpt -match "CURSOR_HANDOFF_WRAPPER_READY")
    $checks.latest_probe_record = Join-Path $probeObj.run_dir "handoff_record.json"
    }
}

$result = [ordered]@{
  status = if (($checks.Values | Where-Object { $_ -eq $false }).Count -eq 0) { "PASS" } else { "FAIL" }
  credential_load_probe_requested = [bool]$IncludeCredentialLoadProbe
  live_probe_requested = [bool]$IncludeLiveProbe
  checks = $checks
  cursor_agent_version = ([string]$agentProbe.stdout).Trim()
  git_lfs_version = ([string]$gitLfsProbe.stdout).Trim()
}
$result | ConvertTo-Json -Depth 8
