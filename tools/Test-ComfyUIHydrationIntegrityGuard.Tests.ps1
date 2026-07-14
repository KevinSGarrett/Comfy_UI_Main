[CmdletBinding()]
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$guard = Join-Path $ProjectRoot "tools\Test-ComfyUIHydrationIntegrityGuard.ps1"
$repair = Join-Path $ProjectRoot "tools\Repair-ComfyUIHydrationCorruption.ps1"
$issues = [Collections.Generic.List[string]]::new()
$roots = [Collections.Generic.List[string]]::new()

function New-TestRoot([string]$label) {
  $root = Join-Path $ProjectRoot ("runtime_artifacts\hydration_guard_tests\{0}_{1}" -f $label, [guid]::NewGuid().ToString("N"))
  New-Item -ItemType Directory -Path (Join-Path $root "Plan\Instructions\Hydration_Rehydration") -Force | Out-Null
  $roots.Add($root)
  return $root
}

function Write-Utf8([string]$path, [string]$text) {
  [IO.File]::WriteAllText($path, $text, (New-Object Text.UTF8Encoding($false)))
}

try {
  $root = New-TestRoot "pass"
  Write-Utf8 (Join-Path $root "Plan\Instructions\Hydration_Rehydration\STATE.md") "# State`nCompact and valid.`n"
  $result = (& $guard -ProjectRoot $root -MaxFileBytes 1024 -MaxLineCharacters 256 -NoExit) | ConvertFrom-Json
  if (!$result.pass) { $issues.Add("valid_fixture_failed") }

  $root = New-TestRoot "oversized"
  Write-Utf8 (Join-Path $root "Plan\Instructions\Hydration_Rehydration\STATE.md") ("x" * 1100)
  $result = (& $guard -ProjectRoot $root -MaxFileBytes 1024 -MaxLineCharacters 256 -NoExit) | ConvertFrom-Json
  if (!@($result.issues | Where-Object { $_ -like "file_too_large:*" }).Count) { $issues.Add("oversized_fixture_not_detected") }

  $root = New-TestRoot "long_line"
  Write-Utf8 (Join-Path $root "Plan\Instructions\Hydration_Rehydration\STATE.md") ("x" * 300)
  $result = (& $guard -ProjectRoot $root -MaxFileBytes 1024 -MaxLineCharacters 256 -NoExit) | ConvertFrom-Json
  if (!@($result.issues | Where-Object { $_ -like "line_too_long:*" }).Count) { $issues.Add("long_line_fixture_not_detected") }

  $root = New-TestRoot "mojibake"
  $bad = "bad " + [char]0x00C3 + [char]0x00A2
  Write-Utf8 (Join-Path $root "Plan\Instructions\Hydration_Rehydration\STATE.md") $bad
  $result = (& $guard -ProjectRoot $root -MaxFileBytes 1024 -MaxLineCharacters 256 -NoExit) | ConvertFrom-Json
  if (!@($result.issues | Where-Object { $_ -like "mojibake_signature:*" }).Count) { $issues.Add("mojibake_fixture_not_detected") }

  $root = New-TestRoot "invalid_utf8"
  $nested = Join-Path $root "Plan\Instructions\Hydration_Rehydration\nested"
  New-Item -ItemType Directory -Path $nested -Force | Out-Null
  [IO.File]::WriteAllBytes((Join-Path $nested "STATE.md"), [byte[]](0xC3, 0x28))
  $result = (& $guard -ProjectRoot $root -MaxFileBytes 1024 -MaxLineCharacters 256 -NoExit) | ConvertFrom-Json
  if (!@($result.issues | Where-Object { $_ -like "invalid_utf8:*nested*" }).Count) { $issues.Add("nested_invalid_utf8_fixture_not_detected") }

  $root = New-TestRoot "repair_preflight"
  $hydrationRoot = Join-Path $root "Plan\Instructions\Hydration_Rehydration"
  $current = Join-Path $hydrationRoot "CURRENT_SESSION_STATE.md"
  $resume = Join-Path $hydrationRoot "RESUME_HERE_NEXT_CODEX_SESSION.md"
  Write-Utf8 $current "original current"
  Write-Utf8 $resume "original resume"
  $goodReplacement = Join-Path $root "good.md"
  $badReplacement = Join-Path $root "bad.md"
  Write-Utf8 $goodReplacement "valid compact replacement"
  Write-Utf8 $badReplacement ("bad " + [char]0x00C3 + [char]0x00A2)
  $currentHash = (Get-FileHash -LiteralPath $current -Algorithm SHA256).Hash
  $resumeHash = (Get-FileHash -LiteralPath $resume -Algorithm SHA256).Hash
  $repairRejected = $false
  try {
    & $repair -ProjectRoot $root -CurrentSessionReplacementPath $badReplacement -ResumeReplacementPath $goodReplacement -ArchiveRoot (Join-Path $root "archive") -EvidenceOutputPath (Join-Path $root "evidence.json") | Out-Null
  } catch {
    $repairRejected = $true
  }
  if (!$repairRejected) { $issues.Add("repair_mojibake_preflight_not_rejected") }
  if ((Get-FileHash -LiteralPath $current -Algorithm SHA256).Hash -ne $currentHash -or (Get-FileHash -LiteralPath $resume -Algorithm SHA256).Hash -ne $resumeHash) {
    $issues.Add("repair_preflight_mutated_targets")
  }
} catch {
  $issues.Add("guard_fixture_execution_failed:$($_.Exception.Message)")
} finally {
  foreach ($root in $roots) {
    if (Test-Path -LiteralPath $root) { Remove-Item -LiteralPath $root -Recurse -Force }
  }
}

$result = [ordered]@{
  schema_version = "1.0"
  classification = if ($issues.Count) { "HYDRATION_GUARD_TESTS_FAIL" } else { "HYDRATION_GUARD_TESTS_PASS" }
  pass = $issues.Count -eq 0
  issue_count = $issues.Count
  issues = @($issues)
}
$json = $result | ConvertTo-Json -Depth 5
if ($OutFile) {
  $parent = Split-Path -Parent $OutFile
  if ($parent -and !(Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
  [IO.File]::WriteAllText($OutFile, $json, (New-Object Text.UTF8Encoding($false)))
}
$json
if ($issues.Count) { exit 1 }
