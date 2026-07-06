# Wave 64 Scope

Wave 64 adds strict AI-operational end-to-end Items and Tracker coverage.

This wave exists because the autonomous session is responsible for the full build and the full QA surface, including implementation, testing, workflow validation, runtime proof, visual review, audio review, multimodal review, blocker handling, cost control, and final certification.

## Hard Rules

- `Plan\Items` and `Plan\Tracker` must contain current strict AI coverage rows in addition to the legacy master packages.
- Every strict row must cite a `C:\Comfy_UI_Main\Plan` source file with section, line start, line end, excerpt, and source key.
- Every generated image, video, GIF, or audio artifact must be reviewed as a whole artifact.
- Localized visual/audio work cannot pass if any unrelated global artifact defect is visible or audible.
- No row is complete until structured evidence exists and the strict pass/fail gate is recorded.

## Primary Outputs

```text
Plan\Items\wave64_end_to_end_strict_ai_itemized_list.csv
Plan\Items\Waves\Wave64\WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv
Plan\Tracker\wave64_end_to_end_strict_ai_tracker.csv
Plan\Tracker\Waves\Wave64\WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv
Plan\Items\Reports\wave64_end_to_end_strict_ai_coverage_report.json
Plan\Tracker\Reports\wave64_end_to_end_strict_ai_coverage_report.json
```

## Validation

Run:

```powershell
python C:\Comfy_UI_Main\Plan\Items\Scripts\generate_wave64_end_to_end_ai_coverage.py
```

Expected result is `pass`.
