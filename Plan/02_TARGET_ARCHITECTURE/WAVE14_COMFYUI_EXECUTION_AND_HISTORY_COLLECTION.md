# ComfyUI Execution and History Collection

Runtime path:
GET /object_info → validate node classes → POST /prompt → monitor /ws or poll → GET /history/{prompt_id} → resolve outputs → QA.

Scripts default to dry-run. Real execution requires --execute.
