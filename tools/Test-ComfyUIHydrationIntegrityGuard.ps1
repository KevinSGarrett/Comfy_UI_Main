[CmdletBinding()]
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [ValidateRange(1024, 16777216)][int64]$MaxFileBytes = 2097152,
  [ValidateRange(256, 1048576)][int]$MaxLineCharacters = 32768,
  [switch]$NoExit
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$hydrationRoot = Join-Path $ProjectRoot "Plan\Instructions\Hydration_Rehydration"
$issues = [Collections.Generic.List[string]]::new()
$filesChecked = 0
$utf8 = New-Object Text.UTF8Encoding($false, $true)

if (!(Test-Path -LiteralPath $hydrationRoot -PathType Container)) {
  $issues.Add("hydration_root_missing")
} else {
  $textExtensions = @(".md", ".txt", ".json", ".yaml", ".yml", ".csv")
  foreach ($file in @(Get-ChildItem -LiteralPath $hydrationRoot -File -Recurse | Where-Object { $_.Extension.ToLowerInvariant() -in $textExtensions } | Sort-Object FullName)) {
    $filesChecked++
    $relativeName = $file.FullName.Substring($hydrationRoot.Length).TrimStart("\")
    if ($file.Length -gt $MaxFileBytes) {
      $issues.Add("file_too_large:${relativeName}:$($file.Length)")
      continue
    }
    try {
      $text = [IO.File]::ReadAllText($file.FullName, $utf8)
    } catch {
      $issues.Add("invalid_utf8:$relativeName")
      continue
    }
    $lineNumber = 0
    foreach ($line in [regex]::Split($text, "\r?\n")) {
      $lineNumber++
      if ($line.Length -gt $MaxLineCharacters) {
        $issues.Add("line_too_long:${relativeName}:${lineNumber}:$($line.Length)")
        break
      }
    }
    $replacementCharacter = [string][char]0xFFFD
    $latinCapitalAWithTilde = [string][char]0x00C3
    $latinCapitalAWithCircumflex = [string][char]0x00C2
    $latinSmallAWithCircumflex = [string][char]0x00E2
    if ($text.Contains($replacementCharacter) -or $text.Contains($latinCapitalAWithTilde) -or $text.Contains($latinCapitalAWithCircumflex) -or $text.Contains($latinSmallAWithCircumflex + [char]0x20AC)) {
      $issues.Add("mojibake_signature:$relativeName")
    }
  }
}

$result = [ordered]@{
  schema_version = "1.0"
  generated_at = (Get-Date).ToString("o")
  classification = if ($issues.Count) { "HYDRATION_INTEGRITY_FAIL" } else { "HYDRATION_INTEGRITY_PASS" }
  pass = $issues.Count -eq 0
  hydration_root = $hydrationRoot.Replace("\", "/")
  files_checked = $filesChecked
  max_file_bytes = $MaxFileBytes
  max_line_characters = $MaxLineCharacters
  issue_count = $issues.Count
  issues = @($issues)
}
$result | ConvertTo-Json -Depth 6
if ($issues.Count -and !$NoExit) { exit 1 }
