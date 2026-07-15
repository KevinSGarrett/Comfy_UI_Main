Set-StrictMode -Version 2
$ErrorActionPreference = 'Stop'
if (-not ('System.Security.Cryptography.ProtectedData' -as [type])) {
  Add-Type -AssemblyName System.Security
}

function Write-Utf8NoBom {
  param([Parameter(Mandatory=$true)][string]$Path,[Parameter(Mandatory=$true)][string]$Text)
  $parent = Split-Path -Parent $Path
  if (-not [string]::IsNullOrWhiteSpace($parent)) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
  [System.IO.File]::WriteAllText($Path,$Text,(New-Object System.Text.UTF8Encoding($false)))
}

function Get-Sha256Text {
  param([Parameter(Mandatory=$true)][AllowEmptyString()][string]$Text)
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try { return ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($Text)))).Replace('-','').ToLowerInvariant() } finally { $sha.Dispose() }
}

function Get-AIWorkerKeyPath {
  param([Parameter(Mandatory=$true)][string]$DispatcherRoot)
  return Join-Path ([IO.Path]::GetFullPath($DispatcherRoot)) 'security\request_signing_key.dpapi'
}

function Initialize-AIWorkerSigningKey {
  param([Parameter(Mandatory=$true)][string]$DispatcherRoot,[switch]$Force)
  $keyPath = Get-AIWorkerKeyPath -DispatcherRoot $DispatcherRoot
  if ((Test-Path -LiteralPath $keyPath) -and -not $Force) { return $keyPath }
  $bytes = New-Object byte[] 32
  $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
  $protected = [System.Security.Cryptography.ProtectedData]::Protect($bytes,$null,[System.Security.Cryptography.DataProtectionScope]::CurrentUser)
  Write-Utf8NoBom -Path $keyPath -Text ([Convert]::ToBase64String($protected))
  return $keyPath
}

function Get-AIWorkerSigningKey {
  param([Parameter(Mandatory=$true)][string]$DispatcherRoot)
  $keyPath = Get-AIWorkerKeyPath -DispatcherRoot $DispatcherRoot
  if (-not (Test-Path -LiteralPath $keyPath -PathType Leaf)) { throw "AI worker signing key missing: $keyPath" }
  $protected = [Convert]::FromBase64String((Get-Content -LiteralPath $keyPath -Raw).Trim())
  return [System.Security.Cryptography.ProtectedData]::Unprotect($protected,$null,[System.Security.Cryptography.DataProtectionScope]::CurrentUser)
}

function Get-AIWorkerHmac {
  param([Parameter(Mandatory=$true)][byte[]]$Key,[Parameter(Mandatory=$true)][byte[]]$Bytes)
  $hmac = New-Object System.Security.Cryptography.HMACSHA256 (,$Key)
  try { return ([BitConverter]::ToString($hmac.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant() } finally { $hmac.Dispose() }
}

function Get-AIWorkerFileSha256Shared {
  param([Parameter(Mandatory=$true)][string]$Path)
  $stream=[IO.File]::Open([IO.Path]::GetFullPath($Path),[IO.FileMode]::Open,[IO.FileAccess]::Read,[IO.FileShare]::ReadWrite -bor [IO.FileShare]::Delete)
  $sha=[Security.Cryptography.SHA256]::Create()
  try{return([BitConverter]::ToString($sha.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose();$stream.Dispose()}
}

function Write-AIWorkerSignedJson {
  param([Parameter(Mandatory=$true)][string]$Path,[Parameter(Mandatory=$true)]$Value,[Parameter(Mandatory=$true)][string]$DispatcherRoot)
  $json = $Value | ConvertTo-Json -Depth 20
  $bytes = [Text.Encoding]::UTF8.GetBytes($json)
  $key = Get-AIWorkerSigningKey -DispatcherRoot $DispatcherRoot
  try { $signature = Get-AIWorkerHmac -Key $key -Bytes $bytes } finally { [Array]::Clear($key,0,$key.Length) }
  $temp = $Path + '.' + [guid]::NewGuid().ToString('N') + '.tmp'
  Write-Utf8NoBom -Path $temp -Text $json
  Move-Item -LiteralPath $temp -Destination $Path -Force
  Write-Utf8NoBom -Path ($Path + '.sig') -Text $signature
  return $signature
}

function Read-AIWorkerSignedJson {
  param([Parameter(Mandatory=$true)][string]$Path,[Parameter(Mandatory=$true)][string]$DispatcherRoot)
  $signaturePath = $Path + '.sig'
  if (-not (Test-Path -LiteralPath $Path -PathType Leaf) -or -not (Test-Path -LiteralPath $signaturePath -PathType Leaf)) { throw "Signed record or signature missing: $Path" }
  $bytes = [IO.File]::ReadAllBytes($Path)
  $expected = (Get-Content -LiteralPath $signaturePath -Raw).Trim().ToLowerInvariant()
  $key = Get-AIWorkerSigningKey -DispatcherRoot $DispatcherRoot
  try { $actual = Get-AIWorkerHmac -Key $key -Bytes $bytes } finally { [Array]::Clear($key,0,$key.Length) }
  if ($expected -notmatch '^[0-9a-f]{64}$' -or $actual -ne $expected) { throw "AI_WORKER_SIGNATURE_INVALID: $Path" }
  return [Text.Encoding]::UTF8.GetString($bytes) | ConvertFrom-Json -ErrorAction Stop
}

function Normalize-AIWorkerRelativePath {
  param([Parameter(Mandatory=$true)][string]$Path)
  if ([IO.Path]::IsPathRooted($Path)) { throw "Path must be repository-relative: $Path" }
  $value = ($Path -replace '\\','/').TrimStart('/')
  if ([string]::IsNullOrWhiteSpace($value) -or @($value -split '/') -contains '..' -or $value -match '[:\u0000-\u001f]') { throw "Invalid repository-relative path: $Path" }
  return $value
}

function Test-AIWorkerProtectedPath {
  param([Parameter(Mandatory=$true)][string]$Path)
  return (Normalize-AIWorkerRelativePath $Path) -match '^(?i)(\.git(?:/|$)|\.env$|Plan/(?:Items|Tracker)(?:/|$)|masks(?:/|$)|Ref_Image_(?:1|2|Canonical_Body)(?:/|$)|Jira(?:/|$))'
}

function Enter-AIWorkerFileLock {
  param([Parameter(Mandatory=$true)][string]$Path,[int]$StaleMinutes=30)
  if (Test-Path -LiteralPath $Path) {
    $remove = $false
    try { $existing = Get-Content -LiteralPath $Path -Raw | ConvertFrom-Json; $remove = ($null -eq (Get-Process -Id ([int]$existing.pid) -ErrorAction SilentlyContinue)) } catch { $remove = $true }
    if (((Get-Date)-(Get-Item -LiteralPath $Path).LastWriteTime).TotalMinutes -ge $StaleMinutes) { $remove = $true }
    if ($remove) { Remove-Item -LiteralPath $Path -Force }
  }
  try {
    $stream=[IO.File]::Open($Path,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try { $b=[Text.Encoding]::UTF8.GetBytes(([ordered]@{pid=$PID;created_at=(Get-Date).ToString('o')}|ConvertTo-Json -Compress));$stream.Write($b,0,$b.Length) } finally { $stream.Dispose() }
    return $true
  } catch [IO.IOException] { return $false }
}

function Get-AIWorkerSafeId {
  param([Parameter(Mandatory=$true)][string]$Value)
  $safe=($Value -replace '[^A-Za-z0-9_.-]+','_').Trim('_')
  if ([string]::IsNullOrWhiteSpace($safe)) { throw 'Identifier normalized to empty.' }
  if ($safe.Length -gt 120) { $safe=$safe.Substring(0,120) }
  return $safe
}

Export-ModuleMember -Function Write-Utf8NoBom,Get-Sha256Text,Get-AIWorkerFileSha256Shared,Get-AIWorkerKeyPath,Initialize-AIWorkerSigningKey,Get-AIWorkerSigningKey,Get-AIWorkerHmac,Write-AIWorkerSignedJson,Read-AIWorkerSignedJson,Normalize-AIWorkerRelativePath,Test-AIWorkerProtectedPath,Enter-AIWorkerFileLock,Get-AIWorkerSafeId
