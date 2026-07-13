param(
  [Parameter(Mandatory=$true)][string]$BundleZip,
  [string]$ManifestFile = ""
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

if (!(Test-Path -LiteralPath $BundleZip -PathType Leaf)) {
  throw "Deploy bundle ZIP is missing: $BundleZip"
}
if ([string]::IsNullOrWhiteSpace($ManifestFile)) {
  $ManifestFile = Join-Path (Split-Path -Parent $BundleZip) "DEPLOY_BUNDLE_MANIFEST.json"
}
if (!(Test-Path -LiteralPath $ManifestFile -PathType Leaf)) {
  throw "Deploy bundle sidecar manifest is missing: $ManifestFile"
}

$manifest = Get-Content -Raw -LiteralPath $ManifestFile | ConvertFrom-Json
$recordedZipHash = ([string]$manifest.bundle_zip_sha256).Trim().ToLowerInvariant()
if (![string]::IsNullOrWhiteSpace($recordedZipHash)) {
  $actualZipHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $BundleZip).Hash.ToLowerInvariant()
  if ($recordedZipHash -notmatch '^[0-9a-f]{64}$' -or $actualZipHash -cne $recordedZipHash) {
    throw "Deploy bundle ZIP hash does not match the sidecar manifest."
  }
}
$expected = New-Object 'System.Collections.Generic.Dictionary[string,string]' ([System.StringComparer]::OrdinalIgnoreCase)
foreach ($record in @($manifest.files)) {
  $path = ([string]$record.path).Replace("\", "/")
  if ([string]::IsNullOrWhiteSpace($path) -or
      $path.Contains("\") -or
      $path.StartsWith("/") -or
      $path -match '^[A-Za-z]:' -or
      @($path.Split("/") | Where-Object { $_ -in @("", ".", "..") }).Count -gt 0) {
    throw "Manifest contains an unsafe or non-portable path: $path"
  }
  if ($expected.ContainsKey($path)) {
    throw "Manifest contains a duplicate normalized path: $path"
  }
  $hash = ([string]$record.sha256).Trim().ToLowerInvariant()
  if ($hash -notmatch '^[0-9a-f]{64}$') {
    throw "Manifest contains an invalid SHA-256 for: $path"
  }
  $expected.Add($path, $hash)
}
if ($expected.Count -ne [int]$manifest.file_count) {
  throw "Manifest file_count does not match its unique file records."
}

$stream = [System.IO.File]::OpenRead((Resolve-Path -LiteralPath $BundleZip).Path)
$archive = New-Object System.IO.Compression.ZipArchive($stream, [System.IO.Compression.ZipArchiveMode]::Read, $false)
$observed = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::OrdinalIgnoreCase)
try {
  foreach ($entry in @($archive.Entries)) {
    $entryName = [string]$entry.FullName
    if ([string]::IsNullOrWhiteSpace($entryName) -or
        $entryName.Contains("\") -or
        $entryName.StartsWith("/") -or
        $entryName -match '^[A-Za-z]:' -or
        @($entryName.Split("/") | Where-Object { $_ -in @("", ".", "..") }).Count -gt 0) {
      throw "ZIP contains an unsafe or non-portable entry: $entryName"
    }
    if (!$observed.Add($entryName)) {
      throw "ZIP contains a duplicate normalized entry: $entryName"
    }
    if ($entryName -eq "DEPLOY_BUNDLE_MANIFEST.json") {
      continue
    }
    if (!$expected.ContainsKey($entryName)) {
      throw "ZIP contains an entry absent from the manifest: $entryName"
    }

    $entryStream = $entry.Open()
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
      $actualHash = ([System.BitConverter]::ToString($sha256.ComputeHash($entryStream))).Replace("-", "").ToLowerInvariant()
    } finally {
      $sha256.Dispose()
      $entryStream.Dispose()
    }
    if ($actualHash -cne $expected[$entryName]) {
      throw "ZIP entry hash does not match the manifest for: $entryName"
    }
  }
} finally {
  $archive.Dispose()
  $stream.Dispose()
}

if (!$observed.Contains("DEPLOY_BUNDLE_MANIFEST.json")) {
  throw "ZIP is missing DEPLOY_BUNDLE_MANIFEST.json."
}
foreach ($path in $expected.Keys) {
  if (!$observed.Contains($path)) {
    throw "Manifest path is missing from ZIP: $path"
  }
}

[ordered]@{
  result = "pass"
  classification = "DEPLOY_BUNDLE_ZIP_PORTABILITY_PASS"
  zip_path = (Resolve-Path -LiteralPath $BundleZip).Path
  manifest_path = (Resolve-Path -LiteralPath $ManifestFile).Path
  declared_file_count = $expected.Count
  observed_entry_count = $observed.Count
  entry_separator = "/"
  unsafe_entry_count = 0
  duplicate_normalized_entry_count = 0
  manifest_entry_mismatch_count = 0
} | ConvertTo-Json -Depth 5
