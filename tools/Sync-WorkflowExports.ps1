<#
.SYNOPSIS
Copies validated Plan workflow lane files into top-level Workflows.

.DESCRIPTION
Uses Plan/07_IMPLEMENTATION/workflow_templates/<group>/runtime_lane_queue.json
as the source of truth. This gives the project root directly usable ComfyUI
workflow files while preserving Plan as the authoritative implementation source.
#>
param(
  [string]$ProjectRoot = "",
  [ValidatePattern('^[a-z0-9_]+$')][string]$WorkflowGroup = "base_generation",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
  $ProjectRoot = Join-Path $PSScriptRoot ".."
}
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path)) {
    throw "Required JSON file missing: $Path"
  }
  return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
}

function Get-RelativePathCompat {
  param(
    [Parameter(Mandatory=$true)][string]$BasePath,
    [Parameter(Mandatory=$true)][string]$TargetPath
  )

  $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
  $baseFull = [System.IO.Path]::GetFullPath($BasePath)
  if (!$baseFull.EndsWith($separator)) {
    $baseFull = "$baseFull$separator"
  }
  $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
  $baseUri = New-Object System.Uri($baseFull)
  $targetUri = New-Object System.Uri($targetFull)
  return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace("/", $separator)
}

function Convert-ToRepoPath {
  param([Parameter(Mandatory=$true)][string]$Path)
  return (Get-RelativePathCompat -BasePath $ProjectRoot -TargetPath $Path).Replace("\", "/")
}

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 8
  )
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

$sourceBase = Join-Path $ProjectRoot "Plan\07_IMPLEMENTATION\workflow_templates\$WorkflowGroup"
$queuePath = Join-Path $sourceBase "runtime_lane_queue.json"
$destinationBase = Join-Path $ProjectRoot "Workflows\$WorkflowGroup"
$queue = Read-JsonFile -Path $queuePath

New-Item -ItemType Directory -Force -Path $destinationBase | Out-Null

$copiedFiles = New-Object System.Collections.ArrayList
$laneExports = New-Object System.Collections.ArrayList
$errors = New-Object System.Collections.ArrayList
$requiredLaneFiles = @(
  "workflow.api.json",
  "smoke_test_request.json",
  "runtime_requirements.json",
  "patch_points.json"
)

foreach ($lane in @($queue.lanes)) {
  $laneId = [string]$lane.lane_id
  $sourceLaneDir = Join-Path $sourceBase $laneId
  $destinationLaneDir = Join-Path $destinationBase $laneId
  New-Item -ItemType Directory -Force -Path $destinationLaneDir | Out-Null

  foreach ($fileName in $requiredLaneFiles) {
    $sourcePath = Join-Path $sourceLaneDir $fileName
    $destinationPath = Join-Path $destinationLaneDir $fileName

    if (!(Test-Path -LiteralPath $sourcePath)) {
      [void]$errors.Add([ordered]@{
        lane_id = $laneId
        file = $fileName
        error = "missing_source_file"
        path = Convert-ToRepoPath -Path $sourcePath
      })
      continue
    }

    Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -Force
    $sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $sourcePath).Hash.ToLowerInvariant()
    $destinationHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $destinationPath).Hash.ToLowerInvariant()
    [void]$copiedFiles.Add([ordered]@{
      lane_id = $laneId
      file = $fileName
      source = Convert-ToRepoPath -Path $sourcePath
      destination = Convert-ToRepoPath -Path $destinationPath
      sha256 = $destinationHash
      hash_match = ($sourceHash -eq $destinationHash)
    })
  }

  [void]$laneExports.Add([ordered]@{
    order = [int]$lane.order
    lane_id = $laneId
    workflow = "Workflows/$WorkflowGroup/$laneId/workflow.api.json"
    smoke_request = "Workflows/$WorkflowGroup/$laneId/smoke_test_request.json"
    runtime_requirements = "Workflows/$WorkflowGroup/$laneId/runtime_requirements.json"
    patch_points = "Workflows/$WorkflowGroup/$laneId/patch_points.json"
    status = [string]$lane.status
    next_gate = [string]$lane.required_next_runtime_gate
  })
}

$activeLanesPath = Join-Path $destinationBase "ACTIVE_LANES.json"
$activeLanes = [ordered]@{
  schema_version = "1.0"
  updated_at = [string]$queue.updated_at
  source_queue = "Plan/07_IMPLEMENTATION/workflow_templates/$WorkflowGroup/runtime_lane_queue.json"
  lanes = @($laneExports)
  runtime_boundaries = [ordered]@{
    ec2_start_allowed_by_this_manifest = $false
    generation_allowed_by_this_manifest = $false
    reason = "This manifest exposes local workflow files only; AWS auth and runtime proof gates remain mandatory."
  }
}
Write-JsonNoBom -Value $activeLanes -Path $activeLanesPath -Depth 8

$result = "pass"
if (@($errors).Count -gt 0 -or @($copiedFiles | Where-Object { -not $_.hash_match }).Count -gt 0) {
  $result = "fail"
}

$record = [ordered]@{
  evidence_id = "ROOT-WORKFLOW-EXPORT-SYNC-$((Get-Date).ToString('yyyyMMddTHHmmsszzz').Replace(':',''))"
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  project_root = $ProjectRoot
  workflow_group = $WorkflowGroup
  queue = Convert-ToRepoPath -Path $queuePath
  destination = Convert-ToRepoPath -Path $destinationBase
  lane_count = @($laneExports).Count
  copied_file_count = @($copiedFiles).Count
  copied_files = @($copiedFiles)
  active_lanes_manifest = Convert-ToRepoPath -Path $activeLanesPath
  errors = @($errors)
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  result = $result
}

if ($OutFile) {
  $outDir = Split-Path -Parent $OutFile
  if ($outDir) {
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
  }
  Write-JsonNoBom -Value $record -Path $OutFile -Depth 8
}

$record | ConvertTo-Json -Depth 8
if ($result -ne "pass") {
  exit 1
}
