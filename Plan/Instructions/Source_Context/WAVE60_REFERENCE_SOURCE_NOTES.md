# Wave 60 Reference Source Notes

Reference checks performed during Wave 60 packaging:

- AWS CLI EC2 `describe-instances`, `start-instances`, `stop-instances`, and waiter command references were checked to align the EC2 identity/start/stop protocol.
- AWS Systems Manager `send-command`, Run Command, and `start-session` references were checked to support SSM-first EC2 access.
- GitHub personal access token and REST API authentication documentation was checked to align token handling.
- Civitai REST API reference migration notice was checked; the GitHub wiki now points to the current developer documentation site, and the historical endpoint reference was used only as fallback endpoint context.

These notes are for instruction traceability only. Codex Desktop must re-check current upstream docs before building or changing live API automation that depends on exact endpoint behavior.
