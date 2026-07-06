<#
.SYNOPSIS
Creates or validates a local EC2 artifact pullback record.

.DESCRIPTION
This helper implements the local side of EC2_TO_LOCAL_ARTIFACT_PULLBACK_PROTOCOL.md.
It does not contact AWS, start EC2, or copy artifacts. It inspects a local
pullback directory, hashes files, compares them to an optional remote artifact
manifest, and writes a PULLBACK_RECORD-style JSON file for downstream QA routing.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$RunId = "",
  [string]$LocalDestination = "",
  [string]$RemoteManifestFile = "",
  [string]$SourceInstance = "i-0560bf8d143f93bb1",
  [string]$SourceArtifactRoot = "",
  [string]$S3Prefix = "",
  [string]$OutFile = "",
  [switch]$DryRun
)

$ErrorActionPreference = "Stop"

function Get-RelativePathCompat {
  param(
    [string]$BasePath,
    [string]$TargetPath
  )

  $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
  $baseFull = [System.IO.Path]::GetFullPath($BasePath)
  if (!$baseFull.EndsWith($separator)) {
    $baseFull = "$baseFull$separator"
  }

  $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
  $baseUri = New-Object System.Uri($baseFull)
  $targetUri = New-Object System.Uri($targetFull)
  $relativeUri = $baseUri.MakeRelativeUri($targetUri)
  $relativePath = [System.Uri]::UnescapeDataString($relativeUri.ToString())
  return $relativePath.Replace("/", $separator)
}

function Get-FileSha256 {
  param([Parameter(Mandatory=$true)][string]$Path)

  $sha = [System.Security.Cryptography.SHA256]::Create()
  try {
    $stream = [System.IO.File]::OpenRead($Path)
    try {
      $hash = $sha.ComputeHash($stream)
      return -join ($hash | ForEach-Object { $_.ToString("x2") })
    } finally {
      $stream.Dispose()
    }
  } finally {
    $sha.Dispose()
  }
}

function Get-ArtifactType {
  param(
    [string]$RelativePath,
    [string]$Extension
  )

  $path = $RelativePath.Replace("\", "/").ToLowerInvariant()
  $ext = $Extension.ToLowerInvariant()

  if ($path -match '(^|/)logs?/') { return "log" }
  if ($path -match '(^|/)reports?/') { return "report" }
  if ($path -match '(^|/)workflows?/') { return "workflow" }
  if ($path -match '(^|/)images?/' -or $ext -in @(".png", ".jpg", ".jpeg", ".webp", ".bmp")) { return "image" }
  if ($path -match '(^|/)videos?/' -or $ext -in @(".mp4", ".mov", ".avi", ".webm", ".gif")) { return "video" }
  if ($path -match '(^|/)audio/' -or $ext -in @(".wav", ".flac", ".mp3", ".ogg", ".m4a")) { return "audio" }
  if ($ext -eq ".json") { return "json" }
  return "other"
}

function Test-QaRequired {
  param([string]$ArtifactType)
  return $ArtifactType -in @("image", "video", "audio", "log", "report", "workflow", "json")
}

function ConvertTo-ProjectRelativePath {
  param(
    [string]$BasePath,
    [string]$TargetPath
  )

  $relative = Get-RelativePathCompat -BasePath $BasePath -TargetPath $TargetPath
  return $relative.Replace("\", "/")
}

function Read-RemoteManifest {
  param([string]$Path)

  if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
  if (!(Test-Path -LiteralPath $Path)) { throw "Remote manifest file not found: $Path" }
  return Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json
}

if ([string]::IsNullOrWhiteSpace($RunId)) {
  if ($DryRun) {
    $RunId = "pending_runtime_pullback"
  } elseif (![string]::IsNullOrWhiteSpace($LocalDestination)) {
    $trimmedDestination = [System.IO.Path]::GetFullPath($LocalDestination).TrimEnd([char[]]@("\", "/"))
    $RunId = Split-Path -Leaf $trimmedDestination
  } else {
    throw "RunId is required when LocalDestination is not supplied."
  }
}

$defaultDestination = Join-Path $ProjectRoot "Plan\Instructions\Operations\Pulled_Back_Artifacts\$RunId"
if ([string]::IsNullOrWhiteSpace($LocalDestination)) {
  $LocalDestination = $defaultDestination
}

$remoteManifest = Read-RemoteManifest -Path $RemoteManifestFile
$files = @()
$errors = @()
$remoteFiles = @{}
$hashMismatch = @()
$sizeMismatch = @()
$missingLocal = @()

if ($null -ne $remoteManifest) {
  foreach ($file in @($remoteManifest.files)) {
    $remoteRelative = ([string]$file.relative_path).Replace("\", "/").TrimStart(".").TrimStart("/")
    if (![string]::IsNullOrWhiteSpace($remoteRelative)) {
      $remoteFiles[$remoteRelative] = $file
    }
  }
}

if (!$DryRun) {
  if (!(Test-Path -LiteralPath $LocalDestination)) {
    throw "Local pullback destination not found: $LocalDestination"
  }

  $localRoot = [System.IO.Path]::GetFullPath($LocalDestination)
  foreach ($fileInfo in Get-ChildItem -LiteralPath $LocalDestination -Recurse -File) {
    if ($fileInfo.Name -eq "PULLBACK_RECORD.json") { continue }
    if ($fileInfo.Name -eq "REMOTE_ARTIFACT_MANIFEST.json") { continue }
    $relativePath = ConvertTo-ProjectRelativePath -BasePath $localRoot -TargetPath $fileInfo.FullName
    $artifactType = Get-ArtifactType -RelativePath $relativePath -Extension $fileInfo.Extension
    $sha = Get-FileSha256 -Path $fileInfo.FullName
    $remote = $null
    if ($remoteFiles.ContainsKey($relativePath)) {
      $remote = $remoteFiles[$relativePath]
      if ($null -ne $remote.size_bytes -and [int64]$remote.size_bytes -ne [int64]$fileInfo.Length) {
        $sizeMismatch += $relativePath
      }
      if (![string]::IsNullOrWhiteSpace([string]$remote.sha256) -and [string]$remote.sha256 -ne $sha) {
        $hashMismatch += $relativePath
      }
    }

    $files += [ordered]@{
      relative_path = $relativePath
      local_path = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $fileInfo.FullName
      size_bytes = [int64]$fileInfo.Length
      sha256 = $sha
      artifact_type = $artifactType
      qa_required = Test-QaRequired -ArtifactType $artifactType
      remote_manifest_match = ($null -ne $remote)
    }
  }

  foreach ($remoteRelative in $remoteFiles.Keys) {
    if (($files | Where-Object { $_.relative_path -eq $remoteRelative }).Count -eq 0) {
      $missingLocal += $remoteRelative
    }
  }
} else {
  $errors += "dry_run_no_artifacts_inspected"
}

if ($hashMismatch.Count -gt 0) { $errors += "hash_mismatch: $($hashMismatch -join '; ')" }
if ($sizeMismatch.Count -gt 0) { $errors += "size_mismatch: $($sizeMismatch -join '; ')" }
if ($missingLocal.Count -gt 0) { $errors += "missing_local_files: $($missingLocal -join '; ')" }

$qaRequiredFiles = @($files | Where-Object { $_.qa_required } | ForEach-Object { $_.local_path })
$remoteFileCount = $(if ($null -ne $remoteManifest) { @($remoteManifest.files).Count } else { $null })
$localFileCount = @($files).Count
$hashesVerified = $false
if ($null -ne $remoteManifest -and $remoteFileCount -eq $localFileCount -and $hashMismatch.Count -eq 0 -and $sizeMismatch.Count -eq 0 -and $missingLocal.Count -eq 0) {
  $hashesVerified = $true
}

$status = "pending_runtime_artifacts"
if (!$DryRun) {
  if ($errors.Count -gt 0) {
    $status = "pullback_validation_failed"
  } elseif ($null -eq $remoteManifest) {
    $status = "local_inventory_created_remote_manifest_missing"
  } elseif ($hashesVerified) {
    $status = "pullback_hashes_verified"
  } else {
    $status = "pullback_pending_verification"
  }
}

$record = [ordered]@{
  run_id = $RunId
  evidence_id = "EC2-PULLBACK-RECORD-" + (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  mode = $(if ($DryRun) { "dry_run" } else { "local_inventory" })
  status = $status
  source_instance = $SourceInstance
  source_artifact_root = $SourceArtifactRoot
  s3_prefix = $S3Prefix
  local_destination = ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $LocalDestination
  remote_manifest_file = $(if ([string]::IsNullOrWhiteSpace($RemoteManifestFile)) { $null } else { ConvertTo-ProjectRelativePath -BasePath $ProjectRoot -TargetPath $RemoteManifestFile })
  file_count_remote = $remoteFileCount
  file_count_local = $localFileCount
  hashes_verified = $hashesVerified
  qa_required_files = $qaRequiredFiles
  qa_completed_files = @()
  files = $files
  errors = $errors
  next_action = $(if ($DryRun) { "Run after EC2 workflow execution and artifact pullback." } elseif ($qaRequiredFiles.Count -gt 0) { "Route qa_required_files through the relevant Wave 61 QA protocols." } else { "Attach remote manifest or rerun after artifacts are pulled back." })
}

if ([string]::IsNullOrWhiteSpace($OutFile)) {
  if ($DryRun) {
    $outStamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
    $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Runtime_Readiness\W60_EC2_PULLBACK_RECORD_DRY_RUN_$outStamp.json"
  } else {
    $OutFile = Join-Path $LocalDestination "PULLBACK_RECORD.json"
  }
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}

$record | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $OutFile -Encoding UTF8
Write-Host "Wrote EC2 pullback record: $OutFile"
$record | ConvertTo-Json -Depth 20

if (!$DryRun -and $errors.Count -gt 0) { exit 2 }
