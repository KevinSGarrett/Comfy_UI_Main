param(
  [Parameter(Mandatory=$true)][ValidateSet("RecordFailure", "Clear", "Inspect")][string]$Action,
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$RuntimeWorkOrderId = "",
  [string]$FailureCategory = "insufficient_instance_capacity",
  [string]$ClearReason = "",
  [string]$StateFile = ""
)

$ErrorActionPreference = "Stop"
$encoding = New-Object System.Text.UTF8Encoding($false)
if ([string]::IsNullOrWhiteSpace($StateFile)) {
  $StateFile = Join-Path $ProjectRoot "runtime_artifacts\ec2_runtime_dispatch\CAPACITY_BACKOFF_STATE.json"
}

if ($Action -eq "Inspect") {
  if (!(Test-Path -LiteralPath $StateFile -PathType Leaf)) {
    [ordered]@{ result = "pass"; classification = "NO_CAPACITY_BACKOFF"; active = $false } | ConvertTo-Json
    return
  }
  $state = Get-Content -Raw -LiteralPath $StateFile | ConvertFrom-Json
  $active = ([datetimeoffset]::Parse([string]$state.not_before) -gt [datetimeoffset]::UtcNow)
  [ordered]@{ result = "pass"; classification = $(if ($active) { "CAPACITY_BACKOFF_ACTIVE" } else { "CAPACITY_BACKOFF_EXPIRED" }); active = $active; state = $state } | ConvertTo-Json -Depth 10
  return
}

if ($Action -eq "Clear") {
  if ($ClearReason -notin @("ec2_start_succeeded", "runtime_work_order_changed", "operator_cancelled")) {
    throw "ClearReason must identify a successful start, changed work order, or explicit cancellation."
  }
  if (Test-Path -LiteralPath $StateFile) { Remove-Item -LiteralPath $StateFile -Force }
  [ordered]@{ result = "pass"; classification = "CAPACITY_BACKOFF_CLEARED"; clear_reason = $ClearReason } | ConvertTo-Json
  return
}

if ($FailureCategory -cne "insufficient_instance_capacity") {
  throw "Only an exact insufficient_instance_capacity failure can create capacity backoff."
}
if ($RuntimeWorkOrderId -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{7,127}$') { throw "RuntimeWorkOrderId is invalid." }

$attempt = 1
if (Test-Path -LiteralPath $StateFile -PathType Leaf) {
  $previous = Get-Content -Raw -LiteralPath $StateFile | ConvertFrom-Json
  if ([string]$previous.runtime_work_order_id -ceq $RuntimeWorkOrderId) {
    $attempt = [int]$previous.consecutive_capacity_failures + 1
  }
}
$delayMinutes = [math]::Min(120, 15 * [math]::Pow(2, [math]::Min(3, $attempt - 1)))
$now = [datetimeoffset]::UtcNow
$state = [ordered]@{
  schema_version = "1.0"
  runtime_work_order_id = $RuntimeWorkOrderId
  failure_category = $FailureCategory
  consecutive_capacity_failures = $attempt
  recorded_at = $now.ToString("yyyy-MM-ddTHH:mm:ssZ")
  backoff_minutes = [int]$delayMinutes
  not_before = $now.AddMinutes($delayMinutes).ToString("yyyy-MM-ddTHH:mm:ssZ")
  classification = "CAPACITY_BACKOFF_ACTIVE"
}
$directory = Split-Path -Parent $StateFile
$null = New-Item -ItemType Directory -Force -Path $directory
$temporary = "$StateFile.$([guid]::NewGuid().ToString('N')).tmp"
try {
  [System.IO.File]::WriteAllText($temporary, ($state | ConvertTo-Json -Depth 10), $encoding)
  Move-Item -LiteralPath $temporary -Destination $StateFile -Force
} finally {
  Remove-Item -LiteralPath $temporary -Force -ErrorAction SilentlyContinue
}
$state | ConvertTo-Json -Depth 10
