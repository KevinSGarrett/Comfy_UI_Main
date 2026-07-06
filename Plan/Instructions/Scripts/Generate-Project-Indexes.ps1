<#
Wave 59 helper script
Purpose:
  Regenerate local Plan / Items / Tracker / Instructions file indexes for Codex Desktop.

Run from PowerShell:

  powershell -ExecutionPolicy Bypass -File C:\Comfy_UI_Main\Plan\Instructions\Scripts\Generate-Project-Indexes.ps1

This script intentionally does NOT read or print .env contents.
#>

param(
    [string]$ProjectRoot = "C:\Comfy_UI_Main",
    [string]$OutDir = "C:\Comfy_UI_Main\Plan\Instructions\Indexes\Generated"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$PlanRoot = Join-Path $ProjectRoot "Plan"
$ItemsRoot = Join-Path $PlanRoot "Items"
$TrackerRoot = Join-Path $PlanRoot "Tracker"
$InstructionsRoot = Join-Path $PlanRoot "Instructions"

$null = New-Item -ItemType Directory -Force -Path $OutDir

function Get-Purpose {
    param([string]$RelativePath)

    $p = $RelativePath.Replace("\", "/").ToLowerInvariant()

    if ($p -match "/blueprint_source/") { return "Authoritative blueprint/reference source file; read-only unless explicit blueprint update is requested." }
    if ($p -match "/plan/items/") { return "Itemized backlog/scope file or items coverage evidence." }
    if ($p -match "/plan/tracker/") { return "Execution tracker, progress state, QA status, blocker, or coverage evidence." }
    if ($p -match "/hydration_rehydration/") { return "Session continuity state used for Codex rehydration/resume." }
    if ($p -match "/instructions/indexes/") { return "Location/file/resource index used for project awareness." }
    if ($p -match "/instructions/reports/") { return "Wave delivery, validation, or file report." }
    if ($p -match "/instructions/manifests/") { return "Machine-readable package manifest." }
    if ($p -match "/instructions/templates/") { return "Reusable Codex instruction or certification template." }
    if ($p -match "/instructions/waves/") { return "Wave-specific supplement, report, or package artifact." }
    if ($p -match "/instructions/source_context/") { return "Source upload context, hash, or inventory summary." }
    if ($p.EndsWith(".md")) { return "Markdown documentation/instruction/reference file." }
    if ($p.EndsWith(".csv")) { return "Tabular tracker/index/audit data." }
    if ($p.EndsWith(".json")) { return "Machine-readable manifest/configuration/validation data." }
    if ($p.EndsWith(".ps1")) { return "PowerShell automation/helper script." }
    if ($p.EndsWith(".py")) { return "Python automation/helper script." }
    return "Project file; inspect context before modifying."
}

function Get-UpdatePolicy {
    param([string]$RelativePath)

    $p = $RelativePath.Replace("\", "/").ToLowerInvariant()

    if ($p -match "/blueprint_source/") { return "read_only_reference" }
    if ($p -match "/plan/items/") { return "update_when_scope_or_item_state_changes" }
    if ($p -match "/plan/tracker/") { return "update_continuously_for_progress_qa_and_completion" }
    if ($p -match "/hydration_rehydration/") { return "update_continuously_and_before_session_end" }
    if ($p -match "/instructions/indexes/generated/") { return "regenerate_when_file_tree_changes" }
    if ($p -match "/instructions/reports/") { return "add_or_regenerate_per_wave" }
    if ($p -match "/instructions/manifests/") { return "regenerate_per_cumulative_pack" }
    if ($p -match "/instructions/waves/") { return "add_per_wave" }
    if ($p -match "/instructions/templates/") { return "read_only_unless_template_upgrade_requested" }
    if ($p -match "/instructions/") { return "read_only_unless_instruction_wave_or_correction_requires_update" }
    return "inspect_before_update"
}

function Get-RelativePathCompat {
    param(
        [string]$BasePath,
        [string]$TargetPath
    )

    # Windows PowerShell 5.1 does not expose [System.IO.Path]::GetRelativePath.
    $separator = [System.IO.Path]::DirectorySeparatorChar.ToString()
    $baseFull = [System.IO.Path]::GetFullPath($BasePath)
    if (!$baseFull.EndsWith($separator)) {
        $baseFull = "$baseFull$separator"
    }

    $targetFull = [System.IO.Path]::GetFullPath($TargetPath)
    $baseUri = New-Object System.Uri($baseFull)
    $targetUri = New-Object System.Uri($targetFull)
    $relativeUri = $baseUri.MakeRelativeUri($targetUri)
    $relativePath = [System.Uri]::UnescapeDataString($relativeUri.ToString())
    return $relativePath.Replace("/", $separator)
}

function Get-FileRecord {
    param(
        [System.IO.FileInfo]$File,
        [string]$Base
    )

    $relative = Get-RelativePathCompat -BasePath $ProjectRoot -TargetPath $File.FullName
    $hash = Get-FileHash -Algorithm SHA256 -LiteralPath $File.FullName

    [PSCustomObject]@{
        relative_path = $relative
        full_path = $File.FullName
        size_bytes = $File.Length
        sha256 = $hash.Hash.ToLowerInvariant()
        extension = $File.Extension
        last_write_time = $File.LastWriteTime.ToString("s")
        purpose = Get-Purpose -RelativePath $relative
        update_policy = Get-UpdatePolicy -RelativePath $relative
    }
}

function Export-Index {
    param(
        [string]$Name,
        [string]$RootPath
    )

    if (!(Test-Path -LiteralPath $RootPath)) {
        Write-Warning "Path missing: $RootPath"
        return
    }

    $records = Get-ChildItem -LiteralPath $RootPath -Recurse -File -Force |
        Where-Object {
            $_.FullName -notmatch "\\\.git\\" -and
            $_.Name -ne ".env" -and
            $_.FullName -notmatch "\\node_modules\\" -and
            $_.FullName -notmatch "\\__pycache__\\"
        } |
        Sort-Object FullName |
        ForEach-Object { Get-FileRecord -File $_ -Base $RootPath }

    $csvPath = Join-Path $OutDir "$Name.csv"
    $jsonPath = Join-Path $OutDir "$Name.json"

    $records | Export-Csv -NoTypeInformation -Encoding UTF8 -Path $csvPath
    $records | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 -Path $jsonPath

    Write-Host "Wrote $csvPath"
    Write-Host "Wrote $jsonPath"
}

Export-Index -Name "plan_file_index" -RootPath $PlanRoot
Export-Index -Name "items_file_index" -RootPath $ItemsRoot
Export-Index -Name "tracker_file_index" -RootPath $TrackerRoot
Export-Index -Name "instructions_file_index" -RootPath $InstructionsRoot

Write-Host "Index generation complete. Output: $OutDir"
