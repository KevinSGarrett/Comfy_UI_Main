[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)]
  [string]$SourceRoot,

  [Parameter(Mandatory = $true)]
  [string]$SourceLabel,

  [Parameter(Mandatory = $true)]
  [string]$ArchiveFile,

  [Parameter(Mandatory = $true)]
  [string]$ManifestFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

function Get-Sha256 {
  param([Parameter(Mandatory = $true)][string]$Path)
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Get-ExclusionReason {
  param([Parameter(Mandatory = $true)][System.IO.FileInfo]$File)

  $segments = $File.FullName.Split([System.IO.Path]::DirectorySeparatorChar)
  foreach ($segment in $segments) {
    if ($segment -in @('.git', '__pycache__', 'cache', 'temp', 'tmp', 'secrets', 'private')) {
      return "excluded_directory:$segment"
    }
  }

  $extension = $File.Extension.ToLowerInvariant()
  if ($extension -in @('.pyc', '.pyo')) { return "generated_cache:$extension" }
  if ($extension -in @('.env', '.pem', '.key', '.p12', '.pfx')) { return "sensitive_extension:$extension" }
  if ($File.Name.ToLowerInvariant() -in @('id_rsa', 'id_ed25519')) { return 'sensitive_filename' }
  return $null
}

$source = (Resolve-Path -LiteralPath $SourceRoot).Path.TrimEnd('\')
$archiveFullPath = [System.IO.Path]::GetFullPath($ArchiveFile)
$manifestFullPath = [System.IO.Path]::GetFullPath($ManifestFile)
$archiveDirectory = Split-Path -Parent $archiveFullPath
$manifestDirectory = Split-Path -Parent $manifestFullPath
New-Item -ItemType Directory -Path $archiveDirectory -Force | Out-Null
New-Item -ItemType Directory -Path $manifestDirectory -Force | Out-Null

if (Test-Path -LiteralPath $archiveFullPath) {
  throw "Archive already exists: $archiveFullPath"
}

$partialPath = "$archiveFullPath.partial"
if (Test-Path -LiteralPath $partialPath) {
  Remove-Item -LiteralPath $partialPath -Force
}

$included = [System.Collections.Generic.List[object]]::new()
$excluded = [System.Collections.Generic.List[object]]::new()
$files = @(Get-ChildItem -LiteralPath $source -Recurse -File -Force | Sort-Object FullName)

foreach ($file in $files) {
  $relativePath = $file.FullName.Substring($source.Length).TrimStart('\').Replace('\', '/')
  $reason = Get-ExclusionReason -File $file
  if ($reason) {
    $excluded.Add([ordered]@{
      relative_path = $relativePath
      size_bytes = $file.Length
      reason = $reason
    })
    continue
  }

  $included.Add([ordered]@{
    file = $file
    relative_path = $relativePath
    size_bytes = $file.Length
    sha256 = Get-Sha256 -Path $file.FullName
  })
}

$stream = [System.IO.File]::Open($partialPath, [System.IO.FileMode]::CreateNew)
try {
  $zip = [System.IO.Compression.ZipArchive]::new(
    $stream,
    [System.IO.Compression.ZipArchiveMode]::Create,
    $false
  )
  try {
    foreach ($entry in $included) {
      $entryName = "$SourceLabel/$($entry.relative_path)"
      [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
        $zip,
        $entry.file.FullName,
        $entryName,
        [System.IO.Compression.CompressionLevel]::Optimal
      ) | Out-Null
    }
  }
  finally {
    $zip.Dispose()
  }
}
finally {
  $stream.Dispose()
}

Move-Item -LiteralPath $partialPath -Destination $archiveFullPath

$treeLines = foreach ($entry in $included) {
  "$($entry.relative_path)`0$($entry.size_bytes)`0$($entry.sha256)`n"
}
$treeBytes = [System.Text.Encoding]::UTF8.GetBytes(($treeLines -join ''))
$sha = [System.Security.Cryptography.SHA256]::Create()
try {
  $treeSha256 = ([System.BitConverter]::ToString($sha.ComputeHash($treeBytes))).Replace('-', '').ToLowerInvariant()
}
finally {
  $sha.Dispose()
}

$extensionSummary = @(
  $included |
    Group-Object { [System.IO.Path]::GetExtension($_.relative_path).ToLowerInvariant() } |
    Sort-Object Count -Descending |
    ForEach-Object {
      [ordered]@{
        extension = if ([string]::IsNullOrWhiteSpace($_.Name)) { '[no_extension]' } else { $_.Name }
        file_count = $_.Count
        size_bytes = [long](($_.Group | ForEach-Object { [long]$_['size_bytes'] } | Measure-Object -Sum).Sum)
      }
    }
)

$manifest = [ordered]@{
  schema_version = 1
  classification = 'LEGACY_SOURCE_ARCHIVE_QUARANTINED_NOT_RUNTIME_AUTHORITY'
  generated_at = (Get-Date).ToString('o')
  source_label = $SourceLabel
  source_root = $source
  archive_file = $archiveFullPath
  archive_size_bytes = (Get-Item -LiteralPath $archiveFullPath).Length
  archive_sha256 = Get-Sha256 -Path $archiveFullPath
  included_file_count = $included.Count
  included_size_bytes = [long](($included | ForEach-Object { [long]$_['size_bytes'] } | Measure-Object -Sum).Sum)
  included_tree_sha256 = $treeSha256
  excluded_file_count = $excluded.Count
  excluded_size_bytes = [long](($excluded | ForEach-Object { [long]$_['size_bytes'] } | Measure-Object -Sum).Sum)
  exclusions = $excluded
  extension_summary = $extensionSummary
  authority_boundary = [ordered]@{
    active_project_root = 'C:\Comfy_UI_Main'
    legacy_source_is_runtime_authority = $false
    archive_may_reopen_completed_work = $false
    archive_may_override_current_tracker_or_hydration = $false
    restore_requires_curated_review = $true
  }
}

$manifest | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $manifestFullPath -Encoding UTF8
Write-Output ($manifest | ConvertTo-Json -Depth 5)
