param(
  [Parameter(Mandatory=$true)][string]$ArtifactId,
  [Parameter(Mandatory=$true)][string]$ArtifactType,
  [string]$OutFile = "./qa_record.json"
)

$record = [ordered]@{
  artifact_id   = $ArtifactId
  artifact_type = $ArtifactType
  reviewer      = "Codex Desktop autonomous QA"
  qa_status     = "pending"
  scores        = @{}
  defects       = @()
  evidence_paths= @()
  known_issues  = @()
  next_action   = "Complete test run and review"
  timestamp     = (Get-Date).ToString("s")
}

$record | ConvertTo-Json -Depth 10 | Set-Content -Path $OutFile -Encoding UTF8
Write-Host "Initialized QA record: $OutFile"
