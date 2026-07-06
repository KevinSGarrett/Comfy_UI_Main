# Wave 35 Expanded Canonical System Structure

The purpose of Wave 35 is to make the project physically understandable.

The system has four primary places where files live:

1. **Local System Root** — the user’s organized working directory.
2. **Git Repository** — source-controlled docs, schemas, scripts, templates, and registries.
3. **ComfyUI Runtime** — executable ComfyUI install, models, inputs, outputs, and active workflows.
4. **App Mode Package** — simplified user-facing apps, controls, presets, and exports.

## Core principle

A file should have exactly one owner domain.

If a file appears in multiple places, one place must be source-of-truth and every other copy must be a runtime copy, export copy, backup copy, or release copy.
