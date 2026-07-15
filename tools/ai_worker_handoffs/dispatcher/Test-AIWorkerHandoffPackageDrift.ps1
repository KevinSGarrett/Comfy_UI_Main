[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$PackageRoot,
  [string]$CodexHome = "C:\Users\kevin\.codex"
)

$ErrorActionPreference = "Stop"
$canonicalVerifier = Join-Path $PackageRoot "Test-AIWorkerHandoffPackageDrift.ps1"
if (!(Test-Path -LiteralPath $canonicalVerifier -PathType Leaf)) {
  throw "Canonical package drift verifier missing: $canonicalVerifier"
}

& $canonicalVerifier -PackageRoot $PackageRoot -CodexHome $CodexHome
