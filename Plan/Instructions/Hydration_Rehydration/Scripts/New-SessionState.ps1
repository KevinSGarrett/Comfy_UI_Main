param(
  [string]$SessionId = "SESSION-" + (Get-Date -Format "yyyyMMdd-HHmmss"),
  [string]$OutFile = "C:\Comfy_UI_Main\Plan\Instructions\Hydration_Rehydration\State\session_state.json"
)

$state = [ordered]@{
  session_id = $SessionId
  started_at = (Get-Date).ToString("s")
  active_wave = ""
  active_tracker_ids = @()
  active_item_ids = @()
  current_goal = ""
  files_changed = @()
  tests_run = @()
  qa_records = @()
  failures = @()
  fixes = @()
  blockers = @()
  next_action = ""
  github_status = @{}
  aws_ec2_status = @{}
  civitai_model_status = @{}
}

$state | ConvertTo-Json -Depth 10 | Set-Content -Path $OutFile -Encoding UTF8
Write-Host "Created session state: $OutFile"
