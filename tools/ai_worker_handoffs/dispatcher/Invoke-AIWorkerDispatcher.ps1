[CmdletBinding(PositionalBinding=$false)]
param(
  [string]$DispatcherRoot = "C:\Users\kevin\.codex\ai_worker_dispatcher",
  [switch]$Once,
  [ValidateRange(1,100)][int]$MaxRequests = 1,
  [ValidateRange(1,240)][int]$StaleDispatchLockMinutes = 30,
  [string]$CursorWrapperPath = "C:\Users\kevin\.codex\cursor_handoff\Invoke-CursorAgentHandoff.ps1",
  [string]$ClaudeWrapperPath = "C:\Users\kevin\.codex\claude_subscription_handoff\Invoke-ClaudeSubscriptionHandoff.ps1"
)

$ErrorActionPreference = "Stop"

function Write-JsonFile {
  param([string]$Path,[object]$Value)
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $Path) | Out-Null
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth 12), (New-Object System.Text.UTF8Encoding($false)))
}

function Assert-UnderRoot {
  param([string]$Path,[string]$Root)
  $full = [System.IO.Path]::GetFullPath($Path)
  $rootFull = [System.IO.Path]::GetFullPath($Root).TrimEnd('\')
  if (-not $full.StartsWith($rootFull + '\',[System.StringComparison]::OrdinalIgnoreCase)) { throw "Path escaped dispatcher root: $full" }
  return $full
}

function Enter-DispatchLock {
  param([string]$Path,[int]$StaleMinutes)
  if (Test-Path -LiteralPath $Path) {
    $remove = $false
    try {
      $existing = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
      $remove = ($null -eq (Get-Process -Id ([int]$existing.pid) -ErrorAction SilentlyContinue))
    } catch { $remove = $true }
    if (((Get-Date) - (Get-Item -LiteralPath $Path).LastWriteTime).TotalMinutes -ge $StaleMinutes) { $remove = $true }
    if ($remove) { Remove-Item -LiteralPath $Path -Force }
  }
  try {
    $stream = [System.IO.File]::Open($Path,[System.IO.FileMode]::CreateNew,[System.IO.FileAccess]::Write,[System.IO.FileShare]::None)
    try {
      $bytes = [System.Text.Encoding]::UTF8.GetBytes(([ordered]@{pid=$PID;created_at=(Get-Date).ToString('o')} | ConvertTo-Json -Compress))
      $stream.Write($bytes,0,$bytes.Length)
    } finally { $stream.Dispose() }
    return $true
  } catch [System.IO.IOException] { return $false }
}

function Copy-HandoffArtifacts {
  param([string]$WorktreePath,[string]$Destination)
  $sourceRoot = Join-Path $WorktreePath 'runtime_artifacts\agent_handoffs'
  if (-not (Test-Path -LiteralPath $sourceRoot -PathType Container)) { return @() }
  $records = @(Get-ChildItem -LiteralPath $sourceRoot -Filter handoff_record.json -File -Recurse -ErrorAction SilentlyContinue | Sort-Object LastWriteTimeUtc)
  if ($records.Count -eq 0) { return @() }
  $latestDir = $records[-1].Directory.FullName
  $artifactDestination = Join-Path $Destination 'worker_handoff'
  Copy-Item -LiteralPath $latestDir -Destination $artifactDestination -Recurse -Force
  return @(Get-ChildItem -LiteralPath $artifactDestination -File -Recurse | ForEach-Object { $_.FullName })
}

function Assert-DispatchRequest {
  param([Parameter(Mandatory=$true)]$Request,[Parameter(Mandatory=$true)][string]$RequestId)
  if ([string]$Request.artifact_type -ne 'ai_worker_dispatch_request' -or [string]$Request.status -ne 'QUEUED' -or [string]$Request.request_id -ne $RequestId) { throw 'Invalid dispatch request contract.' }
  if ([string]$Request.worker_lane -notin @('Cursor','Claude')) { throw 'Invalid worker lane.' }
  if ([string]$Request.operation -notin @('read_only','implementation')) { throw 'Invalid dispatch operation.' }
  if ([string]$Request.worker_lane -eq 'Claude' -and [string]$Request.operation -ne 'read_only') { throw 'Claude dispatch must remain read-only.' }
  $projectRoot = [System.IO.Path]::GetFullPath([string]$Request.project_root).TrimEnd('\')
  $worktrees = @(& git.exe -C $projectRoot worktree list --porcelain 2>$null | Where-Object { $_ -like 'worktree *' } | ForEach-Object { [System.IO.Path]::GetFullPath($_.Substring(9)).TrimEnd('\') })
  if ($LASTEXITCODE -ne 0 -or $worktrees.Count -lt 1 -or -not $projectRoot.Equals($worktrees[0],[System.StringComparison]::OrdinalIgnoreCase)) { throw 'Dispatch project_root must be the registered primary worktree.' }
  $packetFull = [System.IO.Path]::GetFullPath([string]$Request.scope_packet_path)
  $packetRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot 'runtime_artifacts\agent_handoffs\scope_packets')).TrimEnd('\')
  if (-not $packetFull.StartsWith($packetRoot + '\',[System.StringComparison]::OrdinalIgnoreCase)) { throw 'Dispatch scope packet is outside the authoritative packet root.' }
  $protectedPathPattern = '^(?i)(\.git(?:/|$)|\.env$|Plan/(?:Items|Tracker)(?:/|$)|masks(?:/|$)|Ref_Image_(?:1|2|Canonical_Body)(?:/|$)|Jira(?:/|$))'
  $allowedPaths = @($Request.allowed_paths | ForEach-Object { ([string]$_ -replace '\\','/').TrimStart('/') })
  if (@($allowedPaths | Where-Object { [System.IO.Path]::IsPathRooted($_) -or $_ -match '[:\u0000-\u001f]' -or $_ -match $protectedPathPattern -or $_ -match '(^|/)\.\.(/|$)' }).Count -gt 0) { throw 'Queued request crosses a protected worker authority path.' }
  $forbiddenCommandPattern = '(?i)(^|[;&|]\s*)(git|gh|aws|jira|kubectl|terraform)(\.exe)?\b|\b(commit|push|pull request|merge|mask promotion|wave71|tracker status)\b'
  if (@($Request.declared_commands | Where-Object { [string]$_ -match $forbiddenCommandPattern }).Count -gt 0) { throw 'Queued request contains a prohibited authority command.' }
  if ([string]$Request.operation -eq 'implementation' -and ([string]$Request.worker_lane -ne 'Cursor' -or $allowedPaths.Count -lt 1 -or @($Request.declared_commands).Count -lt 1)) { throw 'Implementation request lacks guarded Cursor paths or commands.' }
  if ([string]$Request.operation -eq 'read_only' -and ($allowedPaths.Count -gt 0 -or @($Request.declared_commands).Count -gt 0)) { throw 'Read-only request may not declare writes or commands.' }
}

$dispatcherRootFull = [System.IO.Path]::GetFullPath($DispatcherRoot).TrimEnd('\')
foreach ($name in @('queue','running','completed','failed','worktrees','logs')) { New-Item -ItemType Directory -Force -Path (Join-Path $dispatcherRootFull $name) | Out-Null }
$dispatchLock = Join-Path $dispatcherRootFull 'dispatcher.lock'
if (-not (Enter-DispatchLock -Path $dispatchLock -StaleMinutes $StaleDispatchLockMinutes)) {
  [ordered]@{status='IDLE';classification='AI_WORKER_DISPATCHER_ALREADY_RUNNING';processed=0} | ConvertTo-Json
  return
}

$processed = @()
try {
  $requests = @(Get-ChildItem -LiteralPath (Join-Path $dispatcherRootFull 'queue') -Filter *.json -File | Sort-Object Name | Select-Object -First $MaxRequests)
  foreach ($requestFile in $requests) {
    $request = $null
    $requestId = [System.IO.Path]::GetFileNameWithoutExtension($requestFile.Name)
    if ($requestId -notmatch '^[A-Za-z0-9_.-]{3,180}$') { throw "Unsafe dispatch request filename: $($requestFile.Name)" }
    $queuedHashPath = $requestFile.FullName + '.sha256'
    $runningPath = Join-Path $dispatcherRootFull "running\${requestId}.json"
    $runningHashPath = $runningPath + '.sha256'
    $preflightError = ''
    try {
      if (-not (Test-Path -LiteralPath $queuedHashPath -PathType Leaf)) { throw "Dispatch request hash sidecar missing: $queuedHashPath" }
      $expectedRequestHash = (Get-Content -LiteralPath $queuedHashPath -Raw).Trim().ToLowerInvariant()
      $actualRequestHash = (Get-FileHash -LiteralPath $requestFile.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
      if ($expectedRequestHash -notmatch '^[0-9a-f]{64}$' -or $actualRequestHash -ne $expectedRequestHash) { throw "Dispatch request hash mismatch: $requestId" }
      Move-Item -LiteralPath $requestFile.FullName -Destination $runningPath
      Move-Item -LiteralPath $queuedHashPath -Destination $runningHashPath
    } catch { $preflightError = $_.Exception.Message }
    if (-not [string]::IsNullOrWhiteSpace($preflightError)) {
      $failedRoot = Assert-UnderRoot -Path (Join-Path $dispatcherRootFull "failed\$requestId") -Root $dispatcherRootFull
      New-Item -ItemType Directory -Force -Path $failedRoot | Out-Null
      $failedRecordPath = Join-Path $failedRoot 'dispatch_record.json'
      $failedRecord = [ordered]@{schema_version=1;artifact_type='ai_worker_dispatch_record';request_id=$requestId;started_at=(Get-Date).ToString('o');finalized_at=(Get-Date).ToString('o');status='FAIL';classification='AI_WORKER_DISPATCH_REQUEST_INTEGRITY_FAILED';issues=@($preflightError);warnings=@();adoption_status='NOT_APPLICABLE'}
      Write-JsonFile -Path $failedRecordPath -Value $failedRecord
      if (Test-Path -LiteralPath $requestFile.FullName) { Move-Item -LiteralPath $requestFile.FullName -Destination (Join-Path $failedRoot 'request.json') -Force }
      if (Test-Path -LiteralPath $queuedHashPath) { Move-Item -LiteralPath $queuedHashPath -Destination (Join-Path $failedRoot 'request.json.sha256') -Force }
      $processed += [ordered]@{request_id=$requestId;status='FAIL';classification='AI_WORKER_DISPATCH_REQUEST_INTEGRITY_FAILED';dispatch_record_path=$failedRecordPath}
      continue
    }
    $startedAt = Get-Date
    $worktreePath = Assert-UnderRoot -Path (Join-Path $dispatcherRootFull "worktrees\$requestId") -Root $dispatcherRootFull
    $outcomeRoot = $null
    $worktreeCreated = $false
    $retainWorktree = $false
    $dispatchRecord = [ordered]@{
      schema_version = 1
      artifact_type = 'ai_worker_dispatch_record'
      request_id = $requestId
      started_at = $startedAt.ToString('o')
      status = 'IN_PROGRESS'
      classification = 'AI_WORKER_DISPATCH_IN_PROGRESS'
      issues = @()
      warnings = @()
      adoption_status = 'PENDING_CODEX_REVIEW'
    }
    try {
      $request = Get-Content -LiteralPath $runningPath -Raw | ConvertFrom-Json -ErrorAction Stop
      Assert-DispatchRequest -Request $request -RequestId $requestId
      $projectRoot = [System.IO.Path]::GetFullPath([string]$request.project_root).TrimEnd('\')
      $scopePacketPath = [System.IO.Path]::GetFullPath([string]$request.scope_packet_path)
      if (-not (Test-Path -LiteralPath $scopePacketPath -PathType Leaf)) { throw "Scope packet missing: $scopePacketPath" }
      $scopeHash = (Get-FileHash -LiteralPath $scopePacketPath -Algorithm SHA256).Hash.ToLowerInvariant()
      if ($scopeHash -ne ([string]$request.scope_packet_sha256).ToLowerInvariant()) { throw 'Scope packet hash changed after queueing.' }
      if ([string]$request.base_commit -notmatch '^[0-9a-f]{40}$') { throw 'Invalid base commit.' }
      & git.exe -C $projectRoot cat-file -e "$($request.base_commit)^{commit}"
      if ($LASTEXITCODE -ne 0) { throw "Dispatch base commit is unavailable: $($request.base_commit)" }
      New-Item -ItemType Directory -Force -Path (Split-Path -Parent $worktreePath) | Out-Null
      & git.exe -C $projectRoot worktree add --quiet --detach $worktreePath ([string]$request.base_commit) | Out-Null
      if ($LASTEXITCODE -ne 0) { throw 'Unable to create isolated dispatch worktree.' }
      $worktreeCreated = $true
      $dispatchRecord.project_root = $projectRoot
      $dispatchRecord.isolated_worktree_path = $worktreePath
      $dispatchRecord.base_commit = [string]$request.base_commit
      $dispatchRecord.worker_lane = [string]$request.worker_lane
      $dispatchRecord.operation = [string]$request.operation

      if ([string]$request.worker_lane -eq 'Cursor') {
        if (-not (Test-Path -LiteralPath $CursorWrapperPath -PathType Leaf)) { throw "Cursor wrapper missing: $CursorWrapperPath" }
        $cursorParams = @{
          ProjectRoot = $worktreePath
          CredentialRoot = $projectRoot
          TaskName = [string]$request.task_name
          Mode = $(if ([string]$request.operation -eq 'implementation') { 'agent' } else { 'ask' })
          ScopePacketPath = $scopePacketPath
          TimeoutSeconds = [int]$request.timeout_seconds
          WorkOrderText = [string]$request.work_order_text
        }
        if ([string]$request.operation -eq 'implementation') {
          $cursorParams.AllowWrites = $true
          $cursorParams.AllowedPaths = @($request.allowed_paths)
          $cursorParams.DeclaredAgentCommands = @($request.declared_commands)
          $retainWorktree = $true
        }
        $workerOutput = & $CursorWrapperPath @cursorParams
      } elseif ([string]$request.worker_lane -eq 'Claude') {
        if (-not (Test-Path -LiteralPath $ClaudeWrapperPath -PathType Leaf)) { throw "Claude wrapper missing: $ClaudeWrapperPath" }
        $claudeParams = @{
          ProjectRoot = $worktreePath
          TaskName = [string]$request.task_name
          TaskTier = [string]$request.claude_task_tier
          ClaudeModel = [string]$request.claude_model
          Effort = [string]$request.claude_effort
          ScopePacketPath = $scopePacketPath
          TimeoutSeconds = [int]$request.timeout_seconds
          WorkOrderText = [string]$request.work_order_text
        }
        if (-not [string]::IsNullOrWhiteSpace([string]$request.decision_unit_id)) { $claudeParams.DecisionUnitId = [string]$request.decision_unit_id }
        if ([string]$request.claude_task_tier -eq 'OpusEscalation') {
          $claudeParams.EscalationReason = [string]$request.escalation_reason
          if (-not [string]::IsNullOrWhiteSpace([string]$request.prior_sonnet_record_path)) { $claudeParams.PriorSonnetRecordPath = [string]$request.prior_sonnet_record_path }
        }
        $workerOutput = & $ClaudeWrapperPath @claudeParams
      } else { throw "Unsupported worker lane: $($request.worker_lane)" }

      $workerRecord = ($workerOutput | Out-String).Trim() | ConvertFrom-Json -ErrorAction Stop
      $dispatchRecord.worker_status = [string]$workerRecord.status
      $dispatchRecord.worker_classification = [string]$workerRecord.classification
      if ([string]$workerRecord.status -ne 'PASS') { throw "Worker wrapper did not complete usefully: $($workerRecord.classification)" }
      $dispatchRecord.status = 'PASS'
      $dispatchRecord.classification = 'AI_WORKER_DISPATCH_COMPLETED_AWAITING_CODEX'
      $outcomeRoot = Join-Path $dispatcherRootFull "completed\$requestId"
    } catch {
      $dispatchRecord.status = 'FAIL'
      $dispatchRecord.classification = 'AI_WORKER_DISPATCH_FAILED'
      $dispatchRecord.issues += $_.Exception.Message
      $outcomeRoot = Join-Path $dispatcherRootFull "failed\$requestId"
    } finally {
      New-Item -ItemType Directory -Force -Path $outcomeRoot | Out-Null
      $dispatchRecord.worker_artifact_paths = @(Copy-HandoffArtifacts -WorktreePath $worktreePath -Destination $outcomeRoot)
      $dispatchRecord.worktree_retained_for_codex_review = ($worktreeCreated -and $retainWorktree)
      if ($worktreeCreated -and -not $retainWorktree) {
        & git.exe -C ([string]$request.project_root) worktree remove --force $worktreePath | Out-Null
        if ($LASTEXITCODE -ne 0) { $dispatchRecord.warnings += "Unable to remove completed read-only worktree: $worktreePath" }
      }
      $dispatchRecord.finalized_at = (Get-Date).ToString('o')
      $dispatchRecord.duration_ms = [long]((Get-Date) - $startedAt).TotalMilliseconds
      $dispatchRecordPath = Join-Path $outcomeRoot 'dispatch_record.json'
      Write-JsonFile -Path $dispatchRecordPath -Value $dispatchRecord
      Move-Item -LiteralPath $runningPath -Destination (Join-Path $outcomeRoot 'request.json') -Force
      Move-Item -LiteralPath $runningHashPath -Destination (Join-Path $outcomeRoot 'request.json.sha256') -Force
      $processed += [ordered]@{request_id=$requestId;status=$dispatchRecord.status;classification=$dispatchRecord.classification;dispatch_record_path=$dispatchRecordPath}
    }
  }
} finally {
  Remove-Item -LiteralPath $dispatchLock -Force -ErrorAction SilentlyContinue
}

[ordered]@{
  status = $(if (@($processed | Where-Object { $_.status -eq 'FAIL' }).Count -gt 0) { 'FAIL' } else { 'PASS' })
  classification = $(if ($processed.Count -gt 0) { 'AI_WORKER_DISPATCHER_PROCESSED' } else { 'AI_WORKER_DISPATCHER_IDLE' })
  processed = $processed.Count
  results = $processed
} | ConvertTo-Json -Depth 8
