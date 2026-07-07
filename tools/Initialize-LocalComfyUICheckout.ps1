<#
.SYNOPSIS
Bootstraps an ignored local ComfyUI checkout for low-cost development checks.

.DESCRIPTION
Dry-run by default. With -Execute, clones the ComfyUI source tree into the
project-local external runtime folder when it is absent. This helper never
downloads model binaries, never starts EC2, and never replaces EC2 target proof.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$LocalComfyRoot = "",
  [string]$ComfyRepoUrl = "https://github.com/comfyanonymous/ComfyUI.git",
  [string]$Branch = "",
  [string]$OutFile = "",
  [switch]$Execute
)

$ErrorActionPreference = "Stop"

function Write-JsonNoBom {
  param(
    [Parameter(Mandatory=$true)][object]$Value,
    [Parameter(Mandatory=$true)][string]$Path,
    [int]$Depth = 20
  )
  $encoding = New-Object System.Text.UTF8Encoding($false)
  [System.IO.File]::WriteAllText($Path, ($Value | ConvertTo-Json -Depth $Depth), $encoding)
}

function ConvertTo-RelativePath {
  param([string]$BasePath, [string]$TargetPath)
  try {
    $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
    $baseFull = [System.IO.Path]::GetFullPath($BasePath)
    if (!$baseFull.EndsWith($separator)) { $baseFull = "$baseFull$separator" }
    $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
    $baseUri = New-Object System.Uri($baseFull)
    $targetUri = New-Object System.Uri($targetFull)
    return [System.Uri]::UnescapeDataString($baseUri.MakeRelativeUri($targetUri).ToString()).Replace("/", "\")
  } catch {
    return $TargetPath
  }
}

if (!(Test-Path -LiteralPath $ProjectRoot)) {
  throw "Project root not found: $ProjectRoot"
}

$ProjectRoot = [System.IO.Path]::GetFullPath($ProjectRoot)
if ([string]::IsNullOrWhiteSpace($LocalComfyRoot)) {
  $LocalComfyRoot = Join-Path $ProjectRoot "ComfyUI"
}
$LocalComfyRoot = [System.IO.Path]::GetFullPath($LocalComfyRoot)

$stamp = (Get-Date -Format "yyyyMMddTHHmmsszzz").Replace(":", "")
if ([string]::IsNullOrWhiteSpace($OutFile)) {
  $OutFile = Join-Path $ProjectRoot "Plan\Instructions\QA\Evidence\Runtime_Readiness\W66_LOCAL_COMFYUI_CHECKOUT_BOOTSTRAP_$stamp.json"
}

$mainPy = Join-Path $LocalComfyRoot "main.py"
$gitDir = Join-Path $LocalComfyRoot ".git"
$targetExists = Test-Path -LiteralPath $LocalComfyRoot
$mainExists = Test-Path -LiteralPath $mainPy
$targetFileCount = 0
if ($targetExists) {
  $targetFileCount = @((Get-ChildItem -LiteralPath $LocalComfyRoot -Force -ErrorAction SilentlyContinue | Select-Object -First 2)).Count
}

$gitVersion = $null
$gitAvailable = $false
try {
  $gitVersion = (& git --version 2>$null | Select-Object -First 1)
  $gitAvailable = ![string]::IsNullOrWhiteSpace($gitVersion)
} catch {}

$record = [ordered]@{
  schema_version = "1.0"
  timestamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  operation = "initialize_local_comfyui_checkout"
  project_root = $ProjectRoot
  local_comfy_root = $LocalComfyRoot
  local_comfy_root_relative = ConvertTo-RelativePath -BasePath $ProjectRoot -TargetPath $LocalComfyRoot
  repo_url = $ComfyRepoUrl
  branch = $(if ([string]::IsNullOrWhiteSpace($Branch)) { $null } else { $Branch })
  execute = [bool]$Execute
  local_only = $true
  aws_contacted = $false
  github_api_contacted = $false
  civitai_contacted = $false
  comfyui_started = $false
  ec2_started = $false
  generation_executed = $false
  model_binaries_downloaded = $false
  target_preexisting = $targetExists
  target_preexisting_main_py = $mainExists
  target_preexisting_entry_count = $targetFileCount
  git_available = $gitAvailable
  git_version = $gitVersion
  clone_attempted = $false
  clone_exit_code = $null
  clone_output_tail = $null
  main_py_exists_after = $mainExists
  checkout_git_head = $null
  checkout_remote = $null
  result = "dry_run_local_comfyui_checkout_plan"
  failure_category = $null
  errors = @()
  next_action = "Run with -Execute to create the ignored local ComfyUI checkout, then rerun tools/Test-LocalComfyUIDevPreflight.ps1."
}

if (!$gitAvailable) {
  $record.result = "blocked_git_not_available"
  $record.failure_category = "git_not_available"
  $record.errors += "git is not available on PATH."
} elseif ($mainExists) {
  $record.result = "local_comfyui_checkout_ready"
  $record.next_action = "Rerun tools/Test-LocalComfyUIDevPreflight.ps1 and use tools/Start-LocalComfyUIDev.ps1 for local iteration when dependencies are installed."
} elseif ($targetExists -and $targetFileCount -gt 0) {
  $record.result = "blocked_target_exists_without_main_py"
  $record.failure_category = "target_exists_without_main_py"
  $record.errors += "Target folder exists but does not contain main.py: $LocalComfyRoot"
} elseif ($Execute) {
  $record.clone_attempted = $true
  $null = New-Item -ItemType Directory -Force -Path (Split-Path -Parent $LocalComfyRoot)
  $cloneArgs = @("clone", "--depth", "1")
  if (![string]::IsNullOrWhiteSpace($Branch)) {
    $cloneArgs += @("--branch", $Branch)
  }
  $cloneArgs += @($ComfyRepoUrl, $LocalComfyRoot)
  $previousErrorActionPreference = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  try {
    $cloneOutput = @(& git @cloneArgs 2>&1)
    $record.clone_exit_code = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousErrorActionPreference
  }
  $record.clone_output_tail = (($cloneOutput | Select-Object -Last 20) -join "`n")
  if ($LASTEXITCODE -ne 0) {
    $record.result = "local_comfyui_clone_failed"
    $record.failure_category = "git_clone_failed"
    $record.errors += "git clone exited with code $LASTEXITCODE"
  } elseif (Test-Path -LiteralPath $mainPy) {
    $record.result = "local_comfyui_checkout_ready"
    $record.main_py_exists_after = $true
    $record.next_action = "Rerun tools/Test-LocalComfyUIDevPreflight.ps1 and install ComfyUI Python dependencies only when local execution is needed."
  } else {
    $record.result = "local_comfyui_clone_missing_main_py"
    $record.failure_category = "main_py_missing_after_clone"
    $record.errors += "Clone completed but main.py was not found."
  }
}

if (Test-Path -LiteralPath $gitDir) {
  try {
    $record.checkout_git_head = (& git -C $LocalComfyRoot rev-parse HEAD 2>$null | Select-Object -First 1)
    $record.checkout_remote = (& git -C $LocalComfyRoot remote get-url origin 2>$null | Select-Object -First 1)
  } catch {}
}

$outDir = Split-Path -Parent $OutFile
if (![string]::IsNullOrWhiteSpace($outDir)) {
  $null = New-Item -ItemType Directory -Force -Path $outDir
}
Write-JsonNoBom -Value $record -Path $OutFile -Depth 20
$record | ConvertTo-Json -Depth 20
if ($record.errors.Count -gt 0 -or $record.result -like "blocked_*" -or $record.result -like "*failed") { exit 2 }
