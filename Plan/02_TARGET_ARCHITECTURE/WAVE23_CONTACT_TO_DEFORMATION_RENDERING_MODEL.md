# Wave 23 Contact-to-Deformation Rendering Model

A contact edge becomes a deformation event only when all of the following are true:

1. source/target ownership is known,
2. target material profile is known,
3. the deformation mode is allowed for that material pair,
4. the mask scope is defined,
5. the intended pressure tier is defined,
6. a preservation boundary is defined.

## Rendering principle
- Small contact area + low pressure -> micro indentation / subtle compression.
- Small contact area + medium/high pressure -> finger indentation / sharper contact shadow / localized displacement.
- Large contact area + medium pressure -> broad compression or support-surface flattening.
- Tangential vector + medium/high pressure -> pull, drag, or shear look.
- Opposing vectors -> pull apart / push together class.
