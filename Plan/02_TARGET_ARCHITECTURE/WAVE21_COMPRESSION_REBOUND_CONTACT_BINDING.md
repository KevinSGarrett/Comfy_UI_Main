# Wave 21 Compression / Rebound Contact Binding

Compression and rebound require contact or support context.

## Required context
- target region id
- owned mask id
- contact owner id or support surface id
- material profile id
- compression depth profile
- rebound profile for video/motion use

## Contact examples
- hand pressing skin or fabric
- body resting on cushion/furniture
- clothing elastic compressing skin
- body region constrained by another object

## Failure conditions
- compression without a contact owner
- rebound without a preceding compression or movement event
- deformation outside the owned mask
- deformation that changes approved body proportions
