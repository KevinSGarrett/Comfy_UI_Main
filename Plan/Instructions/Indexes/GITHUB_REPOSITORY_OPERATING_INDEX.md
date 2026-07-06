<!--
Wave 59 — Full Local / GitHub / AWS / Directory Index + Catalogue System
Target path after extraction: C:\Comfy_UI_Main\Plan\Instructions\Indexes
Generated: 2026-07-06T04:53:12Z
-->

# GITHUB_REPOSITORY_OPERATING_INDEX

## 1. Purpose

This file tells Codex Desktop how to understand and verify the GitHub side of the `Comfy_UI_Main` project.

This is a personal project. The GitHub workflow can be intentionally lightweight, but Codex must still protect secrets, keep useful checkpoints, and avoid losing work.

## 2. Canonical repository

```text
Repository:
https://github.com/KevinSGarrett/Comfy_UI_Main

Expected local Git root:
C:\Comfy_UI_Main\

Expected token source:
C:\Comfy_UI_Main\.env
```

## 3. Secret handling

Codex must:

1. Never print token values.
2. Never commit `.env`.
3. Never copy `.env` into reports or indexes.
4. Never include token values in generated docs.
5. Never include private keys, AWS credentials, GitHub tokens, Civitai API keys, or other secrets in cumulative zips.
6. Verify `.gitignore` excludes `.env`, common secrets, logs with secrets, and credential files.

Recommended `.gitignore` protection entries:

```text
.env
*.pem
*.key
*credentials*
*secret*
.aws/
```

Codex may mention that a token is expected in `.env`, but it must not include the token value.

## 4. Minimal personal-project GitHub workflow

Because this is a personal project and not a commercial production repo, Codex may use a minimal workflow:

1. Check local status.
2. Pull/fetch if safe.
3. Make changes locally.
4. Run validation.
5. Update tracker and hydration files.
6. Commit a meaningful checkpoint.
7. Push to GitHub.
8. Record commit hash in tracker/hydration state.

PRs, heavy review branches, branch protection, and formal production gates are not required unless a later instruction explicitly adds them.

## 5. Required Git verification commands

Codex should use equivalent commands:

```powershell
cd C:\Comfy_UI_Main

git rev-parse --show-toplevel
git remote -v
git status --short
git branch --show-current
git rev-parse HEAD
git fetch --all --prune
git status --branch --short
```

Codex must verify the remote points to:

```text
https://github.com/KevinSGarrett/Comfy_UI_Main
```

If the remote differs, Codex must stop and record a blocker before pushing.

## 6. Local-vs-remote match verification

Codex must check:

| Check | Expected outcome |
|---|---|
| Git root | `C:\Comfy_UI_Main` |
| Remote URL | `https://github.com/KevinSGarrett/Comfy_UI_Main` |
| Working tree | Only intentional changes are present |
| `.env` | Exists locally if needed, not tracked |
| Plan files | Current local changes are reflected before commit |
| Tracker | Updated for any completed or failed task |
| Hydration state | Updated before commit |
| Generated indexes | Regenerated if directory contents changed |
| Validation report | Present for the wave or task |

## 7. Commit message format

Use clear checkpoint messages:

```text
Wave 59: add project location indexes and catalogue system
Wave ##: implement <specific subsystem>
Fix: repair <specific broken workflow/path/test>
QA: add evidence for <artifact/test group>
Tracker: update completion state for <item range>
```

Do not use vague messages like:

```text
update
fix stuff
misc
changes
```

## 8. When Codex should not push

Codex must not push if:

- secrets are staged
- tests fail and no failure report is recorded
- tracker falsely claims completion
- cumulative pack is missing prior wave content
- generated files are corrupt
- AWS state was changed but not restored
- `.env` or credentials appear in staged changes
- Git remote is not the expected repository
- Codex is unsure whether changes belong to this project

## 9. GitHub conflict handling

If conflicts occur:

1. Stop automated pushing.
2. Record the conflict in `Hydration_Rehydration\BLOCKERS.md`.
3. Inspect conflicting files.
4. Preserve both user-created and Codex-created work.
5. Resolve only when the intended source-of-truth is clear.
6. Run validation again.
7. Update tracker and hydration state.
8. Commit only after validation.

## 10. GitHub status in Wave 59

Wave 59 defines the GitHub operating index. It does not claim that GitHub was contacted or that the remote repo was modified. Codex must perform live Git checks inside `C:\Comfy_UI_Main` during actual local execution.
