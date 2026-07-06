param(
  [string]$Root = "C:\Comfy_UI_Main\Plan\Tracker"
)
$ErrorActionPreference = "Stop"
python "$Root\Scripts\validate_tracker_package.py" "$Root"
