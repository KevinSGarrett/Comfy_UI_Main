param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main"
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem

$validator = Join-Path $ProjectRoot "Plan\Instructions\QA\Scripts\Test-EC2DeployBundleZipPortability.ps1"
if (!(Test-Path -LiteralPath $validator -PathType Leaf)) {
  throw "ZIP portability validator is missing: $validator"
}

$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("cu-zip-" + [guid]::NewGuid().ToString("N").Substring(0, 8))
$null = New-Item -ItemType Directory -Force -Path $tempRoot
$encoding = New-Object System.Text.UTF8Encoding($false)

function Get-TextSha256 {
  param([Parameter(Mandatory=$true)][string]$Value)

  $sha256 = [System.Security.Cryptography.SHA256]::Create()
  try {
    return ([System.BitConverter]::ToString($sha256.ComputeHash($encoding.GetBytes($Value)))).Replace("-", "").ToLowerInvariant()
  } finally {
    $sha256.Dispose()
  }
}

function New-TestCase {
  param(
    [Parameter(Mandatory=$true)][string]$Name,
    [Parameter(Mandatory=$true)][hashtable[]]$Entries,
    [Parameter(Mandatory=$true)][object[]]$ManifestFiles
  )

  $caseDir = Join-Path $tempRoot $Name
  $null = New-Item -ItemType Directory -Force -Path $caseDir
  $zipPath = Join-Path $caseDir "$Name.zip"
  $manifest = [ordered]@{
    schema_version = "1.0"
    files = @($ManifestFiles)
    file_count = @($ManifestFiles).Count
  }
  [System.IO.File]::WriteAllText((Join-Path $caseDir "DEPLOY_BUNDLE_MANIFEST.json"), ($manifest | ConvertTo-Json -Depth 10), $encoding)

  $fileStream = [System.IO.File]::Open($zipPath, [System.IO.FileMode]::CreateNew)
  $archive = New-Object System.IO.Compression.ZipArchive($fileStream, [System.IO.Compression.ZipArchiveMode]::Create, $false)
  try {
    foreach ($item in $Entries) {
      $entry = $archive.CreateEntry([string]$item.name)
      $writer = New-Object System.IO.StreamWriter($entry.Open(), $encoding)
      try {
        $writer.Write([string]$item.content)
      } finally {
        $writer.Dispose()
      }
    }
  } finally {
    $archive.Dispose()
    $fileStream.Dispose()
  }
  return $zipPath
}

$payload = "portable"
$payloadHash = Get-TextSha256 -Value $payload
$manifestFiles = @([ordered]@{ path = "file.txt"; size_bytes = $payload.Length; sha256 = $payloadHash })
$manifestEntry = @{ name = "DEPLOY_BUNDLE_MANIFEST.json"; content = "{}" }
$cases = @(
  [ordered]@{ name = "valid"; should_pass = $true; entries = @(@{ name = "file.txt"; content = $payload }, $manifestEntry); files = $manifestFiles },
  [ordered]@{ name = "backslash"; should_pass = $false; entries = @(@{ name = "dir\file.txt"; content = $payload }, $manifestEntry); files = $manifestFiles },
  [ordered]@{ name = "traversal"; should_pass = $false; entries = @(@{ name = "../file.txt"; content = $payload }, $manifestEntry); files = $manifestFiles },
  [ordered]@{ name = "duplicate"; should_pass = $false; entries = @(@{ name = "file.txt"; content = $payload }, @{ name = "FILE.TXT"; content = $payload }, $manifestEntry); files = $manifestFiles },
  [ordered]@{ name = "undeclared"; should_pass = $false; entries = @(@{ name = "file.txt"; content = $payload }, @{ name = "extra.txt"; content = $payload }, $manifestEntry); files = $manifestFiles },
  [ordered]@{ name = "hash_mismatch"; should_pass = $false; entries = @(@{ name = "file.txt"; content = "changed" }, $manifestEntry); files = $manifestFiles }
)

$results = New-Object System.Collections.ArrayList
try {
  foreach ($case in $cases) {
    $zipPath = New-TestCase -Name ([string]$case.name) -Entries @($case.entries) -ManifestFiles @($case.files)
    $passed = $false
    $message = ""
    try {
      $null = & $validator -BundleZip $zipPath
      $passed = $true
    } catch {
      $message = $_.Exception.Message
    }
    $expectationMet = $(if ([bool]$case.should_pass) { $passed } else { !$passed })
    [void]$results.Add([ordered]@{
      case = [string]$case.name
      should_pass = [bool]$case.should_pass
      validator_passed = $passed
      expectation_met = $expectationMet
      message = $message
    })
  }
} finally {
  Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}

$failed = @($results | Where-Object { !$_.expectation_met })
$report = [ordered]@{
  result = $(if ($failed.Count -eq 0) { "pass" } else { "fail" })
  classification = $(if ($failed.Count -eq 0) { "DEPLOY_BUNDLE_ZIP_PORTABILITY_REGRESSION_PASS" } else { "DEPLOY_BUNDLE_ZIP_PORTABILITY_REGRESSION_FAIL" })
  checked = $results.Count
  failed = $failed.Count
  cases = @($results)
}
$report | ConvertTo-Json -Depth 10
if ($failed.Count -gt 0) {
  throw "ZIP portability regression failed $($failed.Count) case(s)."
}
