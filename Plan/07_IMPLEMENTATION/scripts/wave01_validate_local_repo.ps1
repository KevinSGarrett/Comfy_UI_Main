param(
  [string]$RepoRoot = "C:\Comfy_UI_Main"
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

$requiredDirs = @(
  "docs","workflows","orchestration","schemas","configs","scripts","manifests","evidence","tests","app_mode","external_assets",".github\workflows"
)

$failures = @()

foreach ($d in $requiredDirs) {
  if (-not (Test-Path $d)) {
    $failures += "Missing required directory: $d"
  }
}

foreach ($f in @(".gitignore",".gitattributes","README.md","PROJECT_MANIFEST.json")) {
  if (-not (Test-Path $f)) {
    $failures += "Missing required file: $f"
  }
}

$forbidden = @("*.safetensors","*.ckpt","*.pt","*.pth","*.bin","*.gguf","*.onnx","*.mp4","*.wav","*.zip","*.7z","*.rar")
foreach ($pattern in $forbidden) {
  $hits = Get-ChildItem -Recurse -File -Filter $pattern -ErrorAction SilentlyContinue | Select-Object -First 5
  if ($hits) {
    $failures += "Forbidden file type found for pattern ${pattern}: $($hits[0].FullName)"
  }
}

$jsonFiles = Get-ChildItem -Recurse -File -Filter *.json -ErrorAction SilentlyContinue
foreach ($jf in $jsonFiles) {
  try {
    Get-Content $jf.FullName -Raw | ConvertFrom-Json | Out-Null
  } catch {
    $failures += "Invalid JSON: $($jf.FullName) :: $($_.Exception.Message)"
  }
}

$result = [ordered]@{
  repo_root = $RepoRoot
  checked_at = (Get-Date).ToString("o")
  failures = $failures
  passed = ($failures.Count -eq 0)
}

New-Item -ItemType Directory -Force -Path "manifests\repo_validation" | Out-Null
$result | ConvertTo-Json -Depth 10 | Set-Content -Path "manifests\repo_validation\wave01_local_repo_validation.json" -Encoding UTF8

if ($failures.Count -gt 0) {
  $failures | ForEach-Object { Write-Error $_ }
  exit 1
}

Write-Host "Wave 01 local repo validation passed."
