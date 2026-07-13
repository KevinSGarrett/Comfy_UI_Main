<#
.SYNOPSIS
Fails when a tracked path would exceed the configured Windows checkout budget.
#>
param(
  [string]$ProjectRoot = "",
  [string]$CheckoutRoot = "D:\a\Comfy_UI_Main\Comfy_UI_Main",
  [ValidateRange(1, 32767)]
  [int]$MaxPathLength = 249,
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
if ([string]::IsNullOrWhiteSpace($ProjectRoot)) {
  $ProjectRoot = Join-Path $PSScriptRoot ".."
}
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$trackedPaths = @(& git -C $ProjectRoot ls-files)
if ($LASTEXITCODE -ne 0) {
  throw "Unable to enumerate tracked files with git ls-files."
}

$measurements = @($trackedPaths | ForEach-Object {
  $relativePath = ([string]$_).Replace("/", [IO.Path]::DirectorySeparatorChar)
  $fullPath = $CheckoutRoot.TrimEnd("\", "/") + [IO.Path]::DirectorySeparatorChar + $relativePath
  [pscustomobject][ordered]@{
    relative_path = ([string]$_).Replace("\", "/")
    projected_full_path_length = $fullPath.Length
  }
})
$violations = @($measurements | Where-Object { $_.projected_full_path_length -gt $MaxPathLength } | Sort-Object projected_full_path_length -Descending)
$maximum = $measurements | Sort-Object projected_full_path_length -Descending | Select-Object -First 1

$record = [ordered]@{
  artifact_type = "windows_checkout_path_budget"
  created_at = (Get-Date).ToString("o")
  checkout_root = $CheckoutRoot
  max_path_length = $MaxPathLength
  tracked_file_count = $trackedPaths.Count
  maximum_projected_path = $maximum
  violation_count = $violations.Count
  violations = $violations
  result = $(if ($violations.Count -eq 0) { "pass" } else { "fail" })
}

if (![string]::IsNullOrWhiteSpace($OutFile)) {
  $parent = Split-Path -Parent $OutFile
  if (![string]::IsNullOrWhiteSpace($parent)) {
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
  }
  [IO.File]::WriteAllText($OutFile, ($record | ConvertTo-Json -Depth 8), (New-Object Text.UTF8Encoding($false)))
}

$record | ConvertTo-Json -Depth 8
if ($violations.Count -gt 0) {
  throw "Windows checkout path budget failed with $($violations.Count) violation(s)."
}
