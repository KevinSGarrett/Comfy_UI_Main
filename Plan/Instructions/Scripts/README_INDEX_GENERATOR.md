# Wave 59 Index Generator Script

Run this on the live Windows project after extracting the cumulative pack:

```powershell
powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Scripts\Generate-Project-Indexes.ps1
```

The script regenerates machine-readable CSV and JSON inventories for:

```text
C:\Comfy_UI_Main\Plan
C:\Comfy_UI_Main\Plan\Items
C:\Comfy_UI_Main\Plan\Tracker
C:\Comfy_UI_Main\Plan\Instructions
```

It does not read or print `.env` contents.
