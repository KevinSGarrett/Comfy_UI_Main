# Next Action

Initialize and verify Git in the canonical project folder:

```powershell
git -C C:\Comfy_UI_Main init -b main
git -C C:\Comfy_UI_Main remote add origin https://github.com/KevinSGarrett/Comfy_UI_Main.git
git -C C:\Comfy_UI_Main fetch origin
git -C C:\Comfy_UI_Main status --branch --short
git -C C:\Comfy_UI_Main check-ignore -v .env
```

Do not commit, push, pull, or merge until fetch/status results are recorded and local-vs-remote file state is understood.
