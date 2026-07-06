# Cumulative Packaging Rules

1. Every wave updates the same blueprint package root.
2. No wave may ship only its own new documents; it must include the prior cumulative package plus updates.
3. Every wave must update:
   - README.md
   - 00_PROJECT_CONTROL/WAVE_00_TO_19_MASTER_SCHEDULE.md when scope changes
   - PROJECT_MANIFEST.json
   - 11_RELEASES/WAVE##_DELIVERY_REPORT.md
   - 11_RELEASES/WAVE##_VALIDATION_REPORT.json
4. Every new workflow/config/schema/script must be listed in the manifest.
5. Every ComfyUI workflow must have:
   - UI JSON when needed
   - API JSON when it will be run by the orchestrator
   - required model/node list
   - smoke-test plan
   - expected outputs
   - QA gates
6. Every model/LoRA selection must be routed by compatibility registry. Do not rely on file names alone.
7. Every local edit must have mask evidence and crop QA evidence.
8. Every video/GIF output must have frame evidence and temporal QA.
9. Every audio output must have timing, sync, and mix QA.
10. Promotion requires runtime proof, not notes.
