[CmdletBinding()]
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [switch]$IncludeLiveProbes,
  [switch]$IncludeOpusProbe
)

$ErrorActionPreference = "Stop"
if ($IncludeOpusProbe -and -not $IncludeLiveProbes) { throw "-IncludeOpusProbe requires -IncludeLiveProbes." }
$wrapper = Join-Path $PSScriptRoot "Invoke-ClaudeSubscriptionHandoff.ps1"
$checks = [ordered]@{}
$checks.wrapper_exists = Test-Path -LiteralPath $wrapper
$checks.wrapper_parses = $false
$checks.wrapper_self_test = $false
$checks.claude_exe_exists = $false
$checks.subscription_auth = $false
$checks.api_env_absent = $true
$checks.exact_model_allowlist = $false
$checks.no_api_fallback_switch = $false
$checks.worktree_fingerprint_contract = $false
$checks.credential_scrub_contract = $false
$checks.opus_escalation_contract = $false
$checks.tool_surface_isolation_contract = $false
$checks.immutable_opus_ceiling_contract = $false
$checks.confidence_and_trigger_contract = $false
$checks.lock_queue_contract = $false
$checks.isolated_worktree_contract = $false
$checks.status_normalization_contract = $false
$checks.sonnet_probe_pass = $null
$checks.scope_packet_probe_pass = $null
$checks.opus_live_probe_pass = $null

function Invoke-BoundedProcess {
  param([string]$FilePath,[string]$Arguments,[int]$TimeoutSeconds=20)
  $psi=New-Object Diagnostics.ProcessStartInfo;$psi.FileName=$FilePath;$psi.Arguments=$Arguments;$psi.UseShellExecute=$false;$psi.CreateNoWindow=$true;$psi.RedirectStandardOutput=$true;$psi.RedirectStandardError=$true
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
    $selfTestProbe=Invoke-BoundedProcess -FilePath (Get-Command powershell.exe -ErrorAction Stop).Source -Arguments "-NoLogo -NoProfile -NonInteractive -File `"$wrapper`" -ProjectRoot `"$ProjectRoot`" -TaskName claude_wrapper_self_test -SelfTest" -TimeoutSeconds 20
    $selfTest=if(-not$selfTestProbe.timed_out-and$selfTestProbe.exit_code-eq0){([string]$selfTestProbe.stdout)|ConvertFrom-Json}else{[pscustomobject]@{status='FAIL';checks=[pscustomobject]@{}}}
    $checks.wrapper_self_test = ($selfTest.status -eq "PASS")
    $checks.wrapper_self_test_completed_in_time=(-not[bool]$selfTestProbe.timed_out)
    $source = Get-Content -LiteralPath $wrapper -Raw
    $checks.exact_model_allowlist = ($source -match 'ValidateSet\("claude-sonnet-5","claude-opus-4-8"\)' -and $source -notmatch 'ValidateSet\("sonnet"')
    $checks.no_api_fallback_switch = ($source -notmatch 'AllowApiEnvironmentFallback')
    $checks.worktree_fingerprint_contract = ($source -match 'worktree_fingerprint_before' -and $source -match 'CLAUDE_SUBSCRIPTION_READ_ONLY_MUTATION_VIOLATION' -and $source -match 'CLAUDE_CONCURRENT_WORKTREE_DRIFT_WARNING' -and $source -match 'scope_files_unchanged')
    $checks.credential_scrub_contract = ($source -match 'credential_environment_scrubbed' -and $source -match 'AWS_WEB_IDENTITY_TOKEN_FILE' -and $source -match 'GITHUB_ENTERPRISE_TOKEN' -and $source -match 'GIT_CONFIG_')
    $checks.opus_escalation_contract = ($source -match 'CLAUDE_OPUS_ESCALATION_NOT_JUSTIFIED' -and $source -match 'OpusDailyCeiling' -and $source -match 'ExpectedDecisionUnitId' -and $source -match 'claude_opus_global_usage_marker')
    $checks.tool_surface_isolation_contract = ($source -match '"--safe-mode"' -and $source -match '"--tools", "Read,Glob,Grep"' -and $source -match '"--strict-mcp-config"' -and $source -match '"--disable-slash-commands"' -and $source -match '"--no-chrome"' -and $source -notmatch '"--allowedTools"')
    $checks.immutable_opus_ceiling_contract = ($source -match '\$OpusDailyCeiling = 2' -and $source -notmatch '\[ValidateRange\(1,10\)\]\[int\]\$OpusDailyCeiling')
    $checks.confidence_and_trigger_contract = ($source -match 'worker_reported_confidence' -and $source -match 'Test-PriorSonnetEscalationTrigger' -and $source -match 'CLAUDE_SUBSCRIPTION_INVALID_CONFIDENCE_LABEL')
    $checks.lock_queue_contract = ($source -match 'Enter-BoundedHandoffLock' -and $source -match 'lock_wait_duration_ms' -and $source -match 'CLAUDE_SUBSCRIPTION_LOCK_WAIT_TIMEOUT')
    $checks.isolated_worktree_contract = ($source -match 'CLAUDE_ISOLATED_WORKTREE_REQUIRED' -and $source -match 'Get-RegisteredGitWorktreeRoots')
    $checks.status_normalization_contract = ($selfTest.checks.confirmed_status_normalized -and $selfTest.checks.findings_status_normalized -and $selfTest.checks.verified_blocked_status_normalized -and $selfTest.checks.compound_confidence_normalized)
  }
}

$claudeRoot = Join-Path $env:APPDATA "Claude\claude-code"
$claudeExe = Get-ChildItem -LiteralPath $claudeRoot -Directory -ErrorAction SilentlyContinue |
  Sort-Object Name -Descending |
  ForEach-Object { Join-Path $_.FullName "claude.exe" } |
  Where-Object { Test-Path -LiteralPath $_ } |
  Select-Object -First 1

$checks.claude_exe_exists = -not [string]::IsNullOrWhiteSpace($claudeExe)

foreach ($name in @("ANTHROPIC_API_KEY","ANTHROPIC_AUTH_TOKEN","ANTHROPIC_BASE_URL")) {
  foreach ($target in @("Process","User","Machine")) {
    $value = [Environment]::GetEnvironmentVariable($name, $target)
    if (-not [string]::IsNullOrWhiteSpace($value)) { $checks.api_env_absent = $false }
  }
}

if ($checks.claude_exe_exists) {
  $authProbe=Invoke-BoundedProcess -FilePath $claudeExe -Arguments 'auth status' -TimeoutSeconds 20
  if(-not$authProbe.timed_out-and$authProbe.exit_code-eq0){$auth=([string]$authProbe.stdout)|ConvertFrom-Json;$checks.subscription_auth=($auth.loggedIn-eq$true-and$auth.authMethod-eq'claude.ai'-and$auth.apiProvider-eq'firstParty');$checks.subscription_type=$auth.subscriptionType}
  $checks.auth_probe_completed_in_time=(-not[bool]$authProbe.timed_out)
}

if ($IncludeLiveProbes -and $checks.wrapper_exists -and $checks.claude_exe_exists -and $checks.subscription_auth -and $checks.api_env_absent) {
  $probe = & $wrapper -ProjectRoot $ProjectRoot -TaskName "claude_subscription_probe" -TaskTier HealthProbe -ClaudeModel claude-sonnet-5 -Effort low -TimeoutSeconds 180 -WorkOrderText "This is only a subscription transport and output-contract probe, not a project-readiness claim. Do not inspect project files. Return every required label. Set status to pass and include CLAUDE_SUBSCRIPTION_HANDOFF_READY only if you can complete this labeled response under the current subscription session; otherwise set status to blocked and explain honestly."
  $probeObj = $probe | ConvertFrom-Json
  $checks.sonnet_probe_pass = ($probeObj.status -eq "PASS" -and $probeObj.classification -eq "CLAUDE_HEALTH_PROBE_COMPLETED" -and $probeObj.result_excerpt -match "CLAUDE_SUBSCRIPTION_HANDOFF_READY")
  $checks.latest_probe_record = Join-Path $probeObj.run_dir "handoff_record.json"

  $packetTool = Join-Path $ProjectRoot "tools\New-AIWorkerScopePacket.ps1"
  if (Test-Path -LiteralPath $packetTool) {
    $packet = & $packetTool -ProjectRoot $ProjectRoot -TaskName "claude_scope_packet_probe" -Gate CLAUDE_SONNET_PRIMARY_REQUIRED -WorkerLane Claude -CandidatePaths @("CLAUDE.md") | ConvertFrom-Json
  $scopeProbe = & $wrapper -ProjectRoot $ProjectRoot -TaskName "claude_scope_packet_probe" -TaskTier SonnetPrimary -ClaudeModel claude-sonnet-5 -Effort medium -TimeoutSeconds 180 -ScopePacketPath $packet.output_path -AllowPrimaryWorktree -AllowDirectDiagnostic -WorkOrderText "The wrapper has already verified the scoped file's byte length and SHA-256; do not recompute either. Inspect only CLAUDE.md semantically. Set status to pass and include CLAUDE_SCOPE_PACKET_READY only if that exact file is readable and its content is consistent with a read-only Claude routing contract; otherwise set status to blocked and report the exact issue. Return every required label."
    $scopeProbeObj = $scopeProbe | ConvertFrom-Json
    $checks.scope_packet_probe_pass = ($scopeProbeObj.status -eq "PASS" -and $scopeProbeObj.classification -eq "CLAUDE_SONNET_HANDOFF_COMPLETED" -and $scopeProbeObj.scope_packet_validated -eq $true -and $scopeProbeObj.worktree_unchanged -eq $true -and $scopeProbeObj.result_excerpt -match "CLAUDE_SCOPE_PACKET_READY")
    $checks.latest_scope_probe_record = Join-Path $scopeProbeObj.run_dir "handoff_record.json"

    if ($IncludeOpusProbe) {
      $opusPacket = & $packetTool -ProjectRoot $ProjectRoot -TaskName "claude_opus_scope_probe" -Gate CLAUDE_OPUS_ESCALATION_REQUIRED -WorkerLane Claude -CandidatePaths @("CLAUDE.md") | ConvertFrom-Json
      $opusProbe = & $wrapper -ProjectRoot $ProjectRoot -TaskName "claude_opus_scope_probe" -TaskTier OpusEscalation -ClaudeModel claude-opus-4-8 -Effort high -TimeoutSeconds 300 -ScopePacketPath $opusPacket.output_path -DecisionUnitId "claude_opus_4_8_capability_probe" -EscalationReason DIRECT_HIGH_RISK_ARCHITECTURE_EXCEPTION -AllowDirectOpusArchitectureException -AllowPrimaryWorktree -AllowDirectDiagnostic -WorkOrderText "This is an explicit exact-model capability probe, not project certification. The wrapper has already verified the scoped file's byte length and SHA-256; do not recompute either. Inspect only CLAUDE.md semantically. Set status to pass and set escalation outcome to CLAUDE_OPUS_4_8_READY only if the file is readable and you can complete the required bounded labeled response; otherwise set status to blocked and explain honestly. Return every required label."
      $opusProbeObj = $opusProbe | ConvertFrom-Json
      $checks.opus_live_probe_pass = ($opusProbeObj.status -eq "PASS" -and $opusProbeObj.classification -eq "CLAUDE_OPUS_ESCALATION_COMPLETED" -and $opusProbeObj.requested_model -eq "claude-opus-4-8" -and $opusProbeObj.worktree_unchanged -eq $true -and $opusProbeObj.result_excerpt -match "CLAUDE_OPUS_4_8_READY")
      $checks.latest_opus_probe_record = Join-Path $opusProbeObj.run_dir "handoff_record.json"
    }
  }
}

$result = [ordered]@{
  status = if (($checks.Values | Where-Object { $_ -eq $false }).Count -eq 0) { "PASS" } else { "FAIL" }
  live_probes_requested = [bool]$IncludeLiveProbes
  opus_probe_requested = [bool]$IncludeOpusProbe
  checks = $checks
}
$result | ConvertTo-Json -Depth 8
