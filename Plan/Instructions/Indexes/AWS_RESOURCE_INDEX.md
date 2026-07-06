<!--
Wave 59 — Full Local / GitHub / AWS / Directory Index + Catalogue System
Target path after extraction: C:\Comfy_UI_Main\Plan\Instructions\Indexes
Generated: 2026-07-06T04:53:12Z
-->

# AWS_RESOURCE_INDEX

## 1. Purpose

This file is the AWS resource awareness index for the ComfyUI autonomous build system.

Codex must use this file before attempting GPU validation, EC2 startup, runtime testing, model validation, or AWS-side artifact pullback.

## 2. Canonical AWS account

```text
AWS Account:
029530099913
```

Codex must verify the active AWS identity before using any AWS resource.

Required identity check:

```powershell
aws sts get-caller-identity
```

Expected account field:

```text
029530099913
```

If the account does not match, Codex must stop immediately and record a blocker.

## 3. Canonical EC2 resource

```text
Instance ID:
i-0560bf8d143f93bb1

Name tag:
ComfyUI-LoRA-GPU-Server

Instance type:
g5.xlarge

IAM profile:
ComfyUI-SSM-Profile

Expected normal idle state:
stopped

Public IP when stopped:
none

Attached EBS volume:
vol-0eb9b2c6d3d2706d6

Volume size:
1024 GB
```

## 4. AWS verification checklist before GPU use

Before starting or using the instance, Codex must verify:

| Check | Required value |
|---|---|
| AWS account | `029530099913` |
| Instance ID | `i-0560bf8d143f93bb1` |
| Name tag | `ComfyUI-LoRA-GPU-Server` |
| Instance type | `g5.xlarge` |
| IAM profile | `ComfyUI-SSM-Profile` |
| EBS volume ID | `vol-0eb9b2c6d3d2706d6` |
| EBS volume size | `1024 GB` |
| Normal idle state | `stopped` |
| Public IP when stopped | none |

Equivalent command:

```powershell
aws ec2 describe-instances --instance-ids i-0560bf8d143f93bb1
aws ec2 describe-volumes --volume-ids vol-0eb9b2c6d3d2706d6
```

## 5. AWS state protection rules

Codex must:

1. Treat stopped as the expected normal idle state.
2. Start the EC2 instance only when GPU runtime validation is actually needed.
3. Avoid leaving the instance running after validation.
4. Record start time, reason, validation performed, stop time, and evidence pulled back.
5. Prefer SSM-based access where available.
6. Avoid manual SSH as the normal workflow.
7. Never start a different GPU instance unless a later explicit instruction replaces this index.
8. Never assume the public IP is stable.
9. Never embed AWS credentials in docs, scripts, trackers, reports, or commits.

## 6. AWS session evidence requirements

Whenever Codex uses AWS, it must record:

```text
AWS account verified:
Instance ID verified:
Instance type verified:
IAM profile verified:
EBS volume verified:
Starting state:
Reason for start:
Tests performed:
Artifacts generated:
Artifacts pulled back:
Logs pulled back:
Final instance state:
Stop confirmation:
Tracker items updated:
Known issues:
```

The evidence must be linked in the Tracker and QA evidence index.

## 7. AWS failure handling

If AWS verification fails, Codex must not continue with GPU testing.

Failure examples:

| Failure | Required response |
|---|---|
| Wrong AWS account | Stop, record blocker. |
| Instance not found | Stop, record blocker. |
| Instance type mismatch | Stop, record blocker. |
| Volume missing or wrong size | Stop, record blocker. |
| IAM profile missing | Stop, record blocker. |
| Instance cannot start | Record failure, do not fake test results. |
| SSM unavailable | Record issue and use approved fallback only if already defined. |
| Stop command fails | Continue attempting safe stop and escalate as blocker. |

## 8. AWS status in Wave 59

Wave 59 defines the AWS resource index and verification requirements. It does not claim that AWS was contacted, that the instance was started, or that EC2 validation was performed.
