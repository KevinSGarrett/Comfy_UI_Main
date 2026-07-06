param(
  [Parameter(Mandatory=$true)][string]$ZipPath
)

if (!(Test-Path $ZipPath)) {
  throw "Zip not found: $ZipPath"
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
try {
  $names = $zip.Entries | ForEach-Object { $_.FullName }
  $required = @(
    "Comfy_UI_Main/Plan/Instructions/AUTONOMOUS_CODEX_DESKTOP_MASTER_MANUAL.md",
    "Comfy_UI_Main/Plan/Instructions/Indexes/MASTER_PROJECT_LOCATION_INDEX.md",
    "Comfy_UI_Main/Plan/Instructions/Operations/GITHUB_MINIMAL_PERSONAL_PROJECT_PROTOCOL.md",
    "Comfy_UI_Main/Plan/Instructions/QA/STRICT_AUTONOMOUS_QA_MASTER_PROTOCOL.md",
    "Comfy_UI_Main/Plan/Instructions/Hydration_Rehydration/SESSION_START_REHYDRATION_CHECKLIST.md",
    "Comfy_UI_Main/Plan/Instructions/Hydration_Rehydration/WAVE58_62_FINAL_COMPLETION_CERTIFICATION.md"
  )
  $missing = @()
  foreach ($r in $required) {
    if ($names -notcontains $r) { $missing += $r }
  }
  if ($missing.Count -gt 0) {
    Write-Error ("Missing required files:`n" + ($missing -join "`n"))
    exit 1
  }
  Write-Host "Cumulative pack validation passed."
}
finally {
  $zip.Dispose()
}
