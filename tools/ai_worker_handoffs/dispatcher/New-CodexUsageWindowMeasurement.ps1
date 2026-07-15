[CmdletBinding(PositionalBinding=$false)]
param(
  [string]$DispatcherRoot = "C:\Users\kevin\.codex\ai_worker_dispatcher",
  [Parameter(Mandatory=$true)][ValidateSet("five_hour","twenty_four_hour_weekly_rate")][string]$WindowType,
  [Parameter(Mandatory=$true)][datetimeoffset]$StartedAt,
  [Parameter(Mandatory=$true)][datetimeoffset]$EndedAt,
  [Parameter(Mandatory=$true)][ValidateRange(0.0001,100)][double]$PreDelegationBurnPercentPerHour,
  [Parameter(Mandatory=$true)][ValidateRange(0,100)][double]$CodexConsumedPercent,
  [string]$Source = "user_observed_codex_desktop_ui",
  [string]$EvidenceNote = ""
)

$ErrorActionPreference = "Stop"
$hours = ($EndedAt - $StartedAt).TotalHours
if ($hours -le 0) { throw 'EndedAt must be later than StartedAt.' }
if ($WindowType -eq 'five_hour' -and ($hours -lt 4.5 -or $hours -gt 5.5)) { throw 'A five-hour measurement must span 4.5 to 5.5 hours.' }
if ($WindowType -eq 'twenty_four_hour_weekly_rate' -and $hours -lt 24) { throw 'A 24-hour/weekly-rate measurement must span at least 24 hours.' }
$postRate = $CodexConsumedPercent / $hours
$reduction = 100 * (1 - ($postRate / $PreDelegationBurnPercentPerHour))
$measurement = [ordered]@{
  schema_version = 1
  artifact_type = 'codex_usage_window_measurement'
  status = 'MEASURED'
  finalized_at = (Get-Date).ToString('o')
  window_type = $WindowType
  started_at = $StartedAt.ToString('o')
  ended_at = $EndedAt.ToString('o')
  elapsed_hours = [math]::Round($hours,4)
  pre_delegation_burn_percent_per_hour = $PreDelegationBurnPercentPerHour
  codex_consumed_percent = $CodexConsumedPercent
  post_delegation_burn_percent_per_hour = [math]::Round($postRate,6)
  measured_reduction_percent = [math]::Round($reduction,2)
  target_reduction_percent = 50
  target_met = ($reduction -ge 50)
  source = $Source
  evidence_note = $EvidenceNote
  direct_measurement = $true
}
$measureRoot = Join-Path ([System.IO.Path]::GetFullPath($DispatcherRoot)) 'measurements'
New-Item -ItemType Directory -Force -Path $measureRoot | Out-Null
$stamp = $EndedAt.ToString('yyyyMMddTHHmmsszzz') -replace ':',''
$path = Join-Path $measureRoot "${stamp}_${WindowType}.json"
[System.IO.File]::WriteAllText($path, ($measurement | ConvertTo-Json -Depth 6), (New-Object System.Text.UTF8Encoding($false)))
$measurement.output_path = $path
$measurement | ConvertTo-Json -Depth 6
