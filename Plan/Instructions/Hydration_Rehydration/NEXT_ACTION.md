# Next Action

Commit and push the EC2 project sync evidence, then run bounded EC2 runtime inventory:

```powershell
git -C C:\Comfy_UI_Main status --branch --short
git -C C:\Comfy_UI_Main add Plan\Instructions
git -C C:\Comfy_UI_Main commit -m "Runtime: record EC2 project sync"
git -C C:\Comfy_UI_Main push origin main
```

After the checkpoint is clean, start only `i-0560bf8d143f93bb1`, use SSM to inventory `/home/ubuntu/ComfyUI` model folders and `/home/ubuntu/Comfy_UI_Main` workflow/runtime files, then stop EC2 and verify final state is `stopped`.

Do not run generation or download models during inventory.
