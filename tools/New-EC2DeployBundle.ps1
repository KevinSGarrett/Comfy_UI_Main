<#
.SYNOPSIS
Builds a local-only EC2 deploy bundle from a validated workflow run package.

.DESCRIPTION
Creates a minimal ready-to-upload bundle that can be prepared while EC2 is
stopped. The bundle contains the active lane files, the selected run package,
model registry metadata, and safe runtime context. It does not contact AWS,
GitHub APIs, Civitai, ComfyUI, or start EC2.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LaneId = "",
  [string]$RunPackageManifestFile = "",
  [string]$OutDir = "",
  [string]$BundleName = ""
)

$ErrorActionPreference = "Stop"

function Read-JsonFile {
  param([Parameter(Mandatory=$true)][string]$Path)
  if (!(Test-Path -LiteralPath $Path)) {
    throw "Required JSON file missing: $Path"
  }
  return Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json
}

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 20
  )
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
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

function Resolve-ProjectPath {
  param([Parameter(Mandatory=$true)][string]$Path)
  if ([System.IO.Path]::IsPathRooted($Path)) {
    return [System.IO.Path]::GetFullPath($Path)
  }
  return [System.IO.Path]::GetFullPath((Join-Path $ProjectRoot $Path.Replace("/", "\")))
}

function Assert-UnderProject {
  param([Parameter(Mandatory=$true)][string]$Path)

  $projectFull = [System.IO.Path]::GetFullPath($ProjectRoot).TrimEnd("\", "/") + [System.IO.Path]::DirectorySeparatorChar
  $targetFull = [System.IO.Path]::GetFullPath($Path)
  if (!$targetFull.StartsWith($projectFull, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to package a path outside ProjectRoot: $Path"
  }
}

function Copy-BundleFile {
  param(
    [Parameter(Mandatory=$true)][string]$SourcePath,
    [Parameter(Mandatory=$true)][string]$ContentRoot,
    [System.Collections.ArrayList]$Records,
    [switch]$Required
  )

  if (!(Test-Path -LiteralPath $SourcePath)) {
    if ($Required) { throw "Bundle source file missing: $SourcePath" }
    return
  }
  Assert-UnderProject -Path $SourcePath
  $repoPath = Convert-ToRepoPath -Path $SourcePath
  $destination = Join-Path $ContentRoot $repoPath.Replace("/", "\")
  $destinationDir = Split-Path -Parent $destination
  if (![string]::IsNullOrWhiteSpace($destinationDir)) {
    $null = New-Item -ItemType Directory -Force -Path $destinationDir
  }
  Copy-Item -LiteralPath $SourcePath -Destination $destination -Force
  [void]$Records.Add([ordered]@{
    path = $repoPath
    size_bytes = (Get-Item -LiteralPath $destination).Length
    sha256 = (Get-FileHash -Algorithm SHA256 -LiteralPath $destination).Hash.ToLowerInvariant()
  })
}

function Copy-BundleDirectory {
  param(
    [Parameter(Mandatory=$true)][string]$SourceDir,
    [Parameter(Mandatory=$true)][string]$ContentRoot,
    [System.Collections.ArrayList]$Records,
    [switch]$Required
  )

  if (!(Test-Path -LiteralPath $SourceDir)) {
    if ($Required) { throw "Bundle source directory missing: $SourceDir" }
    return
  }
  Assert-UnderProject -Path $SourceDir
  foreach ($file in @(Get-ChildItem -LiteralPath $SourceDir -Recurse -File)) {
    Copy-BundleFile -SourcePath $file.FullName -ContentRoot $ContentRoot -Records $Records -Required
  }
}

function Find-RunPackageManifest {
  param([string]$ExpectedLaneId)

  $packageRoot = Join-Path $ProjectRoot "runtime_artifacts\run_packages"
  if (!(Test-Path -LiteralPath $packageRoot)) { return $null }
  foreach ($candidate in @(Get-ChildItem -LiteralPath $packageRoot -Recurse -Filter "RUN_PACKAGE_MANIFEST.json" -File | Sort-Object LastWriteTimeUtc -Descending)) {
    try {
      $manifest = Read-JsonFile -Path $candidate.FullName
      if (([string]$manifest.result -eq "pass_local_only") -and
          ([string]::IsNullOrWhiteSpace($ExpectedLaneId) -or [string]$manifest.lane_id -eq $ExpectedLaneId)) {
        return $candidate.FullName
      }
    } catch {
      continue
    }
  }
  return $null
}

if (!(Test-Path -LiteralPath $ProjectRoot)) {
  throw "Project root not found: $ProjectRoot"
}
$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)

$activeLanesPath = Join-Path $ProjectRoot "Workflows\base_generation\ACTIVE_LANES.json"
$activeLanes = Read-JsonFile -Path $activeLanesPath
$orderedLanes = @($activeLanes.lanes | Sort-Object order)
if ($orderedLanes.Count -eq 0) {
  throw "ACTIVE_LANES.json contains no lanes."
}

if ([string]::IsNullOrWhiteSpace($LaneId)) {
  $LaneId = [string]$orderedLanes[0].lane_id
}

$selectedLane = @($orderedLanes | Where-Object { [string]$_.lane_id -eq $LaneId } | Select-Object -First 1)
if ($selectedLane.Count -eq 0) {
  throw "Lane is not listed in ACTIVE_LANES.json: $LaneId"
}
$selectedLane = $selectedLane[0]

if ([string]::IsNullOrWhiteSpace($RunPackageManifestFile)) {
  $RunPackageManifestFile = Find-RunPackageManifest -ExpectedLaneId $LaneId
}
if ([string]::IsNullOrWhiteSpace($RunPackageManifestFile)) {
  throw "No passing run package manifest found for lane: $LaneId"
}
$RunPackageManifestFile = Resolve-ProjectPath -Path $RunPackageManifestFile
Assert-UnderProject -Path $RunPackageManifestFile
$runPackage = Read-JsonFile -Path $RunPackageManifestFile
if ([string]$runPackage.result -ne "pass_local_only") {
  throw "Run package manifest result must be pass_local_only: $RunPackageManifestFile"
}
if ([string]$runPackage.lane_id -ne $LaneId) {
  throw "Run package lane '$($runPackage.lane_id)' does not match requested lane '$LaneId'."
}

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
if ([string]::IsNullOrWhiteSpace($BundleName)) {
  $BundleName = "deploy_bundle_$($LaneId)_$stamp"
}
if ([string]::IsNullOrWhiteSpace($OutDir)) {
  $OutDir = Join-Path $ProjectRoot "runtime_artifacts\deploy_bundles\$BundleName"
}
$OutDir = [System.IO.Path]::GetFullPath($OutDir)
$contentRoot = Join-Path $OutDir "content"
$null = New-Item -ItemType Directory -Force -Path $contentRoot

$records = New-Object System.Collections.ArrayList

foreach ($requiredFile in @(
  "README.md",
  "PROJECT_ROOT_MANIFEST.json",
  "Workflows/base_generation/ACTIVE_LANES.json",
  "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/runtime_lane_queue.json"
)) {
  Copy-BundleFile -SourcePath (Resolve-ProjectPath -Path $requiredFile) -ContentRoot $contentRoot -Records $records -Required
}

Copy-BundleDirectory -SourceDir (Resolve-ProjectPath -Path "Workflows/base_generation/$LaneId") -ContentRoot $contentRoot -Records $records -Required
Copy-BundleDirectory -SourceDir (Resolve-ProjectPath -Path "Plan/07_IMPLEMENTATION/workflow_templates/base_generation/$LaneId") -ContentRoot $contentRoot -Records $records -Required
Copy-BundleDirectory -SourceDir (Resolve-ProjectPath -Path "Plan/Registries/Models") -ContentRoot $contentRoot -Records $records
Copy-BundleDirectory -SourceDir (Split-Path -Parent $RunPackageManifestFile) -ContentRoot $contentRoot -Records $records -Required
Copy-BundleDirectory -SourceDir (Resolve-ProjectPath -Path "configs/ec2") -ContentRoot $contentRoot -Records $records

if ($runPackage.prompt_profile -and $runPackage.prompt_profile.path) {
  Copy-BundleFile -SourcePath (Resolve-ProjectPath -Path ([string]$runPackage.prompt_profile.path)) -ContentRoot $contentRoot -Records $records
}

$gitHead = $null
$gitStatus = @()
try {
  $gitHead = (git -C $ProjectRoot rev-parse HEAD 2>$null | Select-Object -First 1)
  $gitStatus = @(git -C $ProjectRoot status --porcelain 2>$null)
} catch {
  $gitHead = $null
  $gitStatus = @("git_status_unavailable")
}

$manifest = [ordered]@{
  schema_version = "1.0"
  bundle_id = $BundleName
  created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  project_root = $ProjectRoot
  lane_id = $LaneId
  run_package_manifest = Convert-ToRepoPath -Path $RunPackageManifestFile
  source_git_head = $gitHead
  source_git_clean = (@($gitStatus).Count -eq 0)
  source_git_status_count = @($gitStatus).Count
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  comfyui_contacted = $false
  ec2_started = $false
  generation_executed = $false
  cost_controls = [ordered]@{
    prepared_while_ec2_stopped = $true
    git_lfs_required_by_bundle = $false
    direct_ec2_runtime_proof_required = $true
    direct_ec2_runtime_proof_reason = "Local/CI bundles reduce sync time but do not replace target EC2 A10G object-info, model path/hash, generation, pullback, and QA proof."
  }
  files = @($records | Sort-Object path)
  file_count = @($records).Count
  result = "pass_local_only"
  next_action = "Upload this bundle artifact to GitHub Actions/S3 before EC2 starts, then prefer bundle download on EC2 and skip Git LFS unless the selected lane explicitly requires it."
}

$contentManifestPath = Join-Path $contentRoot "DEPLOY_BUNDLE_MANIFEST.json"
Write-JsonNoBom -Value $manifest -Path $contentManifestPath -Depth 30

$zipPath = Join-Path $OutDir "$BundleName.zip"
if (Test-Path -LiteralPath $zipPath) {
  Remove-Item -LiteralPath $zipPath -Force
}
Compress-Archive -Path (Join-Path $contentRoot "*") -DestinationPath $zipPath -Force

$zipHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $zipPath).Hash.ToLowerInvariant()
$manifest.bundle_zip = Split-Path -Leaf $zipPath
$manifest.bundle_zip_sha256 = $zipHash
$manifest.bundle_zip_size_bytes = (Get-Item -LiteralPath $zipPath).Length

$sidecarManifestPath = Join-Path $OutDir "DEPLOY_BUNDLE_MANIFEST.json"
Write-JsonNoBom -Value $manifest -Path $sidecarManifestPath -Depth 30

$manifest | ConvertTo-Json -Depth 30
