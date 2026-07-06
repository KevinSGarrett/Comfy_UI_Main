# Wave 60 Operational Done Gates

Codex Desktop must use these done gates before declaring operational work complete.

## GitHub done gate

```text
[ ] remote verified
[ ] safe files staged
[ ] secret/binary guard passed
[ ] commit created when needed
[ ] push completed when needed
[ ] tracker/hydration updated
```

## AWS/EC2 done gate

```text
[ ] AWS account verified
[ ] instance identity verified
[ ] start reason valid
[ ] SSM or command channel verified
[ ] runtime command executed
[ ] artifact pullback attempted/completed
[ ] EC2 stopped
[ ] stopped state verified
[ ] run record written
```

## Civitai/model done gate

```text
[ ] model need statement exists
[ ] metadata lookup completed
[ ] duplicate check completed
[ ] compatibility lane assigned
[ ] download verified if performed
[ ] registry updated
[ ] runtime validation queued or passed
[ ] QA result recorded
```

## Sync done gate

```text
[ ] source and destination verified
[ ] method selected
[ ] manifest written
[ ] hashes/commit verified
[ ] tracker updated
```
