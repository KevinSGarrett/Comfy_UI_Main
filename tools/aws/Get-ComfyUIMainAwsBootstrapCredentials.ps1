param(
  [string]$CredentialFile = "$env:USERPROFILE\.aws\comfy-ui-main-bootstrap.dpapi.json"
)

$ErrorActionPreference = "Stop"
if (!(Test-Path -LiteralPath $CredentialFile -PathType Leaf)) {
  throw "ComfyUI main-session bootstrap credential file is missing."
}

$stored = Get-Content -Raw -LiteralPath $CredentialFile | ConvertFrom-Json
$accessKeyId = ([string]$stored.access_key_id).Trim()
$encryptedSecret = ([string]$stored.encrypted_secret_access_key).Trim()
if ($accessKeyId -notmatch '^AKIA[A-Z0-9]{16}$' -or [string]::IsNullOrWhiteSpace($encryptedSecret)) {
  throw "ComfyUI main-session bootstrap credential file is invalid."
}

$secureSecret = ConvertTo-SecureString $encryptedSecret
$secretPointer = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureSecret)
try {
  $secretAccessKey = [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($secretPointer)
  [ordered]@{
    Version = 1
    AccessKeyId = $accessKeyId
    SecretAccessKey = $secretAccessKey
  } | ConvertTo-Json -Compress
} finally {
  if ($secretPointer -ne [IntPtr]::Zero) {
    [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secretPointer)
  }
  $secretAccessKey = $null
}
