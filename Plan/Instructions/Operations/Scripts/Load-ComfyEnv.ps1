<#
.SYNOPSIS
Loads C:\Comfy_UI_Main\.env into the current PowerShell process without printing secret values.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [switch]$Quiet
)

$envPath = Join-Path $ProjectRoot ".env"
if (-not (Test-Path $envPath)) {
  if (-not $Quiet) { Write-Host "No .env found at $envPath" }
  return
}

$loaded = @()
Get-Content $envPath | ForEach-Object {
  $line = $_.Trim()
  if ($line -eq "" -or $line.StartsWith("#")) { return }
  $parts = $line -split "=", 2
  if ($parts.Count -ne 2) { return }
  $name = $parts[0].Trim()
  $value = $parts[1].Trim().Trim('"').Trim("'")
  if ($name -ne "") {
    [Environment]::SetEnvironmentVariable($name, $value, "Process")
    $loaded += $name
  }
}

if (-not $Quiet) {
  foreach ($name in $loaded) {
    Write-Host "$name loaded: yes"
  }
}
