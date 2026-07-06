# Cumulative Wave Pack Build Protocol

## Purpose

This protocol defines how Codex builds cumulative zip packs without losing prior wave content.

## Build rule

Each new wave pack must be built from the latest cumulative pack, not from an empty folder.

Example:

```text
Wave 62 must be built from Wave 61 cumulative.
Wave 61 must be built from Wave 60 cumulative.
```

## Required build steps

1. Identify latest cumulative base zip.
2. Test base zip integrity.
3. Extract base zip to a clean work directory.
4. Confirm expected root folder exists:
   `Comfy_UI_Main`
5. Add or update only the new wave files.
6. Preserve all prior wave files.
7. Generate or update:
   - wave scope
   - wave tracker supplement
   - wave itemized-list supplement
   - delivery report
   - validation report
   - file index
   - manifest
   - extract instructions
8. Validate required files from all prior waves still exist.
9. Run zip integrity test on the final pack.
10. Record packaging limitations honestly.

## Required final zip name format

```text
Comfy_UI_Main_Autonomous_Codex_Desktop_WaveXX_Cumulative.zip
```

For the final five-wave pack:

```text
Comfy_UI_Main_Autonomous_Codex_Desktop_Waves58_62_Cumulative.zip
```

## Prior-wave preservation checks

A cumulative pack must contain:

- Wave 58 master manual files
- Wave 59 index/catalogue files
- Wave 60 operations files
- Wave 61 QA files
- Wave 62 hydration/finalization files

## Do not include

- `.env`
- API tokens
- GitHub tokens
- AWS access keys
- private SSH keys
- model binaries unless explicitly intended
- generated private runtime outputs unless intentionally packaged

## Validation output

Create:

```text
Plan\Instructions\Reports\WAVE62_VALIDATION_REPORT.json
Plan\Instructions\Manifests\wave62_package_manifest.json
```

## If validation fails

Do not deliver the pack as complete. Record:

- missing files
- failed check
- suspected cause
- next action
