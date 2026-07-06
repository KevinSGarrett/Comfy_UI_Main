# Wave 36 Stale Index Policy Expanded

A stale index is a release blocker.

## Stale conditions

- file exists but is not cataloged
- catalog points to a missing file
- workflow exists but is not in workflow catalog
- asset exists but is not in asset catalog
- QA evidence exists but is not linked to a promotion decision
- schema changes but examples are not refreshed
- registry changes but generated index is not refreshed
- release ZIP changes but release manifest hash is not updated
- App Mode control exists but is not mapped to schema/registry/workflow input
- EC2 sync payload exists without an upload manifest

## Release rule

No final handoff or canonical promotion may pass if stale-index blockers exist.
