<#
.SYNOPSIS
Creates a bounded deterministic input packet for a Cursor or Claude handoff.

.DESCRIPTION
Accepts an explicit candidate list, enforces repository containment and size
limits, and records exact hashes. It deliberately does not discover or scan the
project tree; callers must shortlist from current authority files first.
#>
[CmdletBinding(PositionalBinding = $false)]
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",

  [Parameter(Mandatory = $true)]
  [ValidatePattern('^[a-z0-9][a-z0-9_-]{2,80}$')]
  [string]$TaskName,

  [Parameter(Mandatory = $true)]
  [ValidateSet("CURSOR_FIRST_REQUIRED", "CLAUDE_HEAVY_REVIEW_REQUIRED", "GIT_GITHUB_WORKER_ANALYSIS_REQUIRED")]
  [string]$Gate,

  [Parameter(Mandatory = $true)]
  [ValidateSet("Cursor", "Claude", "GitGitHub")]
  [string]$WorkerLane,

  [Parameter(Mandatory = $true)]
  [string[]]$CandidatePaths,

  [ValidateRange(1, 20)]
  [int]$MaxCandidates = 12,

  [ValidateRange(1024, 10485760)]
  [long]$MaxFileBytes = 2097152,

  [string]$OutputPath = ""
)

$ErrorActionPreference = "Stop"
$projectRootFull = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd('\')
if (!(Test-Path -LiteralPath $projectRootFull -PathType Container)) { throw "Project root missing: $projectRootFull" }

$uniqueCandidates = @($CandidatePaths | Where-Object { ![string]::IsNullOrWhiteSpace($_) } | Select-Object -Unique)
if ($uniqueCandidates.Count -eq 0) { throw "At least one candidate path is required." }
if ($uniqueCandidates.Count -gt $MaxCandidates) {
  throw "Candidate count $($uniqueCandidates.Count) exceeds MaxCandidates=$MaxCandidates. Shortlist before worker delegation."
}

$files = @()
foreach ($candidate in $uniqueCandidates) {
  $candidateFull = if ([System.IO.Path]::IsPathRooted($candidate)) {
    [System.IO.Path]::GetFullPath($candidate)
  } else {
    [System.IO.Path]::GetFullPath((Join-Path $projectRootFull $candidate))
  }
  $insideRoot = $candidateFull.Equals($projectRootFull, [System.StringComparison]::OrdinalIgnoreCase) -or
    $candidateFull.StartsWith($projectRootFull + '\', [System.StringComparison]::OrdinalIgnoreCase)
  if (!$insideRoot) { throw "Candidate is outside project root: $candidate" }
  if (!(Test-Path -LiteralPath $candidateFull -PathType Leaf)) { throw "Candidate file missing: $candidateFull" }

  $item = Get-Item -LiteralPath $candidateFull
  if ($item.Length -gt $MaxFileBytes) {
    throw "Candidate exceeds MaxFileBytes=${MaxFileBytes}: $candidateFull ($($item.Length) bytes)"
  }
  $relative = $candidateFull.Substring($projectRootFull.Length).TrimStart('\').Replace('\', '/')
  $files += [ordered]@{
    path = $relative
    bytes = $item.Length
    last_write_utc = $item.LastWriteTimeUtc.ToString("o")
    sha256 = (Get-FileHash -LiteralPath $candidateFull -Algorithm SHA256).Hash.ToLowerInvariant()
  }
}

$now = [DateTimeOffset]::Now
$stamp = $now.ToString("yyyyMMdd'T'HHmmsszzz") -replace ':', ''
if ([string]::IsNullOrWhiteSpace($OutputPath)) {
  $OutputPath = Join-Path $projectRootFull "runtime_artifacts\agent_handoffs\scope_packets\${stamp}_${TaskName}.json"
}
$outputParent = Split-Path -Parent $OutputPath
if (![string]::IsNullOrWhiteSpace($outputParent)) { New-Item -ItemType Directory -Path $outputParent -Force | Out-Null }

$packet = [ordered]@{
  schema_version = 1
  artifact_type = "ai_worker_scope_packet"
  status = "ready"
  created_at = $now.ToString("o")
  task_name = $TaskName
  gate = $Gate
  worker_lane = $WorkerLane
  discovery_mode = "caller_supplied_deterministic_shortlist"
  broad_worker_discovery_allowed = $false
  max_candidates = $MaxCandidates
  candidate_count = $files.Count
  files = $files
  required_worker_output_labels = @("status:", "summary:", "files inspected:", "blockers:", "recommended Codex follow-up:")
  mutation_boundary = "Codex-only"
}

$packet | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $OutputPath -Encoding UTF8
$packet.output_path = [System.IO.Path]::GetFullPath($OutputPath)
$packet | ConvertTo-Json -Depth 8
