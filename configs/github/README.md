# GitHub Control Plane

`main-protection-ruleset.json` is the canonical GitHub ruleset for this
repository. It protects the default branch without owner bypass, requires a
pull request, requires resolved review threads, and requires the strict
`Required preflight and package` check.

Use `tools/github/Test-GitHubMainProtectionRulesetDrift.ps1` for read-only
verification. Use `tools/github/Set-GitHubMainProtectionRuleset.ps1 -Apply`
only under Codex final GitHub mutation authority. Cursor and Claude may review
the payload or verifier output but must never apply the ruleset.

The zero-approval pull-request rule preserves autonomous solo operation while
preventing direct pushes from bypassing clean-environment validation.
