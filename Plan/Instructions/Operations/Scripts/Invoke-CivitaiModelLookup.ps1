<#
.SYNOPSIS
Looks up Civitai models by query/type using the process .env token if available.
Does not download files.
#>
param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$Query,
  [string]$Types = "LORA",
  [int]$Limit = 10,
  [string]$OutFile = ""
)

$ErrorActionPreference = "Stop"
. (Join-Path $ProjectRoot "Plan\Instructions\Operations\Scripts\Load-ComfyEnv.ps1") -ProjectRoot $ProjectRoot -Quiet

if (-not $Query) { throw "Query is required." }

$headers = @{}
if ($env:CIVITAI_API_TOKEN) { $headers["Authorization"] = "Bearer $env:CIVITAI_API_TOKEN" }
elseif ($env:CIVITAI_TOKEN) { $headers["Authorization"] = "Bearer $env:CIVITAI_TOKEN" }
elseif ($env:CIVITAI_API_KEY) { $headers["Authorization"] = "Bearer $env:CIVITAI_API_KEY" }

$encodedQuery = [System.Net.WebUtility]::UrlEncode($Query)
$encodedTypes = [System.Net.WebUtility]::UrlEncode($Types)
$uri = "https://civitai.com/api/v1/models?query=$encodedQuery&types=$encodedTypes&limit=$Limit&primaryFileOnly=true"
$result = Invoke-RestMethod -Method Get -Uri $uri -Headers $headers

if ($OutFile) {
  $dir = Split-Path $OutFile -Parent
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
  $result | ConvertTo-Json -Depth 20 | Set-Content -Encoding UTF8 $OutFile
  Write-Host "Wrote metadata to $OutFile"
} else {
  $result | ConvertTo-Json -Depth 20
}
