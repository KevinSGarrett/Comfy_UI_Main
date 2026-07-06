# Wave 24 Instance Layout Orchestrator and Rerun Loop

## Decision loop
1. Compile instance layout contract.
2. Validate character count and required instance fields.
3. Verify mask/skeleton/depth consistency.
4. Run or route generation/refine pass.
5. Score evidence.
6. Promote, rerun, split, or block.

## Rerun targets
- layout failure -> rerun base/pose/layout wave
- wrong-character edit -> rerun with stricter instance mask
- merged bodies -> rerun frame/layout/depth wave
- skeleton conflict -> rerun pose/control map wave
- depth conflict -> rerun depth/occlusion pass
