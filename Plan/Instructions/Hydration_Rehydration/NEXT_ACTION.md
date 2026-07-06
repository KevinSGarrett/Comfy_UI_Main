# Next Action

Commit and push the readiness preflight evidence, then run bounded EC2 runtime discovery:

```powershell
git -C C:\Comfy_UI_Main status --branch --short
git -C C:\Comfy_UI_Main add Plan\Instructions
git -C C:\Comfy_UI_Main commit -m "Runtime: record readiness preflight"
git -C C:\Comfy_UI_Main push origin main
```

After the GitHub checkpoint is clean, start only `i-0560bf8d143f93bb1`, verify SSM, run minimal remote path/GPU discovery, stop the instance, and verify final state is `stopped`.

Do not print `.env` values. Do not download models or run generation during discovery.
