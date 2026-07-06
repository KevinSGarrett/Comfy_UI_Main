# Current Pursuing Goal

## Active Wave
Wave 61 workflow lane selection.

## Goal Statement
Select the lowest-risk ComfyUI workflow lane from the runtime requirement templates and verify model/node prerequisites before attempting a bounded first execution.

## Why This Goal Is Active
EC2 runtime inventory passed. The remote ComfyUI runtime, GPU, model folders, custom nodes, synced project checkout, and seven runtime requirement templates are present. The next safe step is matching a workflow lane to available assets before running generation.

## Current Status
SELECTED_AUTHORED_STATIC_SMOKE_IMAGE_QA_AUTH_GATE_AND_PULLBACK_DRY_RUN_PASS_PENDING_BROWSER_LOGIN

## Last Action
Added an EC2 pullback record helper and generated pending-runtime dry-run evidence so pulled-back artifacts can be counted, hashed, compared to the remote manifest, and routed to QA after runtime execution.

## Next Action
Complete AWS remote login externally, rerun `Test-AwsAuthGate.ps1` until account `029530099913` is verified and `ec2_work_allowed=true`, then run `Invoke-EC2LaneStaticProof.ps1 -Execute` for object-info/path/hash, run `Invoke-ComfyWorkflowSmoke.ps1 -Execute`, pull back the generated image, run `New-EC2PullbackRecord.ps1` on the pullback folder, then run `New-ImageArtifactQARecord.ps1` on the real artifact and complete visual review.
