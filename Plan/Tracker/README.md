# Tracker Package - Waves 48-52 Legacy Coverage plus Wave 64/65 Strict AI Coverage

Target local path:

```text
C:\Comfy_UI_Main\Plan\Tracker
```

This package contains the autonomous tracker system for Codex Desktop.
Wave 64 is the current strict AI-operational tracker layer for end-to-end build, QA, visual review, audio review, runtime proof, and release certification.
Wave 65 is the current exhaustive Plan source coverage closure for every file under `C:\Comfy_UI_Main\Plan`.

## Tracker Waves

- Wave 48 - Source citation framework
- Wave 49 - Autonomous execution tracker controls
- Wave 50 - Strict QA, testing, and visual review tracker
- Wave 51 - Local, repo, ComfyUI, app, and EC2 runtime tracker
- Wave 52 - Tracker validation, handoff, and release control
- Wave 64 - End-to-end strict AI build, QA, visual review, audio review, runtime, and release coverage
- Wave 65 - Exhaustive direct Plan file source coverage closure

## Master Trackers

Legacy autonomous tracker:

```text
wave48_52_master_autonomous_tracker.csv
```

Current strict AI tracker:

```text
wave64_end_to_end_strict_ai_tracker.csv
Waves\Wave64\WAVE64_END_TO_END_STRICT_AI_TRACKER_ROWS.csv
Reports\wave64_end_to_end_strict_ai_coverage_report.json
```

Current exhaustive Plan source tracker:

```text
wave65_plan_source_coverage_closure_tracker.csv
Waves\Wave65\WAVE65_PLAN_SOURCE_COVERAGE_TRACKER_ROWS.csv
Reports\wave65_plan_source_coverage_report.json
```

## Citation Rule

Every strict tracker row must include source citation file, full path, section, line start, line end, excerpt, and source key back to:

```text
C:\Comfy_UI_Main\Plan
```

## Autonomy Rule

Codex Desktop must treat `Human_Input_Allowed=FALSE` and `Human_Work_Allowed=FALSE` as hard execution constraints.
If blocked, it must create blocker evidence and continue with safe autonomous rerouting.
For Wave 64, localized work cannot pass localized-only review. The tracker requires whole-artifact visual/audio review so defects outside the target edit region still block promotion.
For Wave 65, every current Plan file must have direct Items/Tracker source coverage. Rerun `Plan\Items\Scripts\generate_wave65_plan_source_coverage.py` after any Plan file is added or renamed.
