# Wave 43 Local, EC2, and Runtime Proof Chain

## Proof chain
```text
plan → preview → preview QA → preflight → local run or EC2 run → output artifact
→ manifest → QA evidence → state diff → release decision
```

## EC2 rule
EC2 is not a default workspace. It is a runtime proof/expensive render worker used only when gated and cataloged.
