<#
.SYNOPSIS
Runs a bounded Cursor CLI handoff for Comfy_UI_Main without exposing secrets.
#>
[CmdletBinding(PositionalBinding=$false)]
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$CredentialRoot = "",
  [Parameter(Mandatory=$true)][string]$TaskName,
  [ValidateSet("ask","plan","agent")][string]$Mode = "ask",
  [string]$WorkOrderText = "",
  [string]$WorkOrderPath = "",
  [string]$ScopePacketPath = "",
  [ValidateRange(65536, 2097152)][long]$MaxScopeBytes = 524288,
  [string]$ScopeByteBudgetReason = "",
  [string[]]$AllowedPaths = @(),
  [string[]]$ForbiddenActions = @(
    "print secrets or .env values",
    "git add/commit/push/reset/checkout/stage/unstage",
    "start or stop EC2",
    "upload to S3",
    "launch ComfyUI GPU/runtime generation",
    "promote masks or rerun Wave70 hard gates",
    "activate Wave71+",
    "mutate Jira",
    "execute project scripts, tests, validators, generators, or audits in ask/plan unless explicitly declared side-effect-free"
  ),
  [ValidateRange(30, 900)][int]$TimeoutSeconds = 600,
  [int]$StaleLockMinutes = 120,
  [ValidateRange(0, 1800)][int]$LockWaitSeconds = 600,
  [ValidateRange(1, 30)][int]$LockPollSeconds = 2,
  [ValidateRange(1, 60)][int]$InterruptedRecordGraceMinutes = 5,
  [string]$CursorModel = "",
  [string]$AskPlanDefaultModel = "gpt-5.3-codex",
  [string]$AgentDefaultModel = "gpt-5.3-codex",
  [ValidateNotNullOrEmpty()][string]$WslDistribution = "Ubuntu-22.04",
  [switch]$RequireGitLfs,
  [string]$GitLfsEvidencePath = "",
  [switch]$AllowWrites,
  [switch]$AllowReadOnlyCommandExecution,
  [string[]]$DeclaredReadOnlyCommands = @(),
  [string[]]$DeclaredAgentCommands = @(),
  [switch]$AllowBroadDiscovery,
  [string]$BroadDiscoveryReason = "",
  [switch]$AllowPrimaryWorktree,
  [switch]$ForceCursorCommands,
  [switch]$SelfTest
)

$ErrorActionPreference = "Stop"
$CursorAgentPath = "/home/kevin/.local/bin/cursor-agent"

try {
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
} catch {
  if ((Get-ExecutionPolicy) -notin @("Bypass", "Unrestricted")) { throw }
}

function ConvertTo-WslPath {
  param([Parameter(Mandatory=$true)][string]$Path)
  $resolved = [System.IO.Path]::GetFullPath($Path)
  if ($resolved -match '^([A-Za-z]):\\(.*)$') {
    $drive = $matches[1].ToLowerInvariant()
    $rest = $matches[2] -replace '\\','/'
    return "/mnt/$drive/$rest"
  }
  return ($resolved -replace '\\','/')
}

function Redact-Text {
  param([string]$Text)
  if ($null -eq $Text) { return "" }
  $redacted = $Text
  foreach ($name in @("CURSOR_API_KEY","AWS_ACCESS_KEY_ID","AWS_SECRET_ACCESS_KEY","AWS_SESSION_TOKEN","GITHUB_TOKEN","GH_TOKEN","CIVITAI_API_KEY")) {
    $value = [Environment]::GetEnvironmentVariable($name, "Process")
    if (-not [string]::IsNullOrWhiteSpace($value)) {
      $redacted = $redacted.Replace($value, "***REDACTED_$name***")
    }
  }
  $redacted = $redacted -replace '(?i)(api[_-]?key|token|secret)(\s*[:=]\s*)([^\s"'']{8,})', '$1$2***REDACTED***'
  return $redacted
}

function Quote-ProcessArgument {
  param([string]$Arg)
  if ($null -eq $Arg) { return '""' }
  if ($Arg -notmatch '[\s"]') { return $Arg }
  return '"' + ($Arg -replace '\\','\\' -replace '"','\"') + '"'
}

function Invoke-WslCommandCapture {
  param(
    [Parameter(Mandatory=$true)][string]$Distribution,
    [Parameter(Mandatory=$true)][string[]]$Command,
    [int]$TimeoutMilliseconds = 15000
  )
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = "wsl.exe"
  $psi.Arguments = ((@("-d", $Distribution, "--") + $Command | ForEach-Object { Quote-ProcessArgument $_ }) -join " ")
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.UseShellExecute = $false
  $proc = New-Object System.Diagnostics.Process
  $proc.StartInfo = $psi
  [void]$proc.Start()
  $stdoutTask = $proc.StandardOutput.ReadToEndAsync()
  $stderrTask = $proc.StandardError.ReadToEndAsync()
  if (-not $proc.WaitForExit($TimeoutMilliseconds)) {
    try { & taskkill.exe /PID $proc.Id /T /F | Out-Null } catch { try { $proc.Kill() } catch { } }
    try { [void]$proc.WaitForExit(5000) } catch { }
    return [pscustomobject]@{ exit_code = -1; stdout = ""; stderr = "WSL capability probe timed out after $TimeoutMilliseconds ms." }
  }
  try { $proc.WaitForExit() } catch { }
  return [pscustomobject]@{
    exit_code = $proc.ExitCode
    stdout = $stdoutTask.Result
    stderr = $stderrTask.Result
  }
}

function Get-RegisteredGitWorktreeRoots {
  param([Parameter(Mandatory=$true)][string]$RepoRoot)
  $repoFull = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd('\')
  $output = @(& git.exe -C $repoFull worktree list --porcelain 2>&1)
  if ($LASTEXITCODE -ne 0) {
    throw "Unable to enumerate registered Git worktrees for ${repoFull}: $($output -join ' ')"
  }
  $roots = @(
    $output |
      ForEach-Object { [string]$_ } |
      Where-Object { $_.StartsWith("worktree ", [System.StringComparison]::Ordinal) } |
      ForEach-Object { [System.IO.Path]::GetFullPath($_.Substring(9)).TrimEnd('\') }
  )
  if ($roots.Count -lt 1) { throw "Git reported no registered worktrees for $repoFull" }
  return $roots
}

function Resolve-CursorCredentialRoot {
  param(
    [Parameter(Mandatory=$true)][string]$RepoRoot,
    [string]$RequestedCredentialRoot = ""
  )
  $repoFull = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd('\')
  $registeredRoots = @(Get-RegisteredGitWorktreeRoots -RepoRoot $repoFull)
  $projectRegistered = @($registeredRoots | Where-Object {
    $_.Equals($repoFull, [System.StringComparison]::OrdinalIgnoreCase)
  }).Count -eq 1
  if (-not $projectRegistered) {
    throw "Cursor ProjectRoot is not a registered worktree of the repository: $repoFull"
  }

  # Git lists the primary worktree first. Credentials remain anchored there while
  # Cursor's filesystem workspace stays on the requested registered worktree.
  $primaryRoot = $registeredRoots[0]
  $candidateRoot = if ([string]::IsNullOrWhiteSpace($RequestedCredentialRoot)) {
    $primaryRoot
  } else {
    [System.IO.Path]::GetFullPath($RequestedCredentialRoot).TrimEnd('\')
  }
  if (-not $candidateRoot.Equals($primaryRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "CredentialRoot must be the repository primary worktree '$primaryRoot'; received '$candidateRoot'."
  }
  if (-not (Test-Path -LiteralPath $candidateRoot -PathType Container)) {
    throw "Trusted primary credential root is missing: $candidateRoot"
  }
  return [pscustomobject]@{
    project_root = $repoFull
    credential_root = $candidateRoot
    primary_worktree_root = $primaryRoot
    registered_worktree_count = $registeredRoots.Count
    project_is_primary_worktree = $repoFull.Equals($primaryRoot, [System.StringComparison]::OrdinalIgnoreCase)
  }
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
      $lockItem = Get-Item -LiteralPath $Path
      $ownerAlive = $true
      try {
        $existing = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json -ErrorAction Stop
        $ownerAlive = $null -ne (Get-Process -Id ([int]$existing.pid) -ErrorAction SilentlyContinue)
      } catch { $ownerAlive = $false }
      if (((Get-Date) - $lockItem.LastWriteTime).TotalMinutes -ge $StaleMinutes -or -not $ownerAlive) {
        Remove-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
        $staleRemoved = $true
      }
    }
    try {
      $bytes = [System.Text.Encoding]::UTF8.GetBytes(($Payload | ConvertTo-Json -Compress))
      $stream = [System.IO.File]::Open($Path, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
      try { $stream.Write($bytes, 0, $bytes.Length) } finally { $stream.Dispose() }
      $wait.Stop()
      return [pscustomobject]@{ acquired = $true; waited_ms = $wait.ElapsedMilliseconds; stale_lock_removed = $staleRemoved }
    } catch [System.IO.IOException] {
      if ($wait.Elapsed.TotalSeconds -ge $WaitSeconds) {
        $wait.Stop()
        throw "CURSOR_HANDOFF_LOCK_WAIT_TIMEOUT: Cursor lock remained busy for $WaitSeconds seconds."
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

function Test-RequestsProjectExecution {
  param([string]$Text)
  foreach ($line in @(([string]$Text) -split "`r?`n")) {
    $trimmed = $line.Trim()
    if ($trimmed -match '(?i)\b(do not|must not|never|without|forbid(?:den)?|prohibit(?:ed)?|no)\b.{0,40}\b(run|execute|invoke|rerun)\b') { continue }
    if ($trimmed -match '(?i)^(?:[-*]\s*)?(?:(?:please|you\s+(?:should|must|need\s+to)|the\s+worker\s+(?:should|must))\s+)?(run|rerun|execute|invoke)\b.{0,120}\b(script|test|tests|validator|generator|audit|\.py|\.ps1)\b') { return $true }
  }
  return $false
}

function Expand-DelimitedPathList {
  param([string[]]$Values)
  $expanded = New-Object 'System.Collections.Generic.List[string]'
  foreach ($value in @($Values)) {
    if ([string]::IsNullOrWhiteSpace($value)) { continue }
    foreach ($part in [regex]::Split($value, '[,|;\r\n]+')) {
      $trimmed = $part.Trim().Trim('"').Trim("'")
      if (-not [string]::IsNullOrWhiteSpace($trimmed)) { $expanded.Add($trimmed) }
    }
  }
  return @($expanded | Select-Object -Unique)
}

function Test-MalformedRepoPath {
  param([string]$Path)
  if ([string]::IsNullOrWhiteSpace($Path)) { return $true }
  if ($Path -match '[\u0000-\u001F\u007F\uE000-\uF8FF]') { return $true }
  if ($Path -match ':') { return $true }
  $segments = @((($Path -replace '\\','/') -split '/') | Where-Object { $_ -ne '' })
  return ($segments -contains '..')
}

function Normalize-GitRepoPath {
  param([Parameter(Mandatory=$true)][string]$Path)
  $normalized = ($Path -replace '\\','/')
  while ($normalized.StartsWith('./')) { $normalized = $normalized.Substring(2) }
  $normalized = $normalized.TrimStart('/')
  if (Test-MalformedRepoPath $normalized) { throw "Git returned a malformed repository path: $Path" }
  return $normalized
}

function ConvertFrom-GitPorcelainZBytes {
  param([byte[]]$Bytes)
  $paths = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
  if ($null -eq $Bytes -or $Bytes.Length -eq 0) { return ,$paths }
  $raw = [System.Text.Encoding]::UTF8.GetString($Bytes)
  $entries = @($raw.Split([char]0, [System.StringSplitOptions]::RemoveEmptyEntries))
  for ($i = 0; $i -lt $entries.Count; $i++) {
    $entry = $entries[$i]
    if ($entry.Length -lt 4) { continue }
    $status = $entry.Substring(0, 2)
    $path = Normalize-GitRepoPath -Path $entry.Substring(3)
    [void]$paths.Add($path)
    if ($status -match '[RC]' -and ($i + 1) -lt $entries.Count) { $i++ }
  }
  return ,$paths
}

function Invoke-NativeByteCapture {
  param(
    [Parameter(Mandatory=$true)][string]$FileName,
    [Parameter(Mandatory=$true)][string[]]$Arguments
  )
  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = $FileName
  $psi.Arguments = (($Arguments | ForEach-Object { Quote-ProcessArgument $_ }) -join ' ')
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.UseShellExecute = $false
  $proc = New-Object System.Diagnostics.Process
  $proc.StartInfo = $psi
  [void]$proc.Start()
  $stderrTask = $proc.StandardError.ReadToEndAsync()
  $memory = New-Object System.IO.MemoryStream
  try {
    $proc.StandardOutput.BaseStream.CopyTo($memory)
    $proc.WaitForExit()
    return [pscustomobject]@{
      exit_code = $proc.ExitCode
      stdout_bytes = $memory.ToArray()
      stderr = $stderrTask.Result
    }
  } finally {
    $memory.Dispose()
    $proc.Dispose()
  }
}

function ConvertTo-RepoRelativePath {
  param(
    [Parameter(Mandatory=$true)][string]$BasePath,
    [Parameter(Mandatory=$true)][string]$Path
  )
  $baseFull = [System.IO.Path]::GetFullPath($BasePath).TrimEnd('\')
  $pathFull = [System.IO.Path]::GetFullPath($Path)
  if (-not $pathFull.StartsWith($baseFull + '\', [System.StringComparison]::OrdinalIgnoreCase) -and
      -not $pathFull.Equals($baseFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Path is outside repository root: $Path"
  }
  $relative = if ($pathFull.Length -eq $baseFull.Length) { "." } else { $pathFull.Substring($baseFull.Length + 1) }
  return ($relative -replace '\\','/')
}

function Test-AllowedRepoPath {
  param(
    [Parameter(Mandatory=$true)][string]$RepoRelativePath,
    [Parameter(Mandatory=$true)][string[]]$AllowedRepoRelativePaths
  )
  $candidate = ($RepoRelativePath -replace '\\','/').TrimStart('/')
  foreach ($allowed in $AllowedRepoRelativePaths) {
    $normalizedAllowed = ($allowed -replace '\\','/').TrimEnd('/')
    if ($candidate -ieq $normalizedAllowed) { return $true }
    if ($candidate.StartsWith($normalizedAllowed + '/', [System.StringComparison]::OrdinalIgnoreCase)) { return $true }
  }
  return $false
}

function Get-GitChangedPathSet {
  param([Parameter(Mandatory=$true)][string]$RepoRoot)
  $result = Invoke-NativeByteCapture -FileName "git.exe" -Arguments @(
    "-C", $RepoRoot, "-c", "core.quotepath=false", "status", "--porcelain=v1", "-z", "--untracked-files=all"
  )
  if ($result.exit_code -ne 0) { throw "git status failed: $($result.stderr.Trim())" }
  return ConvertFrom-GitPorcelainZBytes -Bytes $result.stdout_bytes
}

function Get-Sha256Hex {
  param([Parameter(Mandatory=$true)][byte[]]$Bytes)
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try { return ([System.BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant() }
  finally { $sha.Dispose() }
}

function Get-GitWorktreeSnapshot {
  param([Parameter(Mandatory=$true)][string]$RepoRoot)
  $result = Invoke-NativeByteCapture -FileName "git.exe" -Arguments @(
    "-C", $RepoRoot, "-c", "core.quotepath=false", "status", "--porcelain=v1", "-z", "--untracked-files=all"
  )
  if ($result.exit_code -ne 0) { throw "git status failed: $($result.stderr.Trim())" }
  $paths = ConvertFrom-GitPorcelainZBytes -Bytes $result.stdout_bytes
  $signatures = [ordered]@{}
  foreach ($path in @($paths | Sort-Object)) {
    $full = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $path))
    if (Test-Path -LiteralPath $full -PathType Leaf) {
      $item = Get-Item -LiteralPath $full
      $signatures[$path] = "file:$($item.Length):$((Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant())"
    } elseif (Test-Path -LiteralPath $full -PathType Container) {
      $signatures[$path] = "directory"
    } else {
      $signatures[$path] = "missing"
    }
  }
  $statusHash = Get-Sha256Hex -Bytes $result.stdout_bytes
  $headResult = Invoke-NativeByteCapture -FileName "git.exe" -Arguments @("-C", $RepoRoot, "rev-parse", "HEAD")
  if ($headResult.exit_code -ne 0) { throw "git rev-parse HEAD failed: $($headResult.stderr.Trim())" }
  $head = [System.Text.Encoding]::UTF8.GetString($headResult.stdout_bytes).Trim()
  $fingerprintText = "head=$head`nstatus=$statusHash`n" + (($signatures.Keys | ForEach-Object { "$_=$($signatures[$_])" }) -join "`n")
  return [pscustomobject]@{
    fingerprint = Get-Sha256Hex -Bytes ([System.Text.Encoding]::UTF8.GetBytes($fingerprintText))
    status_hash = $statusHash
    head = $head
    signatures = $signatures
  }
}

function Compare-GitWorktreeSnapshots {
  param(
    [Parameter(Mandatory=$true)]$Before,
    [Parameter(Mandatory=$true)]$After
  )
  $allPaths = @($Before.signatures.Keys + $After.signatures.Keys | Select-Object -Unique | Sort-Object)
  $changed = @()
  foreach ($path in $allPaths) {
    $beforeValue = if ($Before.signatures.Contains($path)) { [string]$Before.signatures[$path] } else { "<absent>" }
    $afterValue = if ($After.signatures.Contains($path)) { [string]$After.signatures[$path] } else { "<absent>" }
    if ($beforeValue -cne $afterValue) { $changed += $path }
  }
  if ($changed.Count -eq 0 -and $Before.status_hash -cne $After.status_hash) { $changed += "<git-index-or-status-metadata>" }
  if ($Before.head -cne $After.head) { $changed += "<git-head>" }
  return @($changed)
}

function Read-ValidatedScopePacket {
  param(
    [Parameter(Mandatory=$true)][string]$PacketPath,
    [Parameter(Mandatory=$true)][string]$RepoRoot,
    [Parameter(Mandatory=$true)][string[]]$PacketRoots,
    [Parameter(Mandatory=$true)][long]$ScopeByteLimit
  )
  $packetFull = [System.IO.Path]::GetFullPath($PacketPath)
  $repoFull = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd('\')
  $allowedPacketRoots = @($PacketRoots | ForEach-Object {
    [System.IO.Path]::GetFullPath((Join-Path $_ "runtime_artifacts\agent_handoffs\scope_packets")).TrimEnd('\')
  } | Select-Object -Unique)
  $packetRootAllowed = @($allowedPacketRoots | Where-Object {
    $packetFull.StartsWith($_ + '\', [System.StringComparison]::OrdinalIgnoreCase)
  }).Count -gt 0
  if (-not $packetRootAllowed) {
    throw "Scope packet must be inside a trusted project or primary-worktree scope-packet directory: $PacketPath"
  }
  if (-not (Test-Path -LiteralPath $packetFull -PathType Leaf)) { throw "Scope packet missing: $packetFull" }
  $packet = Get-Content -LiteralPath $packetFull -Raw | ConvertFrom-Json -ErrorAction Stop
  if ($packet.artifact_type -ne "ai_worker_scope_packet" -or $packet.status -ne "ready") {
    throw "Invalid scope packet contract: $packetFull"
  }
  $workerLane = [string]$packet.worker_lane
  $gate = [string]$packet.gate
  if ($workerLane -notin @("Cursor", "GitGitHub")) {
    throw "Cursor scope packet worker_lane must be Cursor or GitGitHub: $workerLane"
  }
  if (($gate -eq "CURSOR_FIRST_REQUIRED" -and $workerLane -ne "Cursor") -or ($gate -eq "GIT_GITHUB_WORKER_ANALYSIS_REQUIRED" -and $workerLane -ne "GitGitHub")) {
    throw "Cursor scope packet gate/lane mismatch: gate=$gate worker_lane=$workerLane"
  }
  if ($gate -notin @("CURSOR_FIRST_REQUIRED", "GIT_GITHUB_WORKER_ANALYSIS_REQUIRED")) {
    throw "Cursor scope packet uses an unsupported routing gate: $gate"
  }
  $files = @($packet.files)
  if ($files.Count -lt 1 -or $files.Count -gt 12 -or [int]$packet.candidate_count -ne $files.Count) {
    throw "Scope packet must contain 1-12 exact files: $packetFull"
  }
  [long]$totalBytes = 0
  foreach ($file in $files) {
    $relative = Normalize-GitRepoPath -Path ([string]$file.path)
    $full = [System.IO.Path]::GetFullPath((Join-Path $repoFull $relative))
    if (-not $full.StartsWith($repoFull + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
      throw "Scope packet file is outside repository root: $relative"
    }
    if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { throw "Scope packet file missing: $relative" }
    $actualLength = (Get-Item -LiteralPath $full).Length
    if ($null -eq $file.bytes -or [long]$file.bytes -ne $actualLength) { throw "Scope packet byte length drifted: $relative" }
    $actualHash = (Get-FileHash -LiteralPath $full -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne ([string]$file.sha256).ToLowerInvariant()) { throw "Scope packet hash drifted: $relative" }
    $totalBytes += $actualLength
  }
  if ($null -eq $packet.total_bytes -or [long]$packet.total_bytes -ne $totalBytes) { throw "Scope packet aggregate byte count drifted: $packetFull" }
  if ($totalBytes -gt $ScopeByteLimit) { throw "Cursor scope packet exceeds MaxScopeBytes=${ScopeByteLimit}: $totalBytes bytes" }
  return [pscustomobject]@{ full_path = $packetFull; packet = $packet; files = $files; total_bytes = $totalBytes; worker_lane = $workerLane; gate = $gate }
}

function Get-WorkerReportedStatus {
  param([string]$Text)
  if ([string]::IsNullOrWhiteSpace($Text)) { return "" }
  $match = [regex]::Match($Text, '(?im)^\s*(?:[-*]\s*)?\*{0,2}status\s*:\*{0,2}\s*([^\r\n]+)')
  if (-not $match.Success) { return "" }
  return $match.Groups[1].Value.Trim().Trim('*').Trim().ToLowerInvariant()
}

function Get-WorkerReportedConfidence {
  param([string]$Text)
  if ([string]::IsNullOrWhiteSpace($Text)) { return "" }
  $match = [regex]::Match($Text, '(?im)^\s*(?:[-*]\s*)?\*{0,2}confidence\s*:\*{0,2}\s*([^\r\n]+)')
  if (-not $match.Success) { return "" }
  return $match.Groups[1].Value.Trim().Trim('*').Trim().ToLowerInvariant()
}

function Repair-AbandonedCursorRecords {
  param(
    [Parameter(Mandatory=$true)][string]$HandoffRoot,
    [int]$GraceMinutes = 5
  )
  if (-not (Test-Path -LiteralPath $HandoffRoot -PathType Container)) { return @() }
  $repaired = @()
  foreach ($dir in Get-ChildItem -LiteralPath $HandoffRoot -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 25) {
    $path = Join-Path $dir.FullName "handoff_record.json"
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { continue }
    try { $item = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json -ErrorAction Stop } catch { continue }
    if ($item.status -ne "IN_PROGRESS") { continue }
    $startedAt = try { [DateTimeOffset]::Parse([string]$item.started_at) } catch { [DateTimeOffset]$dir.LastWriteTime }
    if ([DateTimeOffset]::Now.Subtract($startedAt).TotalMinutes -lt $GraceMinutes -and [string]::IsNullOrWhiteSpace([string]$item.finalized_at)) { continue }
    $item.status = "FAIL"
    $item.classification = "CURSOR_HANDOFF_INTERRUPTED"
    $issues = @($item.issues)
    $issues += "Reconciled abandoned IN_PROGRESS record after the worker lock/process ended."
    $item.issues = $issues
    $item.finalized_at = [DateTimeOffset]::Now.ToString("o")
    $item | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $path -Encoding UTF8
    $repaired += $path
  }
  return $repaired
}

function Test-GitLfsTask {
  param(
    [string]$Name,
    [string]$Text,
    [bool]$ExplicitRequirement,
    [string]$EvidencePath
  )
  if ($ExplicitRequirement -or -not [string]::IsNullOrWhiteSpace($EvidencePath)) { return $true }
  return (($Name + "`n" + $Text) -match '(?i)\b(git[ -]?lfs|lfs-managed|lfs tracked|\.gitattributes)\b')
}

function Read-GitLfsEvidence {
  param(
    [Parameter(Mandatory=$true)][string]$Path,
    [Parameter(Mandatory=$true)][string]$RepoRoot
  )
  $full = [System.IO.Path]::GetFullPath($Path)
  $repoFull = [System.IO.Path]::GetFullPath($RepoRoot).TrimEnd('\')
  if (-not $full.StartsWith($repoFull + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Git LFS evidence must be inside the repository runtime evidence tree: $Path"
  }
  if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { throw "Git LFS evidence is missing: $full" }
  $evidence = Get-Content -LiteralPath $full -Raw | ConvertFrom-Json -ErrorAction Stop
  if ($evidence.artifact_type -ne "git_lfs_read_only_evidence" -or $evidence.status -ne "PASS") {
    throw "Invalid Git LFS evidence contract: $full"
  }
  if ([System.IO.Path]::GetFullPath([string]$evidence.project_root) -ne $repoFull) {
    throw "Git LFS evidence project root does not match the handoff project: $full"
  }
  if ([string]::IsNullOrWhiteSpace([string]$evidence.git_lfs_version)) {
    throw "Git LFS evidence has no Windows Git LFS version: $full"
  }
  return [pscustomobject]@{ full_path = $full; evidence = $evidence }
}

if ($SelfTest) {
  $sample = " M file one.txt$([char]0)?? new.txt$([char]0)R  renamed.txt$([char]0)old.txt$([char]0)"
  $parsed = ConvertFrom-GitPorcelainZBytes -Bytes ([System.Text.Encoding]::UTF8.GetBytes($sample))
  $expanded = @(Expand-DelimitedPathList -Values @("alpha.ps1,beta.ps1|gamma.ps1"))
  $credentialResolution = $null
  $credentialResolutionError = ""
  try {
    $credentialResolution = Resolve-CursorCredentialRoot -RepoRoot $ProjectRoot -RequestedCredentialRoot $CredentialRoot
  } catch {
    $credentialResolutionError = $_.Exception.Message
  }
  $untrustedCredentialRootRejected = $false
  if ($null -ne $credentialResolution) {
    try {
      $invalidCredentialRoot = Join-Path $credentialResolution.credential_root ".cursor-untrusted-credential-root-probe"
      $null = Resolve-CursorCredentialRoot -RepoRoot $ProjectRoot -RequestedCredentialRoot $invalidCredentialRoot
    } catch {
      $untrustedCredentialRootRejected = $_.Exception.Message -match '^CredentialRoot must be the repository primary worktree'
    }
  }
  $checks = [ordered]@{
    delimited_paths_normalized = ($expanded.Count -eq 3)
    nul_git_paths_preserved = ($parsed.Contains("file one.txt") -and $parsed.Contains("new.txt") -and $parsed.Contains("renamed.txt"))
    rename_source_not_misattributed = (-not $parsed.Contains("old.txt"))
    malformed_private_use_path_rejected = (Test-MalformedRepoPath "C$([char]0xF03A)$([char]0xF05C)Comfy_UI_Main")
    dirty_file_content_change_detected = $false
    fast_model_name_detected = ("gpt-5.3-codex-low-fast" -match '(?i)-fast(?:$|\b)')
    git_lfs_task_detected = (Test-GitLfsTask -Name "checkpoint_git_lfs_grouping" -Text "Group LFS-managed paths." -ExplicitRequirement $false -EvidencePath "")
    plain_status_parsed = ((Get-WorkerReportedStatus -Text "status: pass") -eq "pass")
    blocked_status_parsed = ((Get-WorkerReportedStatus -Text "- **status:** blocked") -eq "blocked")
    exact_confidence_parsed = ((Get-WorkerReportedConfidence -Text "confidence: medium") -eq "medium")
    confirmed_status_normalized = ((Normalize-WorkerStatus -Status "confirmed") -eq "pass")
    pass_with_findings_normalized = ((Normalize-WorkerStatus -Status "pass_with_medium_finding") -eq "pass_with_findings")
    verified_blocked_normalized = ((Normalize-WorkerStatus -Status "verified_blocked_as_intended") -eq "blocked")
    compound_confidence_normalized = ((Normalize-WorkerConfidence -Confidence "medium-high") -eq "medium")
    negated_execution_not_rejected = (-not (Test-RequestsProjectExecution -Text "Do not execute project scripts or tests."))
    explicit_execution_detected = (Test-RequestsProjectExecution -Text "Run the exact validator test.ps1.")
    polite_execution_detected = (Test-RequestsProjectExecution -Text "Please run the exact tests.")
    credential_primary_worktree_resolved = ($null -ne $credentialResolution)
    credential_project_root_remains_requested = ($null -ne $credentialResolution -and $credentialResolution.project_root.Equals([System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\'), [System.StringComparison]::OrdinalIgnoreCase))
    credential_root_is_primary_worktree = ($null -ne $credentialResolution -and $credentialResolution.credential_root.Equals($credentialResolution.primary_worktree_root, [System.StringComparison]::OrdinalIgnoreCase))
    untrusted_credential_root_rejected = $untrustedCredentialRootRejected
  }
  $beforeTest = [pscustomobject]@{ status_hash = "same"; signatures = [ordered]@{ "dirty.txt" = "file:1:aaa" } }
  $afterTest = [pscustomobject]@{ status_hash = "same"; signatures = [ordered]@{ "dirty.txt" = "file:1:bbb" } }
  $checks.dirty_file_content_change_detected = (@(Compare-GitWorktreeSnapshots -Before $beforeTest -After $afterTest) -contains "dirty.txt")
  [ordered]@{
    status = $(if (($checks.Values | Where-Object { -not $_ }).Count -eq 0) { "PASS" } else { "FAIL" })
    project_root = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\')
    credential_root = $(if ($null -ne $credentialResolution) { $credentialResolution.credential_root } else { $null })
    credential_resolution_error = $credentialResolutionError
    checks = $checks
  } |
    ConvertTo-Json -Depth 6
  return
}

$projectRootFull = [System.IO.Path]::GetFullPath($ProjectRoot)
$externalRoot = "C:\Users\kevin\.codex\cursor_handoff"
$lockPath = Join-Path $externalRoot "cursor_agent.lock"
$handoffRoot = Join-Path $projectRootFull "runtime_artifacts\agent_handoffs\cursor"
$AllowedPaths = @(Expand-DelimitedPathList -Values $AllowedPaths)
$DeclaredReadOnlyCommands = @($DeclaredReadOnlyCommands | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { $_.Trim() } | Select-Object -Unique)
$DeclaredAgentCommands = @($DeclaredAgentCommands | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { $_.Trim() } | Select-Object -Unique)
$repairedInterruptedRecords = if (-not (Test-Path -LiteralPath $lockPath)) {
  @(Repair-AbandonedCursorRecords -HandoffRoot $handoffRoot -GraceMinutes $InterruptedRecordGraceMinutes)
} else { @() }
$timestamp = (Get-Date -Format "yyyyMMddTHHmmsszzz") -replace ':',''
$safeTaskName = ($TaskName -replace '[^A-Za-z0-9_.-]+','_').Trim('_')
if ([string]::IsNullOrWhiteSpace($safeTaskName)) { $safeTaskName = "cursor_task" }
$runDir = Join-Path $projectRootFull ("runtime_artifacts\agent_handoffs\cursor\{0}_{1}" -f $timestamp,$safeTaskName)
New-Item -ItemType Directory -Force -Path $runDir | Out-Null

$recordPath = Join-Path $runDir "handoff_record.json"
  $record = [ordered]@{
  schema_version = 2
  task_name = $TaskName
  mode = $Mode
  requested_cursor_model = $CursorModel
  wsl_distribution = $WslDistribution
  git_lfs_requirement_declared = [bool]$RequireGitLfs
  git_lfs_evidence_path = $GitLfsEvidencePath
  allow_writes = [bool]$AllowWrites
  allow_read_only_command_execution = [bool]$AllowReadOnlyCommandExecution
  declared_read_only_commands = @($DeclaredReadOnlyCommands)
  declared_agent_commands = @($DeclaredAgentCommands)
  allow_broad_discovery = [bool]$AllowBroadDiscovery
  broad_discovery_reason = $BroadDiscoveryReason
  max_scope_bytes = $MaxScopeBytes
  scope_byte_budget_reason = $ScopeByteBudgetReason
  force_cursor_commands = [bool]$ForceCursorCommands
  require_output_contract = $true
  started_at = (Get-Date).ToString("o")
  project_root = $projectRootFull
  requested_credential_root = $CredentialRoot
  run_dir = $runDir
  status = "IN_PROGRESS"
  classification = "CURSOR_HANDOFF_IN_PROGRESS"
  cursor_agent_path = $CursorAgentPath
  timeout_seconds = $TimeoutSeconds
  stale_lock_minutes = $StaleLockMinutes
  lock_wait_seconds = $LockWaitSeconds
  lock_poll_seconds = $LockPollSeconds
  allowed_paths = @($AllowedPaths)
  forbidden_actions = @($ForbiddenActions)
  output_json_path = Join-Path $runDir "cursor_stdout.json"
  stderr_path = Join-Path $runDir "cursor_stderr.txt"
  work_order_path = Join-Path $runDir "work_order.md"
  issues = @()
  warnings = @()
}
if ($repairedInterruptedRecords.Count -gt 0) {
  $record.repaired_interrupted_records = @($repairedInterruptedRecords)
  $record.issues += "Reconciled $($repairedInterruptedRecords.Count) abandoned Cursor handoff record(s)."
}

try {
  $lockPayload = [ordered]@{
    pid = $PID
    task_name = $TaskName
    created_at = (Get-Date).ToString("o")
    run_dir = $runDir
  }
  $lockResult = Enter-BoundedHandoffLock -Path $lockPath -Payload $lockPayload -WaitSeconds $LockWaitSeconds -PollSeconds $LockPollSeconds -StaleMinutes $StaleLockMinutes
  $record.lock_waited_ms = $lockResult.waited_ms
  $record.lock_stale_removed = $lockResult.stale_lock_removed
} catch {
  $record.status = "BLOCKED"
  $record.classification = "CURSOR_HANDOFF_LOCK_WAIT_TIMEOUT"
  $record.issues += $_.Exception.Message
  $record.finalized_at = (Get-Date).ToString("o")
  $record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $recordPath -Encoding UTF8
  throw
}

try {
  $allowedFullPaths = @()
  $allowedRepoRelativePaths = @()
  $credentialResolution = Resolve-CursorCredentialRoot -RepoRoot $projectRootFull -RequestedCredentialRoot $CredentialRoot
  $credentialRootFull = $credentialResolution.credential_root
  $record.credential_root = $credentialRootFull
  $record.credential_root_relation = "PRIMARY_WORKTREE_FOR_PROJECT"
  $record.registered_worktree_count = $credentialResolution.registered_worktree_count
  $record.project_is_primary_worktree = $credentialResolution.project_is_primary_worktree
  $record.isolated_worktree_required = (-not $AllowPrimaryWorktree)
  if ($credentialResolution.project_is_primary_worktree -and -not $AllowPrimaryWorktree) {
    throw "CURSOR_ISOLATED_WORKTREE_REQUIRED: substantive Cursor handoffs must run in a registered linked worktree. Use -AllowPrimaryWorktree only for an explicit transport/health probe."
  }
  $cursorKey = [Environment]::GetEnvironmentVariable("CURSOR_API_KEY", "Process")
  if ([string]::IsNullOrWhiteSpace($cursorKey)) {
    $envLoader = Join-Path $credentialRootFull "Plan\Instructions\Operations\Scripts\Load-ComfyEnv.ps1"
    if (-not (Test-Path -LiteralPath $envLoader -PathType Leaf)) {
      throw "Trusted Cursor credential loader is missing: $envLoader"
    }
    $record.credential_loader_path = $envLoader
    $record.credential_loader_sha256 = (Get-FileHash -LiteralPath $envLoader -Algorithm SHA256).Hash.ToLowerInvariant()
    . $envLoader -ProjectRoot $credentialRootFull -Quiet
    $cursorKey = [Environment]::GetEnvironmentVariable("CURSOR_API_KEY", "Process")
    $record.cursor_credential_source = "PRIMARY_WORKTREE_ENV_LOADER"
  } else {
    $record.cursor_credential_source = "PROCESS_ENVIRONMENT"
  }
  if ([string]::IsNullOrWhiteSpace($cursorKey)) {
    throw "CURSOR_API_KEY is not loaded from the process environment or trusted primary worktree '$credentialRootFull'."
  }
  $record.cursor_credential_available = $true

  $sourceText = ""
  if (-not [string]::IsNullOrWhiteSpace($WorkOrderPath)) { $sourceText = Get-Content -LiteralPath $WorkOrderPath -Raw }
  if (-not [string]::IsNullOrWhiteSpace($WorkOrderText)) {
    if (-not [string]::IsNullOrWhiteSpace($sourceText)) { $sourceText += "`n`n" }
    $sourceText += $WorkOrderText
  }
  if ([string]::IsNullOrWhiteSpace($sourceText)) { throw "Provide -WorkOrderText or -WorkOrderPath." }
  if ($MaxScopeBytes -gt 524288 -and [string]::IsNullOrWhiteSpace($ScopeByteBudgetReason)) {
    throw "A scope budget above 524288 bytes requires -ScopeByteBudgetReason."
  }

  $gitLfsTask = Test-GitLfsTask -Name $TaskName -Text $sourceText -ExplicitRequirement ([bool]$RequireGitLfs) -EvidencePath $GitLfsEvidencePath
  $record.git_lfs_capability_required = [bool]$gitLfsTask
  $gitLfsEvidence = $null
  if (-not [string]::IsNullOrWhiteSpace($GitLfsEvidencePath)) {
    $gitLfsEvidence = Read-GitLfsEvidence -Path $GitLfsEvidencePath -RepoRoot $projectRootFull
    $record.git_lfs_evidence_path = $gitLfsEvidence.full_path
    $record.git_lfs_evidence_sha256 = (Get-FileHash -LiteralPath $gitLfsEvidence.full_path -Algorithm SHA256).Hash.ToLowerInvariant()
  }
  if ($gitLfsTask) {
    $gitLfsProbe = Invoke-WslCommandCapture -Distribution $WslDistribution -Command @("git", "lfs", "version")
    $gitLfsProbeExitCode = $gitLfsProbe.exit_code
    $gitLfsProbeText = (Redact-Text ((@($gitLfsProbe.stdout, $gitLfsProbe.stderr) -join "`n").Trim()))
    $record.git_lfs_wsl_probe_exit_code = $gitLfsProbeExitCode
    $record.git_lfs_wsl_version = $gitLfsProbeText
    if ($gitLfsProbeExitCode -eq 0 -and $gitLfsProbeText -match '(?i)^git-lfs/') {
      $record.git_lfs_capability_status = "AVAILABLE"
      $record.git_lfs_analysis_route = "CURSOR_WSL_NATIVE_GIT_LFS"
    } elseif ($null -ne $gitLfsEvidence) {
      $record.git_lfs_capability_status = "GAP_BRIDGED"
      $record.git_lfs_capability_classification = "CURSOR_ENVIRONMENT_CAPABILITY_GAP_GIT_LFS"
      $record.git_lfs_analysis_route = "WINDOWS_READ_ONLY_GIT_LFS_EVIDENCE_BRIDGE"
      $record.issues += "Cursor WSL Git LFS is unavailable; using hash-recorded Windows read-only Git LFS evidence."
    } else {
      $record.status = "BLOCKED"
      $record.classification = "CURSOR_ENVIRONMENT_CAPABILITY_GAP_GIT_LFS"
      $record.git_lfs_capability_status = "MISSING"
      $record.git_lfs_analysis_route = "BLOCKED_NO_GIT_LFS_CAPABILITY"
      $record.issues += "Git/LFS analysis requires Git LFS in $WslDistribution or a validated -GitLfsEvidencePath. Probe: $gitLfsProbeText"
      throw "CURSOR_ENVIRONMENT_CAPABILITY_GAP_GIT_LFS: install Git LFS in $WslDistribution or supply Windows read-only evidence."
    }
  } else {
    $record.git_lfs_capability_status = "NOT_REQUIRED"
    $record.git_lfs_analysis_route = "NOT_APPLICABLE"
  }

  $scopePacket = $null
  if (-not [string]::IsNullOrWhiteSpace($ScopePacketPath)) {
    $scopePacket = Read-ValidatedScopePacket -PacketPath $ScopePacketPath -RepoRoot $projectRootFull -PacketRoots @($projectRootFull,$credentialRootFull) -ScopeByteLimit $MaxScopeBytes
    $record.scope_packet_path = $scopePacket.full_path
    $record.scope_packet_candidate_count = $scopePacket.files.Count
    $record.scope_packet_total_bytes = $scopePacket.total_bytes
    $record.scope_packet_worker_lane = $scopePacket.worker_lane
    $record.scope_packet_gate = $scopePacket.gate
    $record.scope_packet_validated = $true
  }
  $broadPattern = '(?i)\b(broad|whole[- ]tree|repository[- ]wide|project[- ]wide|reconcil\w*|inventory|all files|all directories|scan (the )?(repository|project|tree))\b'
  $looksBroad = (($TaskName + "`n" + $sourceText) -match $broadPattern)
  if ($looksBroad -and $null -eq $scopePacket -and -not $AllowBroadDiscovery) {
    throw "Broad worker discovery requires -ScopePacketPath or explicit -AllowBroadDiscovery with -BroadDiscoveryReason."
  }
  if ($AllowBroadDiscovery -and [string]::IsNullOrWhiteSpace($BroadDiscoveryReason)) {
    throw "-AllowBroadDiscovery requires a non-empty -BroadDiscoveryReason."
  }
  if ($TimeoutSeconds -gt 600 -and -not $AllowBroadDiscovery) {
    throw "TimeoutSeconds above 600 requires an explicit broad-discovery exception."
  }
  if ($AllowReadOnlyCommandExecution -and $Mode -eq "agent") { throw "-AllowReadOnlyCommandExecution is only valid with ask/plan mode." }
  if ($DeclaredReadOnlyCommands.Count -gt 0 -and -not $AllowReadOnlyCommandExecution) {
    throw "-DeclaredReadOnlyCommands requires -AllowReadOnlyCommandExecution."
  }
  if ($AllowReadOnlyCommandExecution -and $DeclaredReadOnlyCommands.Count -eq 0) {
    throw "-AllowReadOnlyCommandExecution requires at least one exact -DeclaredReadOnlyCommands entry."
  }
  if ($Mode -in @("ask", "plan") -and (Test-RequestsProjectExecution -Text $sourceText) -and -not $AllowReadOnlyCommandExecution) {
    throw "Ask/plan work orders may not execute project scripts, tests, validators, generators, or audits unless explicitly declared side-effect-free."
  }
  if ($DeclaredAgentCommands.Count -gt 0 -and $Mode -ne "agent") { throw "-DeclaredAgentCommands requires -Mode agent." }
  if ($Mode -eq "agent") {
    if (-not $AllowWrites -or $AllowedPaths.Count -eq 0) {
      throw "CURSOR_AGENT_SCOPE_REQUIRED: agent mode requires -AllowWrites and at least one exact -AllowedPaths entry."
    }
    if ($DeclaredAgentCommands.Count -eq 0) {
      throw "CURSOR_AGENT_COMMANDS_REQUIRED: agent mode requires at least one exact -DeclaredAgentCommands entry."
    }
  } elseif ($AllowWrites) {
    throw "-AllowWrites is valid only with -Mode agent."
  }
  if ($ForceCursorCommands) { throw "CURSOR_FORCE_COMMANDS_DIRECT_OVERRIDE_FORBIDDEN: agent mode enables --force only through the guarded wrapper contract." }
  if ($AllowWrites) {
    foreach ($allowedPath in $AllowedPaths) {
      $combined = if ([System.IO.Path]::IsPathRooted($allowedPath)) { $allowedPath } else { Join-Path $projectRootFull $allowedPath }
      $allowedFull = [System.IO.Path]::GetFullPath($combined)
      [void](ConvertTo-RepoRelativePath -BasePath $projectRootFull -Path $allowedFull)
      $allowedFullPaths += $allowedFull
      $allowedRepoRelativePaths += (ConvertTo-RepoRelativePath -BasePath $projectRootFull -Path $allowedFull)
    }
    $record.allowed_full_paths = @($allowedFullPaths)
    $record.allowed_repo_relative_paths = @($allowedRepoRelativePaths)
  }

  $allowedText = if ($AllowedPaths.Count -gt 0) { ($AllowedPaths | ForEach-Object { "- $_" }) -join "`n" } else { "- No project writes allowed unless explicitly named below." }
  $forbiddenText = ($ForbiddenActions | ForEach-Object { "- $_" }) -join "`n"
  $writePolicy = if ($AllowWrites) { "Writes are allowed only inside listed allowed paths and only if the work order explicitly asks for edits." } else { "Do not edit files. Return analysis, plan, or patch suggestions only." }
  $commandPolicy = if ($Mode -eq "agent") {
    "Do not execute project scripts, tests, validators, generators, package managers, or audits. The host command broker runs these exact validators after your edit and records their results:`n" + (($DeclaredAgentCommands | ForEach-Object { "- $_" }) -join "`n")
  } elseif ($AllowReadOnlyCommandExecution) {
    "Only these exact commands are declared side-effect-free and may run:`n" + (($DeclaredReadOnlyCommands | ForEach-Object { "- $_" }) -join "`n")
  } else {
    "Do not execute project scripts, tests, validators, generators, or audits. Limit commands to file reads, rg, sha256sum, and read-only git status/diff/show/log operations."
  }

  $wslProjectRoot = ConvertTo-WslPath $projectRootFull
  $record.cursor_workspace_wsl = $wslProjectRoot
  $scopeText = if ($null -ne $scopePacket) {
    ($scopePacket.files | ForEach-Object { "- $($_.path) sha256=$($_.sha256)" }) -join "`n"
  } elseif ($AllowBroadDiscovery) {
    "- Explicit broad-discovery exception: $BroadDiscoveryReason"
  } else {
    "- No scope packet required because this work order is below broad-discovery threshold."
  }
  $gitLfsText = if ($gitLfsTask) {
    $evidenceLine = if ($null -ne $gitLfsEvidence) { "Windows evidence: $($gitLfsEvidence.full_path) sha256=$($record.git_lfs_evidence_sha256)" } else { "Windows evidence: none" }
    "Required: yes`nCapability status: $($record.git_lfs_capability_status)`nAnalysis route: $($record.git_lfs_analysis_route)`nWSL version/probe: $($record.git_lfs_wsl_version)`n$evidenceLine"
  } else {
    "Required: no"
  }
  $workOrder = @"
# Cursor CLI Work Order: $TaskName

Windows project root: $projectRootFull
WSL project root: $wslProjectRoot
Mode requested by wrapper: $Mode
Write policy: $writePolicy
Command policy: $commandPolicy

## Git LFS Capability
$gitLfsText

If the analysis route is WINDOWS_READ_ONLY_GIT_LFS_EVIDENCE_BRIDGE, consume only the supplied evidence for LFS facts and do not claim native WSL Git LFS execution. Git/LFS mutations remain forbidden in every route.

Use only the WSL project root for filesystem commands. Never treat the Windows drive path as a relative Linux filename and never create a drive-name directory inside the repository.

## Validated Scope
$scopeText

## Allowed Paths
$allowedText

## Forbidden Actions
$forbiddenText
- Read credential stores, including .env, ~/.aws, ~/.config/gh, SSH keys, cloud profiles, browser profiles, or keychains.

## Output Contract
Return a compact final result only. Include status, summary, files inspected, files changed or proposed, commands run, blockers, confidence, and recommended Codex follow-up.
Never print secrets or .env values. If a secret-like value is encountered, redact it.
Your final response must include these exact plain-text labels: status:, summary:, files inspected:, blockers:, confidence:, and recommended Codex follow-up:.
Do not narrate future intentions. Do not answer with "I will inspect", "next I will read", or similar progress text. If you cannot complete the requested inspection within this call, return `status: blocked` with the exact blocker.

## Task
$sourceText
"@
  Set-Content -LiteralPath $record.work_order_path -Value $workOrder -Encoding UTF8

  $wslWorkOrder = ConvertTo-WslPath $record.work_order_path
  $modeArgs = @()
  if ($Mode -eq "ask") { $modeArgs += @("--mode", "ask") }
  elseif ($Mode -eq "plan") { $modeArgs += @("--mode", "plan") }
  $effectiveCursorModel = $CursorModel
  if ([string]::IsNullOrWhiteSpace($effectiveCursorModel)) {
    if ($Mode -eq "agent") { $effectiveCursorModel = $AgentDefaultModel }
    else { $effectiveCursorModel = $AskPlanDefaultModel }
  }
  if ($effectiveCursorModel -match '(?i)-fast(?:$|\b)') {
    throw "Fast Cursor models are prohibited. Use plain gpt-5.3-codex or route semantic synthesis to Claude."
  }
  if ($effectiveCursorModel -ne "gpt-5.3-codex") {
    throw "Only plain gpt-5.3-codex is allowed for delegated Cursor work. Route semantic synthesis to Claude Sonnet 5."
  }
  $record.effective_cursor_model = $effectiveCursorModel
  $modelArgs = @()
  if (-not [string]::IsNullOrWhiteSpace($effectiveCursorModel)) { $modelArgs += @("--model", $effectiveCursorModel) }
  $record.force_cursor_commands = ($Mode -eq "agent")
  $record.auto_force_cursor_commands = ($Mode -eq "agent")
  $forceArgs = if ($Mode -eq "agent") { @("--force") } else { @() }

  $preHandoffSnapshot = Get-GitWorktreeSnapshot -RepoRoot $projectRootFull
  $record.pre_handoff_worktree_fingerprint = $preHandoffSnapshot.fingerprint
  $record.pre_handoff_head = $preHandoffSnapshot.head
  $scopeHashesBefore = [ordered]@{}
  if ($null -ne $scopePacket) {
    foreach ($file in $scopePacket.files) {
      $relative = Normalize-GitRepoPath -Path ([string]$file.path)
      $scopeHashesBefore[$relative] = (Get-FileHash -LiteralPath (Join-Path $projectRootFull $relative) -Algorithm SHA256).Hash.ToLowerInvariant()
    }
  }

  $argList = @(
    "-d", $WslDistribution, "--",
    $CursorAgentPath,
    "--print",
    "--output-format", "json",
    "--trust",
    "--workspace", $wslProjectRoot
  ) + $modeArgs + $modelArgs + $forceArgs + @("WORKORDER:$wslWorkOrder")

  $psi = New-Object System.Diagnostics.ProcessStartInfo
  $psi.FileName = "wsl.exe"
  $psi.Arguments = (($argList | ForEach-Object { Quote-ProcessArgument $_ }) -join " ")
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  $psi.UseShellExecute = $false
  $credentialEnvironmentNames = @(
    "AWS_ACCESS_KEY_ID","AWS_SECRET_ACCESS_KEY","AWS_SESSION_TOKEN","AWS_SECURITY_TOKEN","AWS_PROFILE","AWS_DEFAULT_PROFILE","AWS_SHARED_CREDENTIALS_FILE","AWS_CONFIG_FILE","AWS_ROLE_ARN","AWS_WEB_IDENTITY_TOKEN_FILE",
    "GITHUB_TOKEN","GH_TOKEN","GITHUB_ENTERPRISE_TOKEN","GH_ENTERPRISE_TOKEN","GIT_ASKPASS","SSH_ASKPASS",
    "ANTHROPIC_API_KEY","ANTHROPIC_AUTH_TOKEN","OPENAI_API_KEY","CIVITAI_API_KEY","HF_TOKEN","HUGGINGFACE_TOKEN","GITLAB_TOKEN"
  )
  foreach ($environmentKey in @($psi.EnvironmentVariables.Keys | ForEach-Object { [string]$_ })) {
    if ($environmentKey -match '^(?i:AWS_|GH_|GITHUB_|AZURE_|GOOGLE_|OPENAI_|ANTHROPIC_|CIVITAI_|HF_TOKEN$|HUGGINGFACE_|GITLAB_|GIT_CONFIG_)') {
      $credentialEnvironmentNames += $environmentKey
    }
  }
  $credentialEnvironmentNames = @($credentialEnvironmentNames | Sort-Object -Unique)
  foreach ($name in $credentialEnvironmentNames) { [void]$psi.EnvironmentVariables.Remove($name) }
  $psi.EnvironmentVariables["CURSOR_API_KEY"] = $cursorKey
  $psi.EnvironmentVariables["WSLENV"] = "CURSOR_API_KEY/u"
  $record.credential_environment_scrubbed = $true
  $record.scrubbed_environment_names = $credentialEnvironmentNames
  $record.wslenv_forward_allowlist = @("CURSOR_API_KEY/u")

  $proc = New-Object System.Diagnostics.Process
  $proc.StartInfo = $psi
  $workerStopwatch = [System.Diagnostics.Stopwatch]::StartNew()
  [void]$proc.Start()
  $stdoutTask = $proc.StandardOutput.ReadToEndAsync()
  $stderrTask = $proc.StandardError.ReadToEndAsync()
  if (-not $proc.WaitForExit($TimeoutSeconds * 1000)) {
    try { & taskkill.exe /PID $proc.Id /T /F | Out-Null } catch { try { $proc.Kill() } catch { } }
    try { [void]$proc.WaitForExit(5000) } catch { }
    $workerStopwatch.Stop()
    $record.duration_ms = $workerStopwatch.ElapsedMilliseconds
    $record.timed_out = $true
    $record.classification = "CURSOR_HANDOFF_TIMEOUT"
    throw "Cursor handoff timed out after $TimeoutSeconds seconds."
  }
  try { $proc.WaitForExit() } catch { }
  $stdout = $stdoutTask.Result
  $stderr = $stderrTask.Result
  $workerStopwatch.Stop()

  $stdoutRedacted = Redact-Text $stdout
  $stderrRedacted = Redact-Text $stderr
  Set-Content -LiteralPath $record.output_json_path -Value $stdoutRedacted -Encoding UTF8
  Set-Content -LiteralPath $record.stderr_path -Value $stderrRedacted -Encoding UTF8

  $record.exit_code = $proc.ExitCode
  $record.duration_ms = $workerStopwatch.ElapsedMilliseconds
  $record.stdout_length = $stdoutRedacted.Length
  $record.stderr_length = $stderrRedacted.Length
  $record.status = if ($proc.ExitCode -eq 0) { "PASS" } else { "FAIL" }
  $record.classification = if ($proc.ExitCode -eq 0) { "CURSOR_HANDOFF_COMPLETED" } else { "CURSOR_HANDOFF_PROCESS_FAILED" }

  try {
    $parsed = $stdoutRedacted | ConvertFrom-Json -ErrorAction Stop
    $record.cursor_session_id = $parsed.session_id
    $record.cursor_request_id = $parsed.request_id
    $outputContractText = (($parsed.result | Out-String).Trim())
    $record.output_contract_validated_from = "full_result"
    $record.cursor_result_excerpt = $outputContractText
    if ($record.cursor_result_excerpt.Length -gt 4000) { $record.cursor_result_excerpt = $record.cursor_result_excerpt.Substring(0,4000) }
    $record.cursor_usage = $parsed.usage
    if ($parsed.is_error -eq $true) {
      $record.status = "FAIL"
      $record.classification = "CURSOR_HANDOFF_AGENT_ERROR"
    }
    $requiredLabels = @("status:", "summary:", "files inspected:", "blockers:", "confidence:", "recommended Codex follow-up:")
    $missingLabels = @($requiredLabels | Where-Object { $outputContractText -notmatch [regex]::Escape($_) })
    $workerReportedStatusRaw = Get-WorkerReportedStatus -Text $outputContractText
    $workerReportedConfidenceRaw = Get-WorkerReportedConfidence -Text $outputContractText
    $workerReportedStatus = Normalize-WorkerStatus -Status $workerReportedStatusRaw
    $workerReportedConfidence = Normalize-WorkerConfidence -Confidence $workerReportedConfidenceRaw
    $record.worker_reported_status_raw = $workerReportedStatusRaw
    $record.worker_reported_status = $workerReportedStatus
    $record.worker_reported_confidence_raw = $workerReportedConfidenceRaw
    $record.worker_reported_confidence = $workerReportedConfidence
    $promiseOnlyPattern = '(?i)\b(i.ll|i will|next i.ll|next i will)\b.*\b(inspect|read|extract|check)\b'
    $tailLength = [Math]::Min(700, $outputContractText.Length)
    $resultTail = if ($tailLength -gt 0) { $outputContractText.Substring($outputContractText.Length - $tailLength, $tailLength) } else { "" }
    $endsWithPromise = ($resultTail -match $promiseOnlyPattern -and $resultTail -notmatch 'recommended Codex follow-up:')
    if ($missingLabels.Count -gt 0 -or $endsWithPromise -or [string]::IsNullOrWhiteSpace($workerReportedStatus) -or [string]::IsNullOrWhiteSpace($workerReportedConfidence)) {
      $record.status = "FAIL"
      $record.classification = "CURSOR_HANDOFF_INCOMPLETE_OUTPUT_CONTRACT"
      if ($missingLabels.Count -gt 0) { $record.issues += ("Cursor result missed output contract labels: " + ($missingLabels -join ", ")) }
      if ($endsWithPromise) { $record.issues += "Cursor result looked like an unfinished promise to inspect/read later, not a completed handoff." }
      if ([string]::IsNullOrWhiteSpace($workerReportedStatus)) { $record.issues += "Cursor result did not contain a parseable status label." }
      if ([string]::IsNullOrWhiteSpace($workerReportedConfidence)) { $record.issues += "Cursor result did not contain a parseable confidence label." }
    } elseif ($workerReportedConfidence -notin @("low","medium","high")) {
      $record.status = "FAIL"
      $record.classification = "CURSOR_HANDOFF_INVALID_CONFIDENCE_LABEL"
      $record.issues += "Cursor confidence must be exactly low, medium, or high: $workerReportedConfidence"
    } elseif ($workerReportedStatus -eq "fail") {
      $record.status = "FAIL"
      $record.classification = "CURSOR_HANDOFF_WORKER_REPORTED_BLOCKED"
      $record.issues += "Cursor reported a non-success status: $workerReportedStatus"
    } elseif ($workerReportedStatus -eq "blocked") {
      $record.status = "PASS"
      $record.classification = "CURSOR_HANDOFF_COMPLETED_BLOCKED"
      $record.worker_outcome = "blocked"
    } elseif ($workerReportedStatus -eq "pass_with_findings") {
      $record.status = "PASS"
      $record.classification = "CURSOR_HANDOFF_COMPLETED_WITH_FINDINGS"
      $record.worker_outcome = "pass_with_findings"
    } elseif ($workerReportedStatus -ne "pass") {
      $record.status = "FAIL"
      $record.classification = "CURSOR_HANDOFF_INVALID_STATUS_LABEL"
      $record.issues += "Cursor returned an unrecognized status label: $workerReportedStatus"
    }
  } catch {
    $record.issues += "Cursor stdout was not parseable JSON. See cursor_stdout.json."
    $record.status = "FAIL"
    $record.classification = "CURSOR_HANDOFF_NON_JSON_OUTPUT"
  }

  $postHandoffSnapshot = Get-GitWorktreeSnapshot -RepoRoot $projectRootFull
  $record.post_handoff_worktree_fingerprint = $postHandoffSnapshot.fingerprint
  $record.post_handoff_head = $postHandoffSnapshot.head
  $handoffChangedPaths = @(Compare-GitWorktreeSnapshots -Before $preHandoffSnapshot -After $postHandoffSnapshot)
  $record.worktree_paths_changed_during_handoff = @($handoffChangedPaths)
  $scopeMutationPaths = @()
  if ($null -ne $scopePacket) {
    foreach ($file in $scopePacket.files) {
      $relative = Normalize-GitRepoPath -Path ([string]$file.path)
      $scopedPath = Join-Path $projectRootFull $relative
      $afterHash = if (Test-Path -LiteralPath $scopedPath -PathType Leaf) { (Get-FileHash -LiteralPath $scopedPath -Algorithm SHA256).Hash.ToLowerInvariant() } else { "<missing>" }
      if ($scopeHashesBefore[$relative] -ne $afterHash) { $scopeMutationPaths += $relative }
    }
  }
  $record.scope_mutation_paths = @($scopeMutationPaths)
  $record.scope_files_unchanged = ($scopeMutationPaths.Count -eq 0)
  $record.concurrent_worktree_drift_detected = ($handoffChangedPaths.Count -gt 0 -and $scopeMutationPaths.Count -eq 0)
  $record.worktree_unchanged = ($handoffChangedPaths.Count -eq 0)
  if (-not $AllowWrites -and $scopeMutationPaths.Count -gt 0) {
    $record.status = "FAIL"
    $record.classification = "CURSOR_HANDOFF_READ_ONLY_MUTATION_VIOLATION"
    $record.issues += ("A hash-bound scope file changed during the read-only Cursor handoff: " + ($scopeMutationPaths -join ", "))
  } elseif ($handoffChangedPaths.Count -gt 0) {
    $record.warnings += ("Repository-visible state changed outside the hash-bound scope while Cursor ran: " + ($handoffChangedPaths -join ", "))
  }
  if ($AllowWrites) {
    $realChangedPaths = @($handoffChangedPaths | Where-Object { $_ -ne "<git-index-or-status-metadata>" })
    $malformedPaths = @($realChangedPaths | Where-Object { Test-MalformedRepoPath $_ })
    $outsideAllowedPaths = @($handoffChangedPaths | Where-Object {
      $_ -eq "<git-index-or-status-metadata>" -or -not (Test-AllowedRepoPath -RepoRelativePath $_ -AllowedRepoRelativePaths $allowedRepoRelativePaths)
    })
    if ($malformedPaths.Count -gt 0) {
      $record.status = "FAIL"
      $record.classification = "CURSOR_HANDOFF_MALFORMED_PATH_CREATED"
      $record.issues += ("Cursor created malformed repository paths: " + ($malformedPaths -join ", "))
    }
    if ($outsideAllowedPaths.Count -gt 0) {
      $record.status = "FAIL"
      $record.classification = "CURSOR_HANDOFF_WRITE_SCOPE_VIOLATION"
      $record.issues += ("Cursor changed paths outside allowed write scope: " + ($outsideAllowedPaths -join ", "))
    } elseif ($record.status -eq "PASS") {
      $record.agent_changes_accepted_for_codex_review = $true
    }
  }
} catch {
  $message = Redact-Text $_.Exception.Message
  $record.status = "FAIL"
  if ($record.classification -eq "CURSOR_HANDOFF_IN_PROGRESS") {
    $record.classification = if ($message -match '^CURSOR_[A-Z0-9_]+:') { ($message -split ':',2)[0] } else { "CURSOR_HANDOFF_WRAPPER_FAILED" }
  }
  $record.issues += $message
  throw
} finally {
  if ($null -ne $workerStopwatch -and $workerStopwatch.IsRunning) {
    $workerStopwatch.Stop()
    $record.duration_ms = $workerStopwatch.ElapsedMilliseconds
  }
  $record.finalized_at = (Get-Date).ToString("o")
  $record | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $recordPath -Encoding UTF8
  Remove-Item -LiteralPath $lockPath -Force -ErrorAction SilentlyContinue
}

$record | ConvertTo-Json -Depth 12
