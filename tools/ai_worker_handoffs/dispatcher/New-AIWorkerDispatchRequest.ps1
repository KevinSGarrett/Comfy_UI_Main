[CmdletBinding(PositionalBinding=$false)]
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$DispatcherRoot = "C:\Users\kevin\.codex\ai_worker_dispatcher",
  [Parameter(Mandatory=$true)][ValidatePattern('^[a-z0-9][a-z0-9_-]{2,80}$')][string]$TaskName,
  [Parameter(Mandatory=$true)][ValidateSet("Cursor","Claude")][string]$WorkerLane,
  [Parameter(Mandatory=$true)][ValidateSet("read_only","implementation")][string]$Operation,
  [Parameter(Mandatory=$true)][string]$WorkOrderText,
  [Parameter(Mandatory=$true)][string[]]$CandidatePaths,
  [string[]]$AllowedPaths = @(),
  [string[]]$DeclaredCommands = @(),
  [ValidateSet("SonnetPrimary","OpusEscalation")][string]$ClaudeTaskTier = "SonnetPrimary",
  [ValidateSet("claude-sonnet-5","claude-opus-4-8")][string]$ClaudeModel = "claude-sonnet-5",
  [ValidateSet("medium","high","xhigh")][string]$ClaudeEffort = "medium",
  [ValidateRange(60,1800)][int]$TimeoutSeconds = 600,
  [string]$DecisionUnitId = "",
  [string]$EscalationReason = "",
  [string]$PriorSonnetRecordPath = ""
)

$ErrorActionPreference = "Stop"

function Normalize-RelativePath {
  param([Parameter(Mandatory=$true)][string]$Path)
  if ([System.IO.Path]::IsPathRooted($Path)) { throw "Dispatch paths must be repository-relative: $Path" }
  $value = ($Path -replace '\\','/').TrimStart('/')
  if ([string]::IsNullOrWhiteSpace($value) -or @($value -split '/') -contains '..' -or $value -match '[:\u0000-\u001f]') {
    throw "Invalid dispatch path: $Path"
  }
  return $value
}

$projectRootFull = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\')
if (-not (Test-Path -LiteralPath (Join-Path $projectRootFull '.git'))) { throw "ProjectRoot is not the authoritative Git worktree: $projectRootFull" }
if ($WorkerLane -eq "Claude" -and $Operation -ne "read_only") { throw "Claude subscription dispatch is read-only." }
if ($WorkerLane -eq "Cursor" -and $ClaudeTaskTier -ne "SonnetPrimary") { throw "Claude tier options are invalid for Cursor dispatch." }
if ($WorkerLane -eq "Claude" -and $ClaudeTaskTier -eq "SonnetPrimary" -and $ClaudeModel -ne "claude-sonnet-5") { throw "SonnetPrimary requires claude-sonnet-5." }
if ($WorkerLane -eq "Claude" -and $ClaudeTaskTier -eq "OpusEscalation" -and $ClaudeModel -ne "claude-opus-4-8") { throw "OpusEscalation requires claude-opus-4-8." }

$candidatePathsNormalized = @($CandidatePaths | ForEach-Object { Normalize-RelativePath $_ } | Sort-Object -Unique)
$allowedPathsNormalized = @($AllowedPaths | ForEach-Object { Normalize-RelativePath $_ } | Sort-Object -Unique)
$declaredCommandsNormalized = @($DeclaredCommands | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { $_.Trim() } | Sort-Object -Unique)
if ($candidatePathsNormalized.Count -lt 1) { throw "At least one exact candidate path is required." }
foreach ($candidatePath in $candidatePathsNormalized) {
  & git.exe -C $projectRootFull diff --quiet -- $candidatePath
  if ($LASTEXITCODE -ne 0) { throw "Dispatch scope must match HEAD before isolated-worktree launch: $candidatePath" }
  & git.exe -C $projectRootFull diff --cached --quiet -- $candidatePath
  if ($LASTEXITCODE -ne 0) { throw "Dispatch scope has staged changes and cannot be hash-reproduced in an isolated worktree: $candidatePath" }
  & git.exe -C $projectRootFull ls-files --error-unmatch -- $candidatePath 2>$null | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "Dispatch scope file is not tracked at HEAD: $candidatePath" }
}
if ($Operation -eq "implementation" -and ($WorkerLane -ne "Cursor" -or $allowedPathsNormalized.Count -lt 1 -or $declaredCommandsNormalized.Count -lt 1)) {
  throw "Cursor implementation dispatch requires exact AllowedPaths and DeclaredCommands."
}
if ($Operation -eq "read_only" -and ($allowedPathsNormalized.Count -gt 0 -or $declaredCommandsNormalized.Count -gt 0)) {
  throw "Read-only dispatch may not declare write paths or execution commands."
}

$protectedPathPattern = '^(?i)(\.git(?:/|$)|\.env$|Plan/(?:Items|Tracker)(?:/|$)|masks(?:/|$)|Ref_Image_(?:1|2|Canonical_Body)(?:/|$)|Jira(?:/|$))'
$protectedPaths = @($allowedPathsNormalized | Where-Object { $_ -match $protectedPathPattern })
if ($protectedPaths.Count -gt 0) { throw "Worker implementation paths cross a Codex-only authority boundary: $($protectedPaths -join ', ')" }
$forbiddenCommandPattern = '(?i)(^|[;&|]\s*)(git|gh|aws|jira|kubectl|terraform)(\.exe)?\b|\b(commit|push|pull request|merge|mask promotion|wave71|tracker status)\b'
$forbiddenCommands = @($declaredCommandsNormalized | Where-Object { $_ -match $forbiddenCommandPattern })
if ($forbiddenCommands.Count -gt 0) { throw "Declared worker command crosses a Codex-only authority boundary: $($forbiddenCommands -join '; ')" }

$packetTool = Join-Path $projectRootFull 'tools\New-AIWorkerScopePacket.ps1'
if (-not (Test-Path -LiteralPath $packetTool -PathType Leaf)) { throw "Scope packet producer missing: $packetTool" }
$gate = if ($WorkerLane -eq 'Cursor') { 'CURSOR_FIRST_REQUIRED' } elseif ($ClaudeTaskTier -eq 'OpusEscalation') { 'CLAUDE_OPUS_ESCALATION_REQUIRED' } else { 'CLAUDE_SONNET_PRIMARY_REQUIRED' }
$packetJson = & $packetTool -ProjectRoot $projectRootFull -TaskName $TaskName -Gate $gate -WorkerLane $WorkerLane -CandidatePaths $candidatePathsNormalized
$packet = $packetJson | ConvertFrom-Json -ErrorAction Stop

$baseCommit = (& git.exe -C $projectRootFull rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $baseCommit -notmatch '^[0-9a-f]{40}$') { throw "Unable to resolve dispatch base commit." }
$stamp = (Get-Date -Format 'yyyyMMddTHHmmssfffzzz') -replace ':',''
$requestId = "${stamp}_${TaskName}_$([guid]::NewGuid().ToString('N').Substring(0,8))"
$queueRoot = Join-Path $DispatcherRoot 'queue'
New-Item -ItemType Directory -Force -Path $queueRoot | Out-Null
$requestPath = Join-Path $queueRoot "${requestId}.json"
$request = [ordered]@{
  schema_version = 1
  artifact_type = 'ai_worker_dispatch_request'
  status = 'QUEUED'
  request_id = $requestId
  created_at = (Get-Date).ToString('o')
  project_root = $projectRootFull
  base_commit = $baseCommit
  task_name = $TaskName
  worker_lane = $WorkerLane
  operation = $Operation
  work_order_text = $WorkOrderText
  scope_packet_path = [string]$packet.output_path
  scope_packet_sha256 = (Get-FileHash -LiteralPath ([string]$packet.output_path) -Algorithm SHA256).Hash.ToLowerInvariant()
  candidate_paths = $candidatePathsNormalized
  allowed_paths = $allowedPathsNormalized
  declared_commands = $declaredCommandsNormalized
  timeout_seconds = $TimeoutSeconds
  claude_task_tier = $ClaudeTaskTier
  claude_model = $ClaudeModel
  claude_effort = $ClaudeEffort
  decision_unit_id = $DecisionUnitId
  escalation_reason = $EscalationReason
  prior_sonnet_record_path = $PriorSonnetRecordPath
  final_authority = 'Codex Desktop'
}
[System.IO.File]::WriteAllText($requestPath, ($request | ConvertTo-Json -Depth 8), (New-Object System.Text.UTF8Encoding($false)))
$requestHashPath = $requestPath + '.sha256'
$requestHash = (Get-FileHash -LiteralPath $requestPath -Algorithm SHA256).Hash.ToLowerInvariant()
[System.IO.File]::WriteAllText($requestHashPath, $requestHash, (New-Object System.Text.UTF8Encoding($false)))
$request.request_path = $requestPath
$request.request_sha256 = $requestHash
$request.request_sha256_path = $requestHashPath
$request | ConvertTo-Json -Depth 8
