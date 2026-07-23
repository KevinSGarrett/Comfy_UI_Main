[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$HostName,
    [Parameter(Mandatory = $true)][int]$Port,
    [Parameter(Mandatory = $true)][string]$OutputPath
)

$ErrorActionPreference = 'Stop'
$commands = 'C:\Users\kevin\.codex\shared_runpod_coordinator\commands'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$runner = Join-Path $projectRoot 'Plan\07_IMPLEMENTATION\scripts\run_wave64_qwen3vl4_fast_triage_refusal_canary.py'
$admission = Join-Path $projectRoot 'Plan\10_REGISTRIES\wave64_qwen3vl4_fast_triage_refusal_admission.json'
$tempReceipt = [System.IO.Path]::GetTempFileName()
$grant = $null
$canaryExit = 99

try {
    $grant = (& (Join-Path $commands 'Request-SharedRunPodLease.ps1') `
        -Project comfyui_main `
        -Profile comfyui_model_qualification `
        -Task 'Qwen3-VL 4B immutable refusal-discipline canary' `
        -ExpectedSteadyVramGiB 6 `
        -QualifiedPeakVramGiB 8 `
        -Intensity medium `
        -LeaseMode exclusive `
        -Model 'qwen3-vl:4b-instruct-q4_K_M' `
        -Checkpointable | ConvertFrom-Json)
    if ($grant.status -ne 'GRANTED') {
        if ($grant.lease_id -and $grant.lease_token) {
            & (Join-Path $commands 'Cancel-SharedRunPodRequest.ps1') `
                -LeaseId $grant.lease_id `
                -LeaseToken $grant.lease_token `
                -Reason 'bounded canary requires immediate exact grant' | Out-Null
        }
        throw "Coordinator did not grant exact lease: $($grant.status)"
    }

    $validated = (& (Join-Path $commands 'Test-SharedRunPodLease.ps1') `
        -LeaseId $grant.lease_id `
        -LeaseToken $grant.lease_token `
        -Project comfyui_main `
        -Profile comfyui_model_qualification | ConvertFrom-Json)
    $receipt = [ordered]@{
        valid = $true
        lease_id = $validated.lease_id
        project = $validated.project
        profile = $validated.profile
        lease_mode = $validated.lease_mode
        reserved_peak_gib = $validated.reserved_peak_gib
        expires_at = $validated.expires_at
        token_retained = $false
    }
    [System.IO.File]::WriteAllText(
        $tempReceipt,
        ($receipt | ConvertTo-Json -Depth 5),
        [System.Text.UTF8Encoding]::new($false)
    )

    $env:SHARED_RUNPOD_LEASE_ID = $grant.lease_id
    $env:SHARED_RUNPOD_LEASE_TOKEN = $grant.lease_token
    $env:SHARED_RUNPOD_LEASE_PROFILE = 'comfyui_model_qualification'
    & python $runner `
        --admission $admission `
        --lease-receipt $tempReceipt `
        --host $HostName `
        --port $Port `
        --output $OutputPath
    $canaryExit = $LASTEXITCODE
}
finally {
    if ($grant -and $grant.status -eq 'GRANTED' -and $grant.lease_token) {
        $releaseResult = if ($canaryExit -eq 0) {
            'completed_and_evidenced'
        }
        else {
            'failed_closed_and_evidenced'
        }
        & (Join-Path $commands 'Release-SharedRunPodLease.ps1') `
            -LeaseId $grant.lease_id `
            -LeaseToken $grant.lease_token `
            -Result $releaseResult | Out-Null
    }
    Remove-Item -LiteralPath $tempReceipt -Force -ErrorAction SilentlyContinue
    Remove-Item `
        Env:SHARED_RUNPOD_LEASE_ID, `
        Env:SHARED_RUNPOD_LEASE_TOKEN, `
        Env:SHARED_RUNPOD_LEASE_PROFILE `
        -ErrorAction SilentlyContinue
}

[ordered]@{
    output = $OutputPath
    exit_code = $canaryExit
    lease_released = $true
} | ConvertTo-Json -Compress
exit $canaryExit
