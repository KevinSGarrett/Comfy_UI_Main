param(
  [Parameter(Mandatory=$true)][string]$TaskId,
  [Parameter(Mandatory=$true)][string]$Title,
  [string]$OutFile = "./done_certification.md"
)

$content = @"
# Done Certification Template

- Certification ID: CERT-$TaskId
- Task / Tracker ID: $TaskId
- Title: $Title
- Artifact Scope:
- Implementation Summary:
- Tests Performed:
- QA Summary:
- Evidence Paths:
- Known Issues:
- Final Decision:
- Certifier: Codex Desktop autonomous release manager
- Timestamp: $(Get-Date -Format s)
"@

Set-Content -Path $OutFile -Value $content -Encoding UTF8
Write-Host "Initialized done certification: $OutFile"
