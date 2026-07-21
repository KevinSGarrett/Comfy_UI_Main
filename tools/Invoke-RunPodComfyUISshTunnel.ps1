<#
.SYNOPSIS
Starts, stops, or reports status for the RunPod ComfyUI SSH local port forward.

.DESCRIPTION
Thin alias for Invoke-EC2ComfyUISshTunnel.ps1. Forwards local TCP 8188 to remote
ComfyUI at 127.0.0.1:8188 on the RunPod pod (195.26.233.100:52077 by default).
Use http://127.0.0.1:8188 while the tunnel is active; stop when finished.

.EXAMPLE
# Start tunnel (background ssh process)
.\tools\Invoke-RunPodComfyUISshTunnel.ps1 -Action Start

.EXAMPLE
# Check whether local 8188 is forwarded
.\tools\Invoke-RunPodComfyUISshTunnel.ps1 -Action Status

.EXAMPLE
# Stop tunnel started by this helper
.\tools\Invoke-RunPodComfyUISshTunnel.ps1 -Action Stop
#>
param(
  [ValidateSet("Start", "Stop", "Status")]
  [string]$Action = "Status",
  [string]$ProjectRoot = "C:\Comfy_UI_Main",
  [string]$RemoteHost = "195.26.233.100",
  [string]$RemoteUser = "root",
  [int]$RemotePort = 52077,
  [int]$LocalPort = 8188,
  [string]$RemoteBindHost = "127.0.0.1",
  [int]$RemoteBindPort = 8188,
  [string]$IdentityFile = "",
  [string]$StateFile = ""
)

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "Invoke-EC2ComfyUISshTunnel.ps1") @PSBoundParameters
exit $LASTEXITCODE
