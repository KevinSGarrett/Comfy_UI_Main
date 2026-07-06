# Next Action

Commit and push the EC2 runtime inventory evidence, then select the lowest-risk workflow lane:

```powershell
git -C C:\Comfy_UI_Main status --branch --short
git -C C:\Comfy_UI_Main add Plan\Instructions
git -C C:\Comfy_UI_Main commit -m "Runtime: record EC2 inventory"
git -C C:\Comfy_UI_Main push origin main
```

After the checkpoint is clean, inspect `Plan\07_IMPLEMENTATION\workflow_templates\base_generation\*\runtime_requirements.example.json` and match the safest candidate against EC2 inventory evidence.

Do not run generation until prerequisite matching is recorded.
