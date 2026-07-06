# Wave 24 Delivery Report

Wave 24 extends the cumulative blueprint with **Multi-Character Instance Layout**.

## Added capability
The system can now represent each visible character as an explicit instance with:

- character instance id
- identity id / character bible binding
- person-instance mask
- skeleton / pose map id
- body-region ownership map
- frame placement box
- depth layer / occlusion order
- contact graph participation
- per-instance QA evidence requirements

## Promotion boundary
No downstream pass may treat the scene as one anonymous body/mask if more than one character is present. Every image/refine/contact/deformation/hard-anatomy pass must declare which instance owns the target region.
