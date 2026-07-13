param(
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$AccountId = "029530099913",
  [string]$Region = "us-east-1",
  [string]$BootstrapUserName = "ComfyUIMainSessionBootstrap",
  [string]$RoleName = "ComfyUIMainSessionRole",
  [string]$CredentialFile = "$env:USERPROFILE\.aws\comfy-ui-main-bootstrap.dpapi.json",
  [string]$AwsConfigFile = "$env:USERPROFILE\.aws\config"
)

$ErrorActionPreference = "Stop"
$encoding = New-Object System.Text.UTF8Encoding($false)

function Invoke-AwsJson {
  param([Parameter(Mandatory=$true)][string[]]$Arguments)

  $output = & aws @Arguments --output json
  if ($LASTEXITCODE -ne 0) {
    throw "AWS CLI command failed: aws $($Arguments -join ' ')"
  }
  if ([string]::IsNullOrWhiteSpace(($output -join "`n"))) { return $null }
  return ($output -join "`n") | ConvertFrom-Json
}

function Test-AwsResource {
  param([Parameter(Mandatory=$true)][string[]]$Arguments)

  $previousPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = "Continue"
    $null = & aws @Arguments --output json 2>$null
    return ($LASTEXITCODE -eq 0)
  } finally {
    $ErrorActionPreference = $previousPreference
  }
}

function Protect-CredentialFile {
  param([Parameter(Mandatory=$true)][string]$Path)

  $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
  $account = New-Object System.Security.Principal.NTAccount($identity)
  $acl = New-Object System.Security.AccessControl.FileSecurity
  $acl.SetOwner($account)
  $acl.SetAccessRuleProtection($true, $false)
  $rule = New-Object System.Security.AccessControl.FileSystemAccessRule($identity, "FullControl", "Allow")
  $acl.AddAccessRule($rule)
  Set-Acl -LiteralPath $Path -AclObject $acl
}

$caller = Invoke-AwsJson -Arguments @("sts", "get-caller-identity")
if ([string]$caller.Account -ne $AccountId -or [string]$caller.Arn -ne "arn:aws:iam::$AccountId`:root") {
  throw "One-time installation must run from the expected account root break-glass login. Observed: $($caller.Arn)"
}

$trustPolicy = Join-Path $ProjectRoot "configs\aws\comfy-ui-main-session-role-trust-policy.json"
$rolePolicy = Join-Path $ProjectRoot "configs\aws\comfy-ui-main-session-role-policy.json"
$bootstrapPolicy = Join-Path $ProjectRoot "configs\aws\comfy-ui-main-session-bootstrap-policy.json"
$credentialProcess = Join-Path $ProjectRoot "tools\aws\Get-ComfyUIMainAwsBootstrapCredentials.ps1"
foreach ($path in @($trustPolicy, $rolePolicy, $bootstrapPolicy, $credentialProcess)) {
  if (!(Test-Path -LiteralPath $path -PathType Leaf)) { throw "Required installation input is missing: $path" }
}

if (!(Test-AwsResource -Arguments @("iam", "get-user", "--user-name", $BootstrapUserName))) {
  $null = Invoke-AwsJson -Arguments @("iam", "create-user", "--user-name", $BootstrapUserName)
}
$null = Invoke-AwsJson -Arguments @(
  "iam", "put-user-policy",
  "--user-name", $BootstrapUserName,
  "--policy-name", "AssumeOnlyComfyUIMainSessionRole",
  "--policy-document", "file://$bootstrapPolicy"
)

if (!(Test-AwsResource -Arguments @("iam", "get-role", "--role-name", $RoleName))) {
  $null = Invoke-AwsJson -Arguments @(
    "iam", "create-role",
    "--role-name", $RoleName,
    "--assume-role-policy-document", "file://$trustPolicy",
    "--description", "Least-privilege short-lived role for the Comfy_UI_Main Codex session"
  )
} else {
  $null = Invoke-AwsJson -Arguments @(
    "iam", "update-assume-role-policy",
    "--role-name", $RoleName,
    "--policy-document", "file://$trustPolicy"
  )
}
$null = Invoke-AwsJson -Arguments @(
  "iam", "put-role-policy",
  "--role-name", $RoleName,
  "--policy-name", "ComfyUIMainSessionScopedRuntimeAccess",
  "--policy-document", "file://$rolePolicy"
)

$credentialDirectory = Split-Path -Parent $CredentialFile
$null = New-Item -ItemType Directory -Force -Path $credentialDirectory
if (!(Test-Path -LiteralPath $CredentialFile -PathType Leaf)) {
  $keys = Invoke-AwsJson -Arguments @("iam", "list-access-keys", "--user-name", $BootstrapUserName)
  if (@($keys.AccessKeyMetadata).Count -ge 2) {
    throw "Bootstrap user already has two access keys; refusing to create another."
  }
  $created = Invoke-AwsJson -Arguments @("iam", "create-access-key", "--user-name", $BootstrapUserName)
  $secureSecret = ConvertTo-SecureString ([string]$created.AccessKey.SecretAccessKey) -AsPlainText -Force
  $stored = [ordered]@{
    schema_version = "1.0"
    access_key_id = [string]$created.AccessKey.AccessKeyId
    encrypted_secret_access_key = ConvertFrom-SecureString $secureSecret
    created_at = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
    protection = "Windows DPAPI current-user"
    permitted_action = "sts:AssumeRole arn:aws:iam::$AccountId`:role/$RoleName"
  }
  [System.IO.File]::WriteAllText($CredentialFile, ($stored | ConvertTo-Json -Depth 5), $encoding)
  Protect-CredentialFile -Path $CredentialFile
  $created.AccessKey.SecretAccessKey = $null
}

$configDirectory = Split-Path -Parent $AwsConfigFile
$null = New-Item -ItemType Directory -Force -Path $configDirectory
$existingConfig = $(if (Test-Path -LiteralPath $AwsConfigFile) { [System.IO.File]::ReadAllText($AwsConfigFile) } else { "" })
$backupPath = "$AwsConfigFile.before-comfy-ui-main-$(Get-Date -Format 'yyyyMMddTHHmmss').bak"
if (Test-Path -LiteralPath $AwsConfigFile) {
  Copy-Item -LiteralPath $AwsConfigFile -Destination $backupPath -Force
}

$sectionsToReplace = @("default", "profile comfy-ui-main", "profile comfy-ui-main-bootstrap", "profile comfy-ui-root-breakglass")
$keptLines = New-Object System.Collections.ArrayList
$skip = $false
foreach ($line in @($existingConfig -split "`r?`n")) {
  if ($line -match '^\s*\[([^\]]+)\]\s*$') {
    $skip = ($sectionsToReplace -contains $Matches[1].Trim())
  }
  if (!$skip) { [void]$keptLines.Add($line) }
}

$canonical = @"
[profile comfy-ui-root-breakglass]
login_session = arn:aws:iam::$AccountId`:root
region = $Region

[profile comfy-ui-main-bootstrap]
credential_process = powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $credentialProcess
region = $Region

[profile comfy-ui-main]
role_arn = arn:aws:iam::$AccountId`:role/$RoleName
source_profile = comfy-ui-main-bootstrap
role_session_name = comfy-ui-main-session
duration_seconds = 3600
region = $Region

[default]
role_arn = arn:aws:iam::$AccountId`:role/$RoleName
source_profile = comfy-ui-main-bootstrap
role_session_name = comfy-ui-main-session
duration_seconds = 3600
region = $Region
s3 =
    max_concurrent_requests = 1
    multipart_chunksize = 64MB
"@
$newConfig = ((@($keptLines) -join "`r`n").Trim() + "`r`n`r`n" + $canonical.Trim() + "`r`n")

try {
  [System.IO.File]::WriteAllText($AwsConfigFile, $newConfig, $encoding)
  $assumed = $null
  for ($attempt = 1; $attempt -le 12; $attempt++) {
    try {
      $assumed = Invoke-AwsJson -Arguments @("sts", "get-caller-identity", "--profile", "comfy-ui-main")
      break
    } catch {
      if ($attempt -eq 12) { throw }
      Start-Sleep -Seconds 5
    }
  }
  if ([string]$assumed.Arn -notmatch ":assumed-role/$([regex]::Escape($RoleName))/") {
    throw "New main-session profile did not assume the expected role. Observed: $($assumed.Arn)"
  }
  $defaultIdentity = Invoke-AwsJson -Arguments @("sts", "get-caller-identity")
  if ([string]$defaultIdentity.Arn -notmatch ":assumed-role/$([regex]::Escape($RoleName))/") {
    throw "Default AWS profile did not switch to the expected role. Observed: $($defaultIdentity.Arn)"
  }
} catch {
  if (Test-Path -LiteralPath $backupPath) {
    Copy-Item -LiteralPath $backupPath -Destination $AwsConfigFile -Force
  }
  throw
}

[ordered]@{
  result = "pass"
  classification = "COMFY_UI_MAIN_SESSION_LEAST_PRIVILEGE_PROFILE_ACTIVE"
  default_identity_arn = [string]$defaultIdentity.Arn
  role_arn = "arn:aws:iam::$AccountId`:role/$RoleName"
  bootstrap_user_arn = "arn:aws:iam::$AccountId`:user/$BootstrapUserName"
  credential_storage = "Windows DPAPI current-user protected file"
  root_profile = "comfy-ui-root-breakglass"
  config_backup = $backupPath
} | ConvertTo-Json -Depth 5
