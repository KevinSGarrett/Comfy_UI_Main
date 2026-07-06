# Next Action

Commit and push the EC2 discovery evidence, then run bounded EC2 project sync:

```powershell
git -C C:\Comfy_UI_Main status --branch --short
git -C C:\Comfy_UI_Main add Plan\Instructions
git -C C:\Comfy_UI_Main commit -m "Runtime: record EC2 discovery"
git -C C:\Comfy_UI_Main push origin main
```

After the checkpoint is clean, start only `i-0560bf8d143f93bb1`, use SSM to clone or update `/home/ubuntu/Comfy_UI_Main`, verify the remote checkout matches the pushed local commit, then stop EC2 and verify final state is `stopped`.

Do not run generation, download models, or leave EC2 running during project sync.
