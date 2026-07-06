param(
  [string]$ManifestPath = "manifests\model_assets\required_assets_for_runtime_proof.json",
  [string]$LocalModelRoot = "D:\ComfyUI_Models",
  [switch]$DryRun = $true
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $ManifestPath)) {
  throw "Missing model hydration manifest: $ManifestPath"
}

$manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json

foreach ($asset in $manifest.assets) {
  if (-not $asset.s3_uri) {
    throw "Asset missing s3_uri: $($asset.asset_id)"
  }
  if (-not $asset.local_cache_path) {
    throw "Asset missing local_cache_path: $($asset.asset_id)"
  }

  $cmd = "aws s3 cp `"$($asset.s3_uri)`" `"$($asset.local_cache_path)`""
  if ($DryRun) {
    $cmd = "$cmd --dryrun"
  }
  Write-Host $cmd
}

if ($DryRun) {
  Write-Host "Dry-run hydration plan produced. No files downloaded."
}
