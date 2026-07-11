param(
  [string]$Root = "."
)

$ErrorActionPreference = "Stop"

try {
  $resolvedRoot = Resolve-Path -LiteralPath $Root -ErrorAction Stop
} catch {
  Write-Error "Root path could not be resolved: $Root"
  exit 1
}

$validatorPath = Join-Path -Path $resolvedRoot.Path -ChildPath "Plan/07_IMPLEMENTATION/scripts/run_wave30_local_validation.py"
if (-not (Test-Path -LiteralPath $validatorPath -PathType Leaf)) {
  Write-Error "Missing validator script: $validatorPath"
  exit 1
}

& python $validatorPath --root $resolvedRoot.Path
$exitCode = $LASTEXITCODE
if ($null -eq $exitCode) {
  $exitCode = 1
}
exit $exitCode
