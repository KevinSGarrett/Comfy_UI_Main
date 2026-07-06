param(
  [string]$RepoRoot = "C:\Comfy_UI_Main",
  [string]$RemoteUrl = "https://github.com/KevinSGarrett/Comfy_UI_Main"
)

$ErrorActionPreference = "Stop"

Write-Host "Wave 01 local repo bootstrap"
Write-Host "RepoRoot: $RepoRoot"

New-Item -ItemType Directory -Force -Path $RepoRoot | Out-Null
Set-Location $RepoRoot

$dirs = @(
  "docs",
  "workflows\ui\current",
  "workflows\ui\archive",
  "workflows\api\templates",
  "workflows\subgraphs",
  "workflows\modules",
  "workflows\app_mode",
  "orchestration\planner",
  "orchestration\runner",
  "orchestration\qa",
  "orchestration\repair",
  "orchestration\registries",
  "schemas",
  "configs",
  "scripts\powershell",
  "scripts\python",
  "manifests\source_inventory",
  "manifests\model_assets",
  "manifests\workflow_validation",
  "manifests\qa",
  "manifests\ec2_runtime_proof",
  "evidence\local",
  "evidence\ec2",
  "evidence\visual_qa",
  "tests\unit",
  "tests\integration",
  "tests\golden_scenes",
  "tests\no_gpu_static",
  "app_mode\specs",
  "external_assets",
  ".github\workflows"
)

foreach ($d in $dirs) {
  New-Item -ItemType Directory -Force -Path $d | Out-Null
}

if (-not (Test-Path ".git")) {
  git init
}

$existingRemote = ""
try {
  $existingRemote = git remote get-url origin 2>$null
} catch {
  $existingRemote = ""
}

if (-not $existingRemote) {
  git remote add origin $RemoteUrl
  Write-Host "Added origin remote: $RemoteUrl"
} else {
  Write-Host "Origin already exists: $existingRemote"
  if ($existingRemote -ne $RemoteUrl) {
    Write-Warning "Origin differs from expected remote. Do not overwrite automatically."
  }
}

Write-Host "Bootstrap complete. Copy template .gitignore/.gitattributes/README/PROJECT_MANIFEST into the repo root before committing."
