# Items Package - Waves 53-57 Legacy Coverage plus Wave 64/65 Strict AI Coverage

Target local path:

```text
C:\Comfy_UI_Main\Plan\Items
```

This package contains source-cited itemized lists for the autonomous project.
Wave 64 is the current strict AI-operational coverage layer for end-to-end build, QA, visual review, audio review, runtime proof, and release certification.
Wave 65 is the current exhaustive Plan source coverage closure for every file under `C:\Comfy_UI_Main\Plan`.

## Item Waves

- Wave 53 - Source-cited item taxonomy
- Wave 54 - Implementation requirements item catalog
- Wave 55 - QA, testing, and visual review item catalog
- Wave 56 - Autonomous runtime and no-human-input item catalog
- Wave 57 - Validation, handoff, and certification item catalog
- Wave 64 - End-to-end strict AI build, QA, visual review, audio review, runtime, and release coverage
- Wave 65 - Exhaustive direct Plan file source coverage closure

## Master Lists

Legacy source-cited itemized list:

```text
wave53_57_master_itemized_list.csv
```

Current strict AI coverage list:

```text
wave64_end_to_end_strict_ai_itemized_list.csv
Waves\Wave64\WAVE64_END_TO_END_STRICT_AI_ITEM_ROWS.csv
Reports\wave64_end_to_end_strict_ai_coverage_report.json
```

Current exhaustive Plan source coverage list:

```text
wave65_plan_source_coverage_closure_itemized_list.csv
Waves\Wave65\WAVE65_PLAN_SOURCE_COVERAGE_ITEM_ROWS.csv
Reports\wave65_plan_source_coverage_report.json
```

## Citation Rule

Every strict item must include source citation file, full path, section, line start, line end, excerpt, and source key back to:

```text
C:\Comfy_UI_Main\Plan
```

## Autonomy Rule

Every item is designed for Codex Desktop autonomous implementation with no human work dependency.
For Wave 64, localized work cannot pass localized-only review. Every generated image, video, GIF, or audio artifact must receive whole-artifact review in addition to any target-region review.
For Wave 65, every current Plan file must have direct Items/Tracker source coverage. Rerun `Plan\Items\Scripts\generate_wave65_plan_source_coverage.py` after any Plan file is added or renamed.
