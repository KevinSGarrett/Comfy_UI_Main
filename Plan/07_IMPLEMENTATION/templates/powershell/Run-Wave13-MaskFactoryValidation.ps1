param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$ContractPath = "",
  [string]$WorkflowPath = ""
)

$ErrorActionPreference = "Stop"

Write-Host "Wave13 Mask Factory validation"
Write-Host "ProjectRoot: $ProjectRoot"

$ScriptRoot = Join-Path $ProjectRoot "07_IMPLEMENTATION\scripts"
$Runner = Join-Path $ScriptRoot "run_wave13_local_validation.py"

if (!(Test-Path $Runner)) {
  throw "Missing runner: $Runner"
}

$args = @("--project-root", $ProjectRoot)

if ($ContractPath -ne "") {
  $args += @("--contract", $ContractPath)
}

if ($WorkflowPath -ne "") {
  $args += @("--workflow", $WorkflowPath)
}

python $Runner @args
