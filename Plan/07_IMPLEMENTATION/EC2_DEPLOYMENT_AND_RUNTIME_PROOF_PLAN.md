# EC2 Deployment and Runtime Proof Plan

## Purpose

EC2 is the expensive GPU proof worker. It should be off unless running a runtime proof or final render.

## Deployment flow

```text
Local repo commit
  → local validation
  → generate runtime model requirement manifest
  → start EC2
  → sync repo files only
  → hydrate required models from S3
  → run ComfyUI object_info snapshot
  → run selected workflow API tests
  → collect outputs/logs/manifests/QA
  → sync evidence back to local/S3
  → stop EC2
```

## Runtime proof manifest fields

```json
{
  "commit_sha": "...",
  "workflow_id": "...",
  "required_models": [],
  "required_inputs": [],
  "output_prefix": "...",
  "qa_gates": [],
  "ec2_instance_id": "...",
  "started_at": "...",
  "stopped_at": "..."
}
```

## Failure handling

If any step fails, the script must:

1. save logs,
2. save partial manifest,
3. attempt EC2 stop,
4. mark the proof failed,
5. block promotion.
