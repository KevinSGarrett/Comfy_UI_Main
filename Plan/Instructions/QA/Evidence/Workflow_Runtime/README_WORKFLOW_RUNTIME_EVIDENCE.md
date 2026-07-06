# Workflow Runtime Evidence

This directory is reserved for live ComfyUI workflow execution records.

Runtime records belong here only after the required static proof exists:

- ComfyUI `/object_info` confirms required nodes.
- Required model paths are resolved.
- Required model hashes are recorded.
- The EC2 instance is stopped or stop failure is recorded after the run.

Generated media artifacts should be pulled back through `Plan/Instructions/Operations/Pulled_Back_Artifacts/` and then routed to the relevant QA review protocol.
