# Wave 43 Runtime Proof Escalation and Pullback

## Proof escalation

```text
metadata proof
→ proxy preview proof
→ local runtime proof
→ EC2 preview proof
→ EC2 final proof
→ QA evidence
→ release decision
```

## Pullback artifacts

Every runtime/EC2 run must pull back:

- output artifact
- run log
- manifest
- QA evidence
- cost/time summary
- failure report if failed
- stop confirmation if EC2 used
