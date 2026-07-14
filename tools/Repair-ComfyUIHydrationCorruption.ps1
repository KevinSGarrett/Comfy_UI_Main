[CmdletBinding()]
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [Parameter(Mandatory = $true)][string]$CurrentSessionReplacementPath,
  [Parameter(Mandatory = $true)][string]$ResumeReplacementPath,
  [string]$ArchiveRoot = "",
  [string]$EvidenceOutputPath = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$stamp = Get-Date -Format "yyyyMMddTHHmmssK"
if ([string]::IsNullOrWhiteSpace($ArchiveRoot)) {
  $ArchiveRoot = Join-Path $ProjectRoot ("runtime_artifacts\hydration_corruption_archive\" + $stamp.Replace(":", ""))
}
if ([string]::IsNullOrWhiteSpace($EvidenceOutputPath)) {
  $EvidenceOutputPath = Join-Path $ProjectRoot ("Plan\Instructions\QA\Evidence\Delivery_Recovery\HYDRATION_COMPACT_REPAIR_" + $stamp.Replace(":", "") + ".json")
}

$targets = @(
  [ordered]@{
    name = "CURRENT_SESSION_STATE.md"
    target = Join-Path $ProjectRoot "Plan\Instructions\Hydration_Rehydration\CURRENT_SESSION_STATE.md"
    replacement = (Resolve-Path -LiteralPath $CurrentSessionReplacementPath).Path
  },
  [ordered]@{
    name = "RESUME_HERE_NEXT_CODEX_SESSION.md"
    target = Join-Path $ProjectRoot "Plan\Instructions\Hydration_Rehydration\RESUME_HERE_NEXT_CODEX_SESSION.md"
    replacement = (Resolve-Path -LiteralPath $ResumeReplacementPath).Path
  }
)

$utf8 = New-Object Text.UTF8Encoding($false, $true)
foreach ($item in $targets) {
  if (!(Test-Path -LiteralPath $item.target -PathType Leaf)) { throw "Hydration target missing: $($item.target)" }
  $replacementInfo = Get-Item -LiteralPath $item.replacement
  if ($replacementInfo.Length -gt 2097152) { throw "Replacement is too large: $($item.replacement)" }
  $text = [IO.File]::ReadAllText($item.replacement, $utf8)
  if (@([regex]::Split($text, "\r?\n") | Where-Object { $_.Length -gt 32768 }).Count) { throw "Replacement contains an oversized line: $($item.replacement)" }
  $replacementCharacter = [string][char]0xFFFD
  $latinCapitalAWithTilde = [string][char]0x00C3
  $latinCapitalAWithCircumflex = [string][char]0x00C2
  $latinSmallAWithCircumflex = [string][char]0x00E2
  if ($text.Contains($replacementCharacter) -or $text.Contains($latinCapitalAWithTilde) -or $text.Contains($latinCapitalAWithCircumflex) -or $text.Contains($latinSmallAWithCircumflex + [char]0x20AC)) {
    throw "Replacement contains a mojibake signature: $($item.replacement)"
  }
}

New-Item -ItemType Directory -Path $ArchiveRoot -Force | Out-Null
$records = [Collections.Generic.List[object]]::new()
foreach ($item in $targets) {
  $sourceInfo = Get-Item -LiteralPath $item.target
  $sourceHash = (Get-FileHash -LiteralPath $item.target -Algorithm SHA256).Hash.ToLowerInvariant()
  $archivePath = Join-Path $ArchiveRoot ($item.name + ".gz")
  $input = [IO.File]::OpenRead($item.target)
  try {
    $output = [IO.File]::Create($archivePath)
    try {
      $gzip = New-Object IO.Compression.GZipStream($output, [IO.Compression.CompressionMode]::Compress, $true)
      try { $input.CopyTo($gzip) } finally { $gzip.Dispose() }
    } finally { $output.Dispose() }
  } finally { $input.Dispose() }
  $records.Add([ordered]@{
      path = $item.target.Substring($ProjectRoot.Length).TrimStart("\").Replace("\", "/")
      original_bytes = $sourceInfo.Length
      original_sha256 = $sourceHash
      archive_path = $archivePath.Substring($ProjectRoot.Length).TrimStart("\").Replace("\", "/")
      archive_bytes = (Get-Item -LiteralPath $archivePath).Length
      archive_sha256 = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
      replacement_source_sha256 = (Get-FileHash -LiteralPath $item.replacement -Algorithm SHA256).Hash.ToLowerInvariant()
    })
}

foreach ($item in $targets) {
  [IO.File]::WriteAllBytes($item.target, [IO.File]::ReadAllBytes($item.replacement))
}
for ($index = 0; $index -lt $targets.Count; $index++) {
  $records[$index].replacement_bytes = (Get-Item -LiteralPath $targets[$index].target).Length
  $records[$index].replacement_sha256 = (Get-FileHash -LiteralPath $targets[$index].target -Algorithm SHA256).Hash.ToLowerInvariant()
}

$evidence = [ordered]@{
  schema_version = "1.0"
  created_iso = (Get-Date).ToString("o")
  classification = "HYDRATION_COMPACT_REPAIR_ARCHIVE_FIRST_PASS"
  project_root = $ProjectRoot.Replace("\", "/")
  archive_preserves_exact_pre_repair_bytes = $true
  records = @($records)
  next_action = "Run Test-ComfyUIHydrationIntegrityGuard.ps1 and keep future hydration updates compact."
}
$parent = Split-Path -Parent $EvidenceOutputPath
if (!(Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
[IO.File]::WriteAllText($EvidenceOutputPath, ($evidence | ConvertTo-Json -Depth 8), (New-Object Text.UTF8Encoding($false)))
$evidence | ConvertTo-Json -Depth 8
