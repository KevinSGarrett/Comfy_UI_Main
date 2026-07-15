<#
.SYNOPSIS
Runs a bounded Claude Code subscription handoff for Comfy_UI_Main.
#>
[CmdletBinding(PositionalBinding=$false)]
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [Parameter(Mandatory=$true)][string]$TaskName,
  [string]$WorkOrderText = "",
  [string]$WorkOrderPath = "",
  [string]$ScopePacketPath = "",
  [ValidateSet("HealthProbe","SonnetPrimary","OpusEscalation")][string]$TaskTier = "SonnetPrimary",
  [ValidateSet("claude-sonnet-5","claude-opus-4-8")][string]$ClaudeModel = "claude-sonnet-5",
  [ValidateSet("low","medium","high","xhigh","max")][string]$Effort = "medium",
  [ValidateSet("plan","manual")][string]$PermissionMode = "plan",
  [ValidateRange(30,1800)][int]$TimeoutSeconds = 1200,
  [int]$StaleLockMinutes = 120,
  [ValidateRange(0,1800)][int]$LockWaitSeconds = 600,
  [ValidateRange(1,30)][int]$LockPollSeconds = 2,
  [string]$ClaudeExe = "",
  [switch]$AllowBroadDiscovery,
  [string]$BroadDiscoveryReason = "",
  [ValidateRange(65536,2097152)][long]$MaxScopeBytes = 524288,
  [string]$ScopeByteBudgetReason = "",
  [ValidateSet("","SONNET_BLOCKED_OR_LOW_CONFIDENCE","HIGH_SEVERITY_UNRESOLVED_AFTER_REMEDIATION","CROSS_SYSTEM_ARCHITECTURE","MATERIAL_AUTHORITY_CONTRADICTION","LONG_FORM_ARCHITECTURE_OVER_15_MINUTES","DIRECT_HIGH_RISK_ARCHITECTURE_EXCEPTION")][string]$EscalationReason = "",
  [string]$PriorSonnetRecordPath = "",
  [ValidatePattern('^$|^[A-Za-z0-9][A-Za-z0-9_.-]{2,100}$')][string]$DecisionUnitId = "",
  [switch]$AllowDirectOpusArchitectureException,
  [switch]$AllowMaxEffort,
  [switch]$AllowPrimaryWorktree,
  [switch]$SelfTest
)

$ErrorActionPreference = "Stop"
$OpusDailyCeiling = 2

function Redact-Text {
  param([string]$Text)
  if ($null -eq $Text) { return "" }
  $redacted = $Text
  foreach ($name in @("ANTHROPIC_API_KEY","ANTHROPIC_AUTH_TOKEN","AWS_ACCESS_KEY_ID","AWS_SECRET_ACCESS_KEY","AWS_SESSION_TOKEN","GITHUB_TOKEN","GH_TOKEN","CURSOR_API_KEY","CIVITAI_API_KEY")) {
    $value = [Environment]::GetEnvironmentVariable($name, "Process")
    if (-not [string]::IsNullOrWhiteSpace($value)) {
      $redacted = $redacted.Replace($value, "***REDACTED_$name***")
    }
  }
  $redacted = $redacted -replace '(?i)(api[_-]?key|token|secret|auth)(\s*[:=]\s*)([^\s"'']{8,})', '$1$2***REDACTED***'
  return $redacted
}

function Quote-ProcessArgument {
  param([string]$Arg)
  if ($null -eq $Arg) { return '""' }
  if ($Arg -notmatch '[\s"]') { return $Arg }
  return '"' + ($Arg -replace '\\','\\' -replace '"','\"') + '"'
}

function Get-RegisteredGitWorktreeRoots {
  param([Parameter(Mandatory=$true)][string]$RepoRoot)
  $repoFull = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd('\')
  $output = @(& git.exe -C $repoFull worktree list --porcelain 2>&1)
  if ($LASTEXITCODE -ne 0) { throw "Unable to enumerate registered Git worktrees for ${repoFull}: $($output -join ' ')" }
  $roots = @($output | ForEach-Object { [string]$_ } | Where-Object {
    $_.StartsWith("worktree ", [System.StringComparison]::Ordinal)
  } | ForEach-Object { [System.IO.Path]::GetFullPath($_.Substring(9)).TrimEnd('\') })
  if ($roots.Count -lt 1) { throw "Git reported no registered worktrees for $repoFull" }
  if (@($roots | Where-Object { $_.Equals($repoFull, [System.StringComparison]::OrdinalIgnoreCase) }).Count -ne 1) {
    throw "Claude ProjectRoot is not a registered worktree: $repoFull"
  }
  return $roots
}

function Enter-BoundedHandoffLock {
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)][System.Collections.IDictionary]$Payload,
    [int]$WaitSeconds,
    [int]$PollSeconds,
    [int]$StaleMinutes
  )
  $wait = [System.Diagnostics.Stopwatch]::StartNew()
  $staleRemoved = $false
  while ($true) {
    if (Test-Path -LiteralPath $Path) {
      $item = Get-Item -LiteralPath $Path
      $ownerAlive = $true
      try {
        $existing = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -ErrorAction Stop
        $ownerAlive = $null -ne (Get-Process -Id ([int]$existing.pid) -ErrorAction SilentlyContinue)
      } catch { $ownerAlive = $false }
      if (((Get-Date) - $item.LastWriteTime).TotalMinutes -ge $StaleMinutes -or -not $ownerAlive) {
        Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
        $staleRemoved = $true
      }
    }
    try {
      $bytes = [System.Text.Encoding]::UTF8.GetBytes(($Payload | ConvertTo-Json -Compress))
      $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
      try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
      $wait.Stop()
      return [pscustomobject]@{ waited_ms = $wait.ElapsedMilliseconds; stale_lock_removed = $staleRemoved }
    } catch [System.IO.IOException] {
      if ($wait.Elapsed.TotalSeconds -ge $WaitSeconds) {
        $wait.Stop()
        throw "CLAUDE_SUBSCRIPTION_LOCK_WAIT_TIMEOUT: Claude lock remained busy for $WaitSeconds seconds."
      }
      Start-Sleep -Seconds $PollSeconds
    }
  }
}

function Normalize-WorkerStatus {
  param([string]$Status)
  $value = ([string]$Status).Trim().Trim('*').Trim().ToLowerInvariant() -replace '[\s-]+','_'
  if ($value -match '^(pass|complete|completed|ready|success|ok|confirmed|verified)$') { return "pass" }
  if ($value -match '^pass_with_(?:.*_)?findings?$') { return "pass_with_findings" }
  if ($value -match '^(verified_)?blocked(_as_intended)?$') { return "blocked" }
  if ($value -match '^(fail|failed|incomplete|error|unable|declined)$') { return "fail" }
  return $value
}

function Normalize-WorkerConfidence {
  param([string]$Confidence)
  $value = ([string]$Confidence).Trim().Trim('*').Trim().ToLowerInvariant() -replace '[\s_]+','-'
  if ($value -in @("medium-high","high-medium")) { return "medium" }
  if ($value -in @("low-medium","medium-low")) { return "low" }
  return $value
}

function Test-EnvPresent {
  param([Parameter(Mandatory=$true)][string]$Name)
  foreach ($target in @("Process","User","Machine")) {
    $value = [Environment]::GetEnvironmentVariable($Name, $target)
    if (-not [string]::IsNullOrWhiteSpace($value)) { return $true }
  }
  return $false
}

function Get-FileSha256OrMissing {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return "MISSING" }
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-WorktreeSnapshot {
  param([Parameter(Mandatory=$true)][string]$RepoRoot)
  $paths = @()
  foreach ($commandArgs in @(
    @("-C",$RepoRoot,"diff","--name-only"),
    @("-C",$RepoRoot,"diff","--cached","--name-only"),
    @("-C",$RepoRoot,"ls-files","--others","--exclude-standard")
  )) {
    $priorErrorActionPreference = $ErrorActionPreference
    try {
      $ErrorActionPreference = "Continue"
      $output = @(& git @commandArgs 2>$null)
      $gitExitCode = $LASTEXITCODE
    } finally {
      $ErrorActionPreference = $priorErrorActionPreference
    }
    if ($gitExitCode -ne 0) { throw "Unable to capture read-only Git worktree snapshot." }
    $paths += $output
  }
  $entries = @()
  foreach ($relative in @($paths | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | Sort-Object -Unique)) {
    $full = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $relative))
    $entries += [ordered]@{
      path = ($relative -replace '\\','/')
      sha256_or_missing = Get-FileSha256OrMissing -Path $full
    }
  }
  $priorErrorActionPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = "Continue"
    $head = (& git -C $RepoRoot rev-parse HEAD 2>$null).Trim()
    $gitExitCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $priorErrorActionPreference
  }
  if ($gitExitCode -ne 0) { throw "Unable to resolve repository HEAD for worktree snapshot." }
  $payload = [ordered]@{ head = $head; entries = $entries }
  $json = $payload | ConvertTo-Json -Depth 6 -Compress
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($json)
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try { $fingerprint = ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant() } finally { $sha.Dispose() }
  return [pscustomobject]@{ fingerprint = $fingerprint; head = $head; paths = @($entries | ForEach-Object { $_.path }); entries = $entries }
}

function Get-WorktreeChangedPaths {
  param(
    [Parameter(Mandatory=$true)]$Before,
    [Parameter(Mandatory=$true)]$After
  )
  $beforeMap = @{}
  $afterMap = @{}
  foreach ($entry in @($Before.entries)) { $beforeMap[[string]$entry.path] = [string]$entry.sha256_or_missing }
  foreach ($entry in @($After.entries)) { $afterMap[[string]$entry.path] = [string]$entry.sha256_or_missing }
  $paths = @($beforeMap.Keys) + @($afterMap.Keys)
  $changed = @()
  foreach ($path in @($paths | Sort-Object -Unique)) {
    if (-not $beforeMap.ContainsKey($path) -or -not $afterMap.ContainsKey($path) -or $beforeMap[$path] -ne $afterMap[$path]) {
      $changed += $path
    }
  }
  if ([string]$Before.head -ne [string]$After.head) { $changed += "@git/HEAD" }
  return @($changed | Sort-Object -Unique)
}

function Normalize-RepoRelativePath {
  param([Parameter(Mandatory=$true)][string]$Path)
  $normalized = ($Path -replace '\\','/')
  while ($normalized.StartsWith('./')) { $normalized = $normalized.Substring(2) }
  $normalized = $normalized.TrimStart('/')
  if ([string]::IsNullOrWhiteSpace($normalized) -or $normalized -match '[:\u0000-\u001F\u007F\uE000-\uF8FF]') {
    throw "Malformed scope-packet path: $Path"
  }
  if (@($normalized -split '/') -contains '..') { throw "Scope-packet path traversal is forbidden: $Path" }
  return $normalized
}

function Read-ValidatedScopePacket {
  param(
    [Parameter(Mandatory=$true)][string]$PacketPath,
    [Parameter(Mandatory=$true)][string]$RepoRoot,
    [Parameter(Mandatory=$true)][string[]]$TrustedPacketRoots,
    [Parameter(Mandatory=$true)][long]$ScopeByteLimit
  )
  $packetFull = [System.IO.Path]::GetFullPath($PacketPath)
  $repoFull = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd('\')
  $trustedPacket = @($TrustedPacketRoots | Where-Object {
    $trustedRoot = [System.IO.Path]::GetFullPath((Join-Path $_ "runtime_artifacts\agent_handoffs\scope_packets")).TrimEnd('\')
    $packetFull.StartsWith($trustedRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)
  }).Count -gt 0
  if (-not $trustedPacket) {
    throw "Scope packet is outside registered trusted packet roots: $PacketPath"
  }
  if (-not (Test-Path -LiteralPath $packetFull -PathType Leaf)) { throw "Scope packet missing: $packetFull" }
  $packet = Get-Content -LiteralPath $packetFull -Raw | ConvertFrom-Json -ErrorAction Stop
  if ($packet.artifact_type -ne "ai_worker_scope_packet" -or $packet.status -ne "ready") {
    throw "Invalid scope packet contract: $packetFull"
  }
  if ([string]$packet.worker_lane -ne "Claude") { throw "Scope packet worker_lane must be Claude: $packetFull" }
  $files = @($packet.files)
  if ($files.Count -lt 1 -or $files.Count -gt 12 -or [int]$packet.candidate_count -ne $files.Count) {
    throw "Claude scope packet must contain 1-12 exact files: $packetFull"
  }
  [long]$totalBytes = 0
  foreach ($file in $files) {
    $relative = Normalize-RepoRelativePath -Path ([string]$file.path)
    $full = [System.IO.Path]::GetFullPath((Join-Path $repoFull $relative))
    if (-not $full.StartsWith($repoFull + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
      throw "Scope packet file is outside repository root: $relative"
    }
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { throw "Scope packet file missing: $relative" }
    $actualLength = (Get-Item -LiteralPath $full).Length
    if ($null -ne $file.bytes -and [long]$file.bytes -ne $actualLength) { throw "Scope packet byte length drifted: $relative" }
    $actualHash = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne ([string]$file.sha256).ToLowerInvariant()) { throw "Scope packet hash drifted: $relative" }
    $totalBytes += $actualLength
  }
  if ($null -ne $packet.total_bytes -and [long]$packet.total_bytes -ne $totalBytes) {
    throw "Scope packet aggregate byte count drifted: $packetFull"
  }
  if ($totalBytes -gt $ScopeByteLimit) {
    throw "Claude scope packet exceeds MaxScopeBytes=${ScopeByteLimit}: $totalBytes bytes"
  }
  return [pscustomobject]@{ full_path = $packetFull; packet = $packet; files = $files; total_bytes = $totalBytes }
}

function Read-ValidatedPriorSonnetRecord {
  param(
    [Parameter(Mandatory=$true)][string]$RecordPath,
    [Parameter(Mandatory=$true)][string]$RepoRoot,
    [Parameter(Mandatory=$true)][string[]]$TrustedRecordRoots,
    [Parameter(Mandatory=$true)][string]$ExpectedDecisionUnitId
  )
  $recordFull = [System.IO.Path]::GetFullPath($RecordPath)
  $trustedRecord = @($TrustedRecordRoots | Where-Object {
    $allowedRoot = [System.IO.Path]::GetFullPath((Join-Path $_ "runtime_artifacts\agent_handoffs\claude_subscription")).TrimEnd('\')
    $recordFull.StartsWith($allowedRoot + '\', [System.StringComparison]::OrdinalIgnoreCase)
  }).Count -gt 0
  if (-not $trustedRecord) {
    throw "CLAUDE_OPUS_ESCALATION_NOT_JUSTIFIED: prior Sonnet record is outside the Claude handoff root."
  }
  if (-not (Test-Path -LiteralPath $recordFull -PathType Leaf)) {
    throw "CLAUDE_OPUS_ESCALATION_NOT_JUSTIFIED: prior Sonnet record is missing."
  }
  $prior = Get-Content -LiteralPath $recordFull -Raw | ConvertFrom-Json -ErrorAction Stop
  $classification = [string]$prior.classification
  $validCompletedClassification = $classification -in @("CLAUDE_SONNET_HANDOFF_COMPLETED","CLAUDE_SUBSCRIPTION_HANDOFF_COMPLETED","CLAUDE_SUBSCRIPTION_HANDOFF_COMPLETED_WITH_FINDINGS")
  $validBlockedClassification = $classification -in @("CLAUDE_SUBSCRIPTION_HANDOFF_COMPLETED_BLOCKED","CLAUDE_SUBSCRIPTION_WORKER_REPORTED_BLOCKED")
  if ((-not $validCompletedClassification -and -not $validBlockedClassification) -or [string]$prior.requested_model -ne "claude-sonnet-5") {
    throw "CLAUDE_OPUS_ESCALATION_NOT_JUSTIFIED: prior record is not a completed or worker-blocked pinned Sonnet 5 handoff."
  }
  if ($validCompletedClassification -and [string]$prior.status -ne "PASS") {
    throw "CLAUDE_OPUS_ESCALATION_NOT_JUSTIFIED: completed Sonnet evidence must have status PASS."
  }
  if ($validBlockedClassification -and [string]$prior.status -notin @("PASS","FAIL")) {
    throw "CLAUDE_OPUS_ESCALATION_NOT_JUSTIFIED: blocked Sonnet evidence must be finalized."
  }
  if ($prior.scope_packet_validated -ne $true -or $prior.scope_files_unchanged -ne $true) {
    throw "CLAUDE_OPUS_ESCALATION_NOT_JUSTIFIED: prior Sonnet evidence must be scope-validated with unchanged hash-bound files."
  }
  if ([string]$prior.decision_unit_id -ne $ExpectedDecisionUnitId) {
    throw "CLAUDE_OPUS_ESCALATION_NOT_JUSTIFIED: prior Sonnet decision unit does not match $ExpectedDecisionUnitId."
  }
  $finalized = [DateTimeOffset]$prior.finalized_at
  if ($finalized -lt [DateTimeOffset]::Now.AddDays(-7)) {
    throw "CLAUDE_OPUS_ESCALATION_NOT_JUSTIFIED: prior Sonnet record is older than seven days."
  }
  $reportedStatus = Normalize-WorkerStatus -Status ([string]$prior.worker_reported_status)
  $reportedConfidence = Normalize-WorkerConfidence -Confidence ([string]$prior.worker_reported_confidence)
  if ($reportedStatus -notin @("pass","pass_with_findings","blocked","fail")) {
    throw "CLAUDE_OPUS_ESCALATION_NOT_JUSTIFIED: prior Sonnet status is missing or not normalized."
  }
  if ($reportedConfidence -notin @("low","medium","high")) {
    throw "CLAUDE_OPUS_ESCALATION_NOT_JUSTIFIED: prior Sonnet confidence must be exactly low, medium, or high."
  }
  return [pscustomobject]@{
    full_path = $recordFull
    record = $prior
    sha256 = (Get-FileHash -LiteralPath $recordFull -Algorithm SHA256).Hash.ToLowerInvariant()
    worker_reported_status = $reportedStatus
    worker_reported_confidence = $reportedConfidence
    blocked = $validBlockedClassification
  }
}

function Get-TodaysCompletedOpusUsageMarkers {
  param([Parameter(Mandatory=$true)][string]$ExternalRoot)
  $root = Join-Path $ExternalRoot ("opus_usage\" + [DateTimeOffset]::Now.ToString("yyyy-MM-dd"))
  if (-not (Test-Path -LiteralPath $root -PathType Container)) { return @() }
  return @(Get-ChildItem -LiteralPath $root -Filter *.json -File -ErrorAction SilentlyContinue | ForEach-Object {
    try {
      $candidate = Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json -ErrorAction Stop
      if (
        [string]$candidate.artifact_type -ne "claude_opus_global_usage_marker" -or
        [string]$candidate.status -ne "PASS" -or
        [string]$candidate.classification -ne "CLAUDE_OPUS_ESCALATION_COMPLETED" -or
        [string]$candidate.requested_model -ne "claude-opus-4-8" -or
        [string]::IsNullOrWhiteSpace([string]$candidate.decision_unit_id) -or
        [string]::IsNullOrWhiteSpace([string]$candidate.handoff_record_path)
      ) { return }
      $handoff = Get-Content -LiteralPath ([string]$candidate.handoff_record_path) -Raw | ConvertFrom-Json -ErrorAction Stop
      if (
        [string]$handoff.status -ne "PASS" -or
        [string]$handoff.classification -ne "CLAUDE_OPUS_ESCALATION_COMPLETED" -or
        [string]$handoff.requested_model -ne "claude-opus-4-8" -or
        [string]$handoff.decision_unit_id -ne [string]$candidate.decision_unit_id
      ) { return }
      $resultPath = $(if (-not [string]::IsNullOrWhiteSpace([string]$candidate.result_path)) { [string]$candidate.result_path } else { [string]$handoff.output_path })
      if ([string]::IsNullOrWhiteSpace($resultPath) -or -not (Test-Path -LiteralPath $resultPath -PathType Leaf)) { return }
      if (-not [string]::IsNullOrWhiteSpace([string]$candidate.result_sha256)) {
        $actualResultHash = (Get-FileHash -LiteralPath $resultPath -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($actualResultHash -ne ([string]$candidate.result_sha256).ToLowerInvariant()) { return }
      } elseif ([int]$candidate.schema_version -ne 1) {
        return
      }
      if ([DateTimeOffset]$candidate.finalized_at -lt [DateTimeOffset]::Now.Date) { return }
      $candidate
    } catch { }
  })
}

function Get-WorkerReportedStatus {
  param([string]$Text)
  if ([string]::IsNullOrWhiteSpace($Text)) { return "" }
  $match = [regex]::Match($Text, '(?im)^\s*(?:[-*]\s*)?\*{0,2}status\s*:\*{0,2}\s*([^\r\n]+)')
  if (-not $match.Success) { return "" }
  return $match.Groups[1].Value.Trim().Trim('*').Trim()
}

function Get-WorkerReportedConfidence {
  param([string]$Text)
  if ([string]::IsNullOrWhiteSpace($Text)) { return "" }
  $match = [regex]::Match($Text, '(?im)^\s*(?:[-*]\s*)?\*{0,2}confidence\s*:\*{0,2}\s*([^\r\n]+)')
  if (-not $match.Success) { return "" }
  return $match.Groups[1].Value.Trim().Trim('*').Trim().ToLowerInvariant()
}

function Test-PriorSonnetEscalationTrigger {
  param(
    [Parameter(Mandatory=$true)][object]$PriorSonnet,
    [Parameter(Mandatory=$true)][string]$Reason
  )
  switch ($Reason) {
    "SONNET_BLOCKED_OR_LOW_CONFIDENCE" { return ($PriorSonnet.blocked -or $PriorSonnet.worker_reported_confidence -eq "low") }
    "HIGH_SEVERITY_UNRESOLVED_AFTER_REMEDIATION" { return ($PriorSonnet.blocked -or $PriorSonnet.worker_reported_confidence -in @("low","medium")) }
    "CROSS_SYSTEM_ARCHITECTURE" { return $true }
    "MATERIAL_AUTHORITY_CONTRADICTION" { return $true }
    "LONG_FORM_ARCHITECTURE_OVER_15_MINUTES" { return $true }
    default { return $false }
  }
}

if ($SelfTest) {
  $checks = [ordered]@{
    normal_path_accepted = ((Normalize-RepoRelativePath -Path 'Plan/Instructions/example.md') -eq 'Plan/Instructions/example.md')
    malformed_path_rejected = $false
    exact_models_pinned = ($ClaudeModel -in @("claude-sonnet-5","claude-opus-4-8"))
    plain_status_parsed = ((Get-WorkerReportedStatus -Text "status: pass") -eq "pass")
    markdown_status_parsed = ((Get-WorkerReportedStatus -Text "- **status:** pass") -eq "pass")
    blocked_status_parsed = ((Get-WorkerReportedStatus -Text "**status:** blocked") -eq "blocked")
    exact_confidence_parsed = ((Get-WorkerReportedConfidence -Text "- **confidence:** high") -eq "high")
    confirmed_status_normalized = ((Normalize-WorkerStatus -Status "confirmed") -eq "pass")
    findings_status_normalized = ((Normalize-WorkerStatus -Status "pass_with_findings") -eq "pass_with_findings")
    verified_blocked_status_normalized = ((Normalize-WorkerStatus -Status "verified_blocked_as_intended") -eq "blocked")
    compound_confidence_normalized = ((Normalize-WorkerConfidence -Confidence "medium-high") -eq "medium")
    opus_ceiling_immutable = ($OpusDailyCeiling -eq 2)
  }
  try { Normalize-RepoRelativePath -Path "C$([char]0xF03A)$([char]0xF05C)Comfy_UI_Main" | Out-Null } catch { $checks.malformed_path_rejected = $true }
  try {
    $snapshot = Get-WorktreeSnapshot -RepoRoot ([System.IO.Path]::GetFullPath($ProjectRoot))
    $checks.worktree_fingerprint_available = (-not [string]::IsNullOrWhiteSpace($snapshot.fingerprint))
  } catch {
    $checks.worktree_fingerprint_available = $false
    $checks.worktree_fingerprint_error = $_.Exception.Message
  }
  [ordered]@{ status = $(if (($checks.Values | Where-Object { -not $_ }).Count -eq 0) { 'PASS' } else { 'FAIL' }); checks = $checks } | ConvertTo-Json -Depth 5
  return
}

$projectRootFull = [System.IO.Path]::GetFullPath($ProjectRoot)
$registeredWorktreeRoots = @(Get-RegisteredGitWorktreeRoots -RepoRoot $projectRootFull)
$primaryWorktreeRoot = $registeredWorktreeRoots[0]
$projectIsPrimaryWorktree = $projectRootFull.TrimEnd('\').Equals($primaryWorktreeRoot, [System.StringComparison]::OrdinalIgnoreCase)
$defaultScopeByteLimit = 524288
$externalRoot = "C:\Users\kevin\.codex\claude_subscription_handoff"
$lockPath = Join-Path $externalRoot "claude_subscription.lock"
$timestamp = (Get-Date -Format "yyyyMMddTHHmmsszzz") -replace ':',''
$safeTaskName = ($TaskName -replace '[^A-Za-z0-9_.-]+','_').Trim('_')
if ([string]::IsNullOrWhiteSpace($safeTaskName)) { $safeTaskName = "claude_task" }
if ([string]::IsNullOrWhiteSpace($DecisionUnitId)) {
  $DecisionUnitId = $safeTaskName
  if ($DecisionUnitId.Length -gt 100) { $DecisionUnitId = $DecisionUnitId.Substring(0,100) }
}
$runDir = Join-Path $projectRootFull ("runtime_artifacts\agent_handoffs\claude_subscription\{0}_{1}" -f $timestamp,$safeTaskName)
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

$recordPath = Join-Path $runDir "handoff_record.json"
$record = [ordered]@{
  schema_version = 2
  task_name = $TaskName
  lane = "claude_subscription"
  task_tier = $TaskTier
  decision_unit_id = $DecisionUnitId
  requested_model = $ClaudeModel
  effort = $Effort
  permission_mode = $PermissionMode
  allow_broad_discovery = [bool]$AllowBroadDiscovery
  broad_discovery_reason = $BroadDiscoveryReason
  max_scope_bytes = $MaxScopeBytes
  scope_byte_budget_reason = $ScopeByteBudgetReason
  escalation_reason = $EscalationReason
  opus_daily_ceiling = $OpusDailyCeiling
  direct_opus_exception = [bool]$AllowDirectOpusArchitectureException
  api_fallback_allowed = $false
  usage_credit_state = "not_programmatically_verifiable_fail_closed_on_limit"
  started_at = (Get-Date).ToString("o")
  project_root = $projectRootFull
  run_dir = $runDir
  status = "IN_PROGRESS"
  classification = $(switch ($TaskTier) {
    "HealthProbe" { "CLAUDE_HEALTH_PROBE_IN_PROGRESS" }
    "SonnetPrimary" { "CLAUDE_SONNET_HANDOFF_IN_PROGRESS" }
    "OpusEscalation" { "CLAUDE_OPUS_ESCALATION_IN_PROGRESS" }
  })
  timeout_seconds = $TimeoutSeconds
  stale_lock_minutes = $StaleLockMinutes
  lock_wait_seconds = $LockWaitSeconds
  lock_poll_seconds = $LockPollSeconds
  registered_worktree_roots = $registeredWorktreeRoots
  primary_worktree_root = $primaryWorktreeRoot
  project_is_primary_worktree = $projectIsPrimaryWorktree
  warnings = @()
  output_path = Join-Path $runDir "claude_stdout.txt"
  stderr_path = Join-Path $runDir "claude_stderr.txt"
  work_order_path = Join-Path $runDir "work_order.md"
  issues = @()
}
$worktreeBefore = $null
$scopePacket = $null
$scopeHashesBefore = @{}
$lockAcquired = $false
$workerStopwatch = $null

if ([string]::IsNullOrWhiteSpace($ClaudeExe)) {
  $candidateRoot = Join-Path $env:APPDATA "Claude\claude-code"
  $candidate = Get-ChildItem -LiteralPath $candidateRoot -Directory -ErrorAction SilentlyContinue |
    Sort-Object Name -Descending |
    ForEach-Object { Join-Path $_.FullName "claude.exe" } |
    Where-Object { Test-Path -LiteralPath $_ } |
    Select-Object -First 1
  if ([string]::IsNullOrWhiteSpace($candidate)) { throw "Claude Code executable not found under $candidateRoot" }
  $ClaudeExe = $candidate
}
$record.claude_exe = $ClaudeExe

try {
  $lockPayload = [ordered]@{
    pid = $PID
    task_name = $TaskName
    created_at = (Get-Date).ToString("o")
    run_dir = $runDir
  }
  $lockResult = Enter-BoundedHandoffLock -Path $lockPath -Payload $lockPayload -WaitSeconds $LockWaitSeconds -PollSeconds $LockPollSeconds -StaleMinutes $StaleLockMinutes
  $lockAcquired = $true
  $record.lock_wait_duration_ms = $lockResult.waited_ms
  $record.stale_lock_removed = $lockResult.stale_lock_removed
} catch {
  $record.status = "BLOCKED"
  $record.classification = "CLAUDE_SUBSCRIPTION_LOCK_WAIT_TIMEOUT"
  $record.issues += $_.Exception.Message
  $record.finalized_at = (Get-Date).ToString("o")
  $record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $recordPath -Encoding UTF8
  throw
}

try {
  if ($projectIsPrimaryWorktree -and -not $AllowPrimaryWorktree -and $TaskTier -ne "HealthProbe") {
    throw "CLAUDE_ISOLATED_WORKTREE_REQUIRED: substantive Claude handoffs must run in a registered isolated worktree."
  }
  $blockedEnv = @("ANTHROPIC_API_KEY","ANTHROPIC_AUTH_TOKEN","ANTHROPIC_BASE_URL") | Where-Object { Test-EnvPresent $_ }
  if ($blockedEnv.Count -gt 0) {
    throw "CLAUDE_API_FALLBACK_BLOCKED: subscription handoff refused because API/provider environment variables are present: $($blockedEnv -join ', ')"
  }
  if ($MaxScopeBytes -gt $defaultScopeByteLimit -and [string]::IsNullOrWhiteSpace($ScopeByteBudgetReason)) {
    throw "A scope budget above $defaultScopeByteLimit bytes requires -ScopeByteBudgetReason."
  }
  if ($Effort -eq "max" -and -not $AllowMaxEffort) {
    throw "Max effort requires explicit -AllowMaxEffort approval."
  }
  if ($TaskTier -eq "HealthProbe") {
    if ($ClaudeModel -ne "claude-sonnet-5" -or $Effort -ne "low") { throw "HealthProbe requires claude-sonnet-5 with low effort." }
  } elseif ($TaskTier -eq "SonnetPrimary") {
    if ($ClaudeModel -ne "claude-sonnet-5" -or $Effort -eq "low" -or $Effort -eq "max") {
      throw "SonnetPrimary requires claude-sonnet-5 with medium, high, or xhigh effort."
    }
    if ([string]::IsNullOrWhiteSpace($ScopePacketPath) -and -not $AllowBroadDiscovery) {
      throw "CLAUDE_SCOPE_PACKET_REQUIRED: SonnetPrimary requires a hash-bound scope packet or an explicit broad-discovery exception."
    }
  } elseif ($TaskTier -eq "OpusEscalation") {
    if ($ClaudeModel -ne "claude-opus-4-8" -or $Effort -in @("low","medium")) {
      throw "CLAUDE_OPUS_ESCALATION_NOT_JUSTIFIED: OpusEscalation requires claude-opus-4-8 with high, xhigh, or explicitly approved max effort."
    }
    if ([string]::IsNullOrWhiteSpace($EscalationReason) -or [string]::IsNullOrWhiteSpace($DecisionUnitId)) {
      throw "CLAUDE_OPUS_ESCALATION_NOT_JUSTIFIED: escalation reason and decision unit ID are required."
    }
    if ([string]::IsNullOrWhiteSpace($ScopePacketPath)) {
      throw "CLAUDE_OPUS_ESCALATION_NOT_JUSTIFIED: Opus requires a hash-validated scope packet."
    }
    if ($AllowBroadDiscovery) {
      throw "CLAUDE_OPUS_ESCALATION_NOT_JUSTIFIED: Opus escalation does not permit broad discovery."
    }
    $todayOpus = @(Get-TodaysCompletedOpusUsageMarkers -ExternalRoot $externalRoot)
    $record.completed_opus_today_before_launch = $todayOpus.Count
    if ($todayOpus.Count -ge $OpusDailyCeiling) {
      throw "CLAUDE_OPUS_DAILY_CEILING_REACHED: $($todayOpus.Count) completed Opus handoffs already reached the daily ceiling of $OpusDailyCeiling."
    }
    if (@($todayOpus | Where-Object { [string]$_.decision_unit_id -eq $DecisionUnitId }).Count -gt 0) {
      throw "CLAUDE_DUPLICATE_REVIEW_SUPPRESSED: Opus already completed for decision unit $DecisionUnitId today."
    }
  }

  $authJsonText = & $ClaudeExe auth status
  $auth = $authJsonText | ConvertFrom-Json -ErrorAction Stop
  $record.auth_method = $auth.authMethod
  $record.api_provider = $auth.apiProvider
  $record.subscription_type = $auth.subscriptionType
  if ($auth.loggedIn -ne $true -or $auth.authMethod -ne "claude.ai" -or $auth.apiProvider -ne "firstParty") {
    throw "Claude Code is not logged in with claude.ai subscription auth. Run: `"$ClaudeExe`" auth login"
  }
  $record.metering_posture = "claude_p_currently_draws_from_subscription_limits_agent_sdk_credit_change_paused"

  $sourceText = ""
  if (-not [string]::IsNullOrWhiteSpace($WorkOrderPath)) { $sourceText = Get-Content -LiteralPath $WorkOrderPath -Raw }
  if (-not [string]::IsNullOrWhiteSpace($WorkOrderText)) {
    if (-not [string]::IsNullOrWhiteSpace($sourceText)) { $sourceText += "`n`n" }
    $sourceText += $WorkOrderText
  }
  if ([string]::IsNullOrWhiteSpace($sourceText)) { throw "Provide -WorkOrderText or -WorkOrderPath." }

  $scopePacket = $null
  if (-not [string]::IsNullOrWhiteSpace($ScopePacketPath)) {
    $scopePacket = Read-ValidatedScopePacket -PacketPath $ScopePacketPath -RepoRoot $projectRootFull -TrustedPacketRoots $registeredWorktreeRoots -ScopeByteLimit $MaxScopeBytes
    $record.scope_packet_path = $scopePacket.full_path
    $record.scope_packet_candidate_count = $scopePacket.files.Count
    $record.scope_packet_total_bytes = $scopePacket.total_bytes
    $record.scope_packet_validated = $true
  }

  $priorSonnet = $null
  if ($TaskTier -eq "OpusEscalation") {
    $isDirectException = ($EscalationReason -eq "DIRECT_HIGH_RISK_ARCHITECTURE_EXCEPTION")
    if ([string]::IsNullOrWhiteSpace($PriorSonnetRecordPath)) {
      if (-not $isDirectException -or -not $AllowDirectOpusArchitectureException) {
        throw "CLAUDE_OPUS_ESCALATION_NOT_JUSTIFIED: a successful prior Sonnet record is required unless the direct high-risk architecture exception is explicitly enabled."
      }
      $record.escalation_link_validated = $true
      $record.escalation_source = "direct_high_risk_architecture_exception"
    } else {
      $priorSonnet = Read-ValidatedPriorSonnetRecord -RecordPath $PriorSonnetRecordPath -RepoRoot $projectRootFull -TrustedRecordRoots $registeredWorktreeRoots -ExpectedDecisionUnitId $DecisionUnitId
      $record.prior_sonnet_record_path = $priorSonnet.full_path
      $record.prior_sonnet_record_sha256 = $priorSonnet.sha256
      $record.prior_sonnet_task_name = $priorSonnet.record.task_name
      $record.prior_sonnet_worker_status = $priorSonnet.worker_reported_status
      $record.prior_sonnet_worker_confidence = $priorSonnet.worker_reported_confidence
      if (-not (Test-PriorSonnetEscalationTrigger -PriorSonnet $priorSonnet -Reason $EscalationReason)) {
        throw "CLAUDE_OPUS_ESCALATION_NOT_JUSTIFIED: prior Sonnet status/confidence does not satisfy escalation trigger $EscalationReason."
      }
      $record.escalation_link_validated = $true
      $record.escalation_source = "validated_pinned_sonnet_record"
    }
  }
  $broadPattern = '(?i)\b(broad|whole[- ]tree|repository[- ]wide|project[- ]wide|reconcil\w*|inventory|all files|all directories|scan (the )?(repository|project|tree))\b'
  $isProbe = $TaskName -match '(^|_)(claude_subscription_probe|scope_packet_probe)($|_)'
  $looksBroad = (($TaskName + "`n" + $sourceText) -match $broadPattern)
  if (-not $isProbe -and $looksBroad -and $null -eq $scopePacket -and -not $AllowBroadDiscovery) {
    throw "Broad Claude discovery requires -ScopePacketPath or explicit -AllowBroadDiscovery with -BroadDiscoveryReason."
  }
  if ($AllowBroadDiscovery -and [string]::IsNullOrWhiteSpace($BroadDiscoveryReason)) {
    throw "-AllowBroadDiscovery requires a non-empty -BroadDiscoveryReason."
  }

  $scopeText = if ($null -ne $scopePacket) {
    ($scopePacket.files | ForEach-Object { "- $($_.path) sha256=$($_.sha256)" }) -join "`n"
  } elseif ($AllowBroadDiscovery) {
    "- Explicit broad-discovery exception: $BroadDiscoveryReason"
  } else {
    "- No scope packet required because this task is below broad-discovery threshold."
  }

  $escalationText = if ($TaskTier -eq "OpusEscalation") {
    "Escalation reason: $EscalationReason`nPrior Sonnet record: $($record.prior_sonnet_record_path)`nDecision unit: $DecisionUnitId"
  } else {
    "Decision unit: $DecisionUnitId"
  }
  $opusOutputLabel = if ($TaskTier -eq "OpusEscalation") { "- escalation outcome:" } else { "" }

  $workOrder = @"
# Claude Subscription Work Order: $TaskName

Project root: $projectRootFull
Lane: Claude subscription semantic worker
Task tier: $TaskTier
Model requested: $ClaudeModel
Effort requested: $Effort
Permission mode: $PermissionMode
$escalationText

## Validated Scope
$scopeText

Inspect only the validated scope. Do not rediscover unrelated project trees.
The wrapper already verified each listed file's byte length and SHA-256 before launch. Treat that cryptographic validation as supplied evidence; do not attempt to recompute it with unavailable tools.

## Authority Boundary
Codex Desktop remains final authority. Do not edit files. Do not run Git, AWS, EC2, S3, Jira, ComfyUI generation, mask promotion, Wave70 gates, or Wave71+ activation.

## Output Contract
Return a compact final result only. Include labels exactly:
- status:
- summary:
- files inspected:
- blockers:
- confidence:
- recommended Codex follow-up:
$opusOutputLabel

Do not narrate future intentions. If you cannot complete the task within this call, return `status: blocked` and name the blocker.
Never print secrets or .env values.

## Task
$sourceText
"@
  Set-Content -LiteralPath $record.work_order_path -Value $workOrder -Encoding UTF8

  if ($null -ne $scopePacket) {
    foreach ($file in $scopePacket.files) {
      $relative = Normalize-RepoRelativePath -Path ([string]$file.path)
      $scopeHashesBefore[$relative] = Get-FileSha256OrMissing -Path (Join-Path $projectRootFull $relative)
    }
  }
  $worktreeBefore = Get-WorktreeSnapshot -RepoRoot $projectRootFull
  $record.worktree_fingerprint_before = $worktreeBefore.fingerprint
  $record.worktree_paths_before = $worktreeBefore.paths

  $prompt = Get-Content -LiteralPath $record.work_order_path -Raw
  $argList = @(
    "-p", $prompt,
    "--model", $ClaudeModel,
    "--effort", $Effort,
    "--permission-mode", $PermissionMode,
    "--safe-mode",
    "--disable-slash-commands",
    "--strict-mcp-config",
    "--no-chrome",
    "--tools", "Read,Glob,Grep",
    "--disallowedTools", "Bash,Edit,Write,NotebookEdit,Task,Agent",
    "--output-format", "text",
    "--no-session-persistence"
  )

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $ClaudeExe
  $psi.Arguments = (($argList | ForEach-Object { Quote-ProcessArgument $_ }) -join " ")
  $psi.WorkingDirectory = $projectRootFull
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.UseShellExecute = $false
  $credentialEnvironmentNames = @(
    "ANTHROPIC_API_KEY","ANTHROPIC_AUTH_TOKEN","ANTHROPIC_BASE_URL",
    "AWS_ACCESS_KEY_ID","AWS_SECRET_ACCESS_KEY","AWS_SESSION_TOKEN","AWS_SECURITY_TOKEN","AWS_PROFILE","AWS_DEFAULT_PROFILE","AWS_SHARED_CREDENTIALS_FILE","AWS_CONFIG_FILE","AWS_ROLE_ARN","AWS_WEB_IDENTITY_TOKEN_FILE","AWS_CONTAINER_CREDENTIALS_FULL_URI","AWS_CONTAINER_CREDENTIALS_RELATIVE_URI","AWS_CONTAINER_AUTHORIZATION_TOKEN","AWS_CONTAINER_AUTHORIZATION_TOKEN_FILE",
    "GITHUB_TOKEN","GH_TOKEN","GITHUB_ENTERPRISE_TOKEN","GH_ENTERPRISE_TOKEN","GIT_ASKPASS","SSH_ASKPASS","GCM_INTERACTIVE","GCM_CREDENTIAL_STORE","GCM_CONFIGSTORE",
    "AZURE_CLIENT_ID","AZURE_CLIENT_SECRET","AZURE_TENANT_ID","GOOGLE_APPLICATION_CREDENTIALS",
    "OPENAI_API_KEY","CURSOR_API_KEY","CIVITAI_API_KEY","HF_TOKEN","HUGGINGFACE_TOKEN","GITLAB_TOKEN"
  )
  foreach ($environmentKey in @($psi.EnvironmentVariables.Keys | ForEach-Object { [string]$_ })) {
    if ($environmentKey -match '^(?i:AWS_|GH_|GITHUB_|AZURE_|GOOGLE_|OPENAI_|ANTHROPIC_|CURSOR_|CIVITAI_|HF_TOKEN$|HUGGINGFACE_|GITLAB_|GIT_CONFIG_)') {
      $credentialEnvironmentNames += $environmentKey
    }
  }
  $credentialEnvironmentNames = @($credentialEnvironmentNames | Sort-Object -Unique)
  foreach ($name in $credentialEnvironmentNames) { [void]$psi.EnvironmentVariables.Remove($name) }
  $record.credential_environment_scrubbed = $true
  $record.scrubbed_environment_names = $credentialEnvironmentNames
  $record.tool_surface = @("Read","Glob","Grep")
  $record.safe_mode = $true
  $record.strict_mcp_config = $true
  $record.chrome_disabled = $true
  $record.skills_disabled = $true

  $proc = New-Object System.Diagnostics.Process
  $proc.StartInfo = $psi
  $sw = [System.Diagnostics.Stopwatch]::StartNew()
  $workerStopwatch = $sw
  [void]$proc.Start()
  $stdoutTask = $proc.StandardOutput.ReadToEndAsync()
  $stderrTask = $proc.StandardError.ReadToEndAsync()
  if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
    try { & taskkill.exe /PID $proc.Id /T /F | Out-Null } catch { try { $proc.Kill() } catch { } }
    try { [void]$proc.WaitForExit(5000) } catch { }
    $sw.Stop()
    $record.duration_ms = $sw.ElapsedMilliseconds
    $record.timeout_duration_ms = $sw.ElapsedMilliseconds
    throw "CLAUDE_SUBSCRIPTION_TIMEOUT: Claude subscription handoff timed out after $($sw.ElapsedMilliseconds) ms (configured timeout $TimeoutSeconds seconds)."
  }
  try { $proc.WaitForExit() } catch { }
  $stdout = Redact-Text $stdoutTask.Result
  $stderr = Redact-Text $stderrTask.Result
  $sw.Stop()

  Set-Content -LiteralPath $record.output_path -Value $stdout -Encoding UTF8
  Set-Content -LiteralPath $record.stderr_path -Value $stderr -Encoding UTF8
  $record.exit_code = $proc.ExitCode
  $record.duration_ms = $sw.ElapsedMilliseconds
  $record.stdout_length = $stdout.Length
  $record.stderr_length = $stderr.Length
  $record.result_excerpt = $stdout.Trim()
  if ($record.result_excerpt.Length -gt 4000) { $record.result_excerpt = $record.result_excerpt.Substring(0,4000) }
  $record.output_contract_validated_from = "full_stdout"

  $worktreeAfter = Get-WorktreeSnapshot -RepoRoot $projectRootFull
  $record.worktree_fingerprint_after = $worktreeAfter.fingerprint
  $record.worktree_paths_after = $worktreeAfter.paths
  $worktreeChangedPaths = @(Get-WorktreeChangedPaths -Before $worktreeBefore -After $worktreeAfter)
  $record.worktree_changed_paths = $worktreeChangedPaths
  $scopeMutationPaths = @()
  if ($null -ne $scopePacket) {
    foreach ($file in $scopePacket.files) {
      $relative = Normalize-RepoRelativePath -Path ([string]$file.path)
      $afterHash = Get-FileSha256OrMissing -Path (Join-Path $projectRootFull $relative)
      if ($scopeHashesBefore[$relative] -ne $afterHash) { $scopeMutationPaths += $relative }
    }
  }
  $record.scope_mutation_paths = $scopeMutationPaths
  $record.worktree_unchanged = ($worktreeChangedPaths.Count -eq 0)
  $record.scope_files_unchanged = ($scopeMutationPaths.Count -eq 0)
  $record.concurrent_worktree_drift_detected = (-not $record.worktree_unchanged -and $record.scope_files_unchanged)

  $record.status = if ($proc.ExitCode -eq 0) { "PASS" } else { "FAIL" }
  if ($proc.ExitCode -eq 0) {
    $record.classification = $(switch ($TaskTier) {
      "HealthProbe" { "CLAUDE_HEALTH_PROBE_COMPLETED" }
      "SonnetPrimary" { "CLAUDE_SONNET_HANDOFF_COMPLETED" }
      "OpusEscalation" { "CLAUDE_OPUS_ESCALATION_COMPLETED" }
    })
  } elseif (($stdout + "`n" + $stderr) -match '(?i)(usage limit|limit reached|rate limit|usage.*reset|capacity unavailable)') {
    $record.classification = "CLAUDE_SUBSCRIPTION_CAPACITY_UNAVAILABLE"
  } else {
    $record.classification = "CLAUDE_SUBSCRIPTION_PROCESS_FAILED"
  }

  if (-not $record.scope_files_unchanged) {
    $record.status = "FAIL"
    $record.classification = "CLAUDE_SUBSCRIPTION_READ_ONLY_MUTATION_VIOLATION"
    $record.issues += "A hash-bound scope file changed while the Claude handoff was active."
  } elseif (-not $record.worktree_unchanged) {
    $record.warnings += "CLAUDE_CONCURRENT_WORKTREE_DRIFT_WARNING: repository-visible state changed outside the hash-bound scope; the hash-bound scope remained unchanged."
  }

  $requiredLabels = @("status:", "summary:", "files inspected:", "blockers:", "confidence:", "recommended Codex follow-up:")
  if ($TaskTier -eq "OpusEscalation") { $requiredLabels += "escalation outcome:" }
  $outputContractText = $stdout.Trim()
  $missingLabels = @($requiredLabels | Where-Object { $outputContractText -notmatch [regex]::Escape($_) })
  $workerReportedStatus = Get-WorkerReportedStatus -Text $outputContractText
  $workerReportedStatus = Normalize-WorkerStatus -Status $workerReportedStatus
  $workerReportedConfidence = Get-WorkerReportedConfidence -Text $outputContractText
  $workerReportedConfidence = Normalize-WorkerConfidence -Confidence $workerReportedConfidence
  $record.worker_reported_status = $workerReportedStatus
  $record.worker_reported_confidence = $workerReportedConfidence
  $promiseOnlyPattern = '(?i)\b(i.ll|i will|next i.ll|next i will)\b.*\b(inspect|read|extract|check)\b'
  $tailLength = [Math]::Min(700, $outputContractText.Length)
  $resultTail = if ($tailLength -gt 0) { $outputContractText.Substring($outputContractText.Length - $tailLength, $tailLength) } else { "" }
  $endsWithPromise = ($resultTail -match $promiseOnlyPattern -and $resultTail -notmatch 'recommended Codex follow-up:')
  if (($missingLabels.Count -gt 0 -or $endsWithPromise -or [string]::IsNullOrWhiteSpace($workerReportedStatus) -or [string]::IsNullOrWhiteSpace($workerReportedConfidence)) -and $proc.ExitCode -eq 0 -and $record.scope_files_unchanged) {
    $record.status = "FAIL"
    $record.classification = "CLAUDE_SUBSCRIPTION_INCOMPLETE_OUTPUT_CONTRACT"
    if ($missingLabels.Count -gt 0) { $record.issues += ("Claude result missed output contract labels: " + ($missingLabels -join ", ")) }
    if ($endsWithPromise) { $record.issues += "Claude result looked like an unfinished promise, not a completed handoff." }
    if ([string]::IsNullOrWhiteSpace($workerReportedStatus)) { $record.issues += "Claude result did not contain a parseable status label." }
    if ([string]::IsNullOrWhiteSpace($workerReportedConfidence)) { $record.issues += "Claude result did not contain a parseable confidence label." }
  } elseif ($proc.ExitCode -eq 0 -and $record.scope_files_unchanged -and -not [string]::IsNullOrWhiteSpace($workerReportedStatus)) {
    if ($workerReportedConfidence -notin @("low","medium","high")) {
      $record.status = "FAIL"
      $record.classification = "CLAUDE_SUBSCRIPTION_INVALID_CONFIDENCE_LABEL"
      $record.issues += "Claude confidence must be exactly low, medium, or high: $workerReportedConfidence"
    } elseif ($workerReportedStatus -eq "blocked") {
      $record.status = "PASS"
      $record.classification = "CLAUDE_SUBSCRIPTION_HANDOFF_COMPLETED_BLOCKED"
      $record.warnings += "Claude completed the bounded analysis and reported an explicit blocker."
    } elseif ($workerReportedStatus -eq "fail") {
      $record.status = "FAIL"
      $record.classification = "CLAUDE_SUBSCRIPTION_WORKER_REPORTED_FAILURE"
      $record.issues += "Claude reported failure."
    } elseif ($workerReportedStatus -eq "pass_with_findings") {
      $record.status = "PASS"
      $record.classification = "CLAUDE_SUBSCRIPTION_HANDOFF_COMPLETED_WITH_FINDINGS"
    } elseif ($workerReportedStatus -ne "pass") {
      $record.status = "FAIL"
      $record.classification = "CLAUDE_SUBSCRIPTION_INVALID_STATUS_LABEL"
      $record.issues += "Claude returned an unrecognized status label: $workerReportedStatus"
    }
  }
  if ($TaskTier -eq "OpusEscalation" -and $record.status -eq "PASS" -and $record.classification -eq "CLAUDE_OPUS_ESCALATION_COMPLETED") {
    $opusUsageRoot = Join-Path $externalRoot ("opus_usage\" + [DateTimeOffset]::Now.ToString("yyyy-MM-dd"))
    New-Item -ItemType Directory -Force -Path $opusUsageRoot | Out-Null
    $safeDecisionUnit = ($DecisionUnitId -replace '[^A-Za-z0-9_.-]+','_').Trim('_')
    $opusUsageMarkerPath = Join-Path $opusUsageRoot ("{0}_{1}.json" -f $timestamp,$safeDecisionUnit)
    $opusUsageMarker = [ordered]@{
      schema_version = 2
      artifact_type = "claude_opus_global_usage_marker"
      status = "PASS"
      classification = "CLAUDE_OPUS_ESCALATION_COMPLETED"
      finalized_at = (Get-Date).ToString("o")
      requested_model = "claude-opus-4-8"
      decision_unit_id = $DecisionUnitId
      project_root = $projectRootFull
      handoff_record_path = $recordPath
      result_path = $record.output_path
      result_sha256 = (Get-FileHash -LiteralPath $record.output_path -Algorithm SHA256).Hash.ToLowerInvariant()
      escalation_reason = $EscalationReason
    }
    $opusUsageMarker | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $opusUsageMarkerPath -Encoding UTF8
    $record.opus_global_usage_marker_path = $opusUsageMarkerPath
  }
} catch {
  $record.status = "FAIL"
  $message = Redact-Text $_.Exception.Message
  $classification = if ($message -match '^CLAUDE_[A-Z0-9_]+:') { ($message -split ':',2)[0] } else { "CLAUDE_SUBSCRIPTION_WRAPPER_FAILED" }
  if ($null -ne $worktreeBefore) {
    try {
      $worktreeAfter = Get-WorktreeSnapshot -RepoRoot $projectRootFull
      $record.worktree_fingerprint_after = $worktreeAfter.fingerprint
      $record.worktree_paths_after = $worktreeAfter.paths
      $worktreeChangedPaths = @(Get-WorktreeChangedPaths -Before $worktreeBefore -After $worktreeAfter)
      $record.worktree_changed_paths = $worktreeChangedPaths
      $scopeMutationPaths = @()
      if ($null -ne $scopePacket) {
        foreach ($file in $scopePacket.files) {
          $relative = Normalize-RepoRelativePath -Path ([string]$file.path)
          $afterHash = Get-FileSha256OrMissing -Path (Join-Path $projectRootFull $relative)
          if ($scopeHashesBefore[$relative] -ne $afterHash) { $scopeMutationPaths += $relative }
        }
      }
      $record.scope_mutation_paths = $scopeMutationPaths
      $record.worktree_unchanged = ($worktreeChangedPaths.Count -eq 0)
      $record.scope_files_unchanged = ($scopeMutationPaths.Count -eq 0)
      $record.concurrent_worktree_drift_detected = (-not $record.worktree_unchanged -and $record.scope_files_unchanged)
      if (-not $record.scope_files_unchanged) {
        $classification = "CLAUDE_SUBSCRIPTION_READ_ONLY_MUTATION_VIOLATION"
        $record.issues += "A hash-bound scope file changed before the handoff failed."
      } elseif (-not $record.worktree_unchanged) {
        $record.warnings += "CLAUDE_CONCURRENT_WORKTREE_DRIFT_WARNING: repository-visible state changed outside the hash-bound scope before the handoff failed."
      }
    } catch { $record.issues += "Unable to capture the post-failure worktree fingerprint." }
  }
  $record.classification = $classification
  $record.issues += $message
  throw
} finally {
  if ($null -ne $workerStopwatch -and $workerStopwatch.IsRunning) {
    $workerStopwatch.Stop()
    $record.duration_ms = $workerStopwatch.ElapsedMilliseconds
  }
  $record.finalized_at = (Get-Date).ToString("o")
  $record | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $recordPath -Encoding UTF8
  if ($lockAcquired) { Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue }
}

$record | ConvertTo-Json -Depth 12
