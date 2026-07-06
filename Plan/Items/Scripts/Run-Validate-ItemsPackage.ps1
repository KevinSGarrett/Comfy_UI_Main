param(
  [string]$Root = "C:\Comfy_UI_Main\Plan\Items"
)
$ErrorActionPreference = "Stop"
python "$Root\Scripts\validate_items_package.py" "$Root"
