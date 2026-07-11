<#
.SYNOPSIS
Runs disposable containment and bound tests for AI worker scope packets.
#>
[CmdletBinding(PositionalBinding = $false)]
param([string]$ProjectRoot = "C:\Comfy_UI_Main")

$ErrorActionPreference = "Stop"
$scriptPath = Join-Path $ProjectRoot "tools\New-AIWorkerScopePacket.ps1"
if (!(Test-Path -LiteralPath $scriptPath -PathType Leaf)) { throw "Scope packet script missing: $scriptPath" }

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ai_worker_scope_packet_" + [guid]::NewGuid().ToString("N"))
$outsidePath = Join-Path ([System.IO.Path]::GetTempPath()) ("outside_" + [guid]::NewGuid().ToString("N") + ".txt")
New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
Set-Content -LiteralPath (Join-Path $tempRoot "one.md") -Value "one" -Encoding UTF8
Set-Content -LiteralPath (Join-Path $tempRoot "two.ps1") -Value "Write-Output two" -Encoding UTF8
Set-Content -LiteralPath $outsidePath -Value "outside" -Encoding UTF8

try {
  $packetPath = Join-Path $tempRoot "packet.json"
  $packet = & $scriptPath -ProjectRoot $tempRoot -TaskName "bounded_scope_test" -Gate CURSOR_FIRST_REQUIRED -WorkerLane Cursor -CandidatePaths @("one.md", "two.ps1") -OutputPath $packetPath | ConvertFrom-Json

  $tooManyRejected = $false
  try {
    & $scriptPath -ProjectRoot $tempRoot -TaskName "too_many_test" -Gate CURSOR_FIRST_REQUIRED -WorkerLane Cursor -CandidatePaths @("one.md", "two.ps1") -MaxCandidates 1 -OutputPath (Join-Path $tempRoot "too_many.json") | Out-Null
  } catch { $tooManyRejected = $_.Exception.Message -match "exceeds MaxCandidates" }

  $outsideRejected = $false
  try {
    & $scriptPath -ProjectRoot $tempRoot -TaskName "outside_test" -Gate CLAUDE_HEAVY_REVIEW_REQUIRED -WorkerLane Claude -CandidatePaths @($outsidePath) -OutputPath (Join-Path $tempRoot "outside.json") | Out-Null
  } catch { $outsideRejected = $_.Exception.Message -match "outside project root" }

  $checks = @(
    [pscustomobject]@{ name = "bounded_packet_ready"; passed = ($packet.status -eq "ready" -and $packet.candidate_count -eq 2) },
    [pscustomobject]@{ name = "broad_discovery_disabled"; passed = ($packet.broad_worker_discovery_allowed -eq $false) },
    [pscustomobject]@{ name = "too_many_rejected"; passed = $tooManyRejected },
    [pscustomobject]@{ name = "outside_root_rejected"; passed = $outsideRejected }
  )
  $failed = @($checks | Where-Object { -not $_.passed })
  [ordered]@{
    status = $(if ($failed.Count -eq 0) { "PASS" } else { "FAIL" })
    check_count = $checks.Count
    failed_count = $failed.Count
    checks = $checks
  } | ConvertTo-Json -Depth 6
  if ($failed.Count -gt 0) { exit 1 }
} finally {
  if (Test-Path -LiteralPath $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force }
  if (Test-Path -LiteralPath $outsidePath) { Remove-Item -LiteralPath $outsidePath -Force }
}
