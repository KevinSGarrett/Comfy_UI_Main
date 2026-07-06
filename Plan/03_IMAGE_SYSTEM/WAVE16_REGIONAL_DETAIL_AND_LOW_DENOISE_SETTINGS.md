# Wave 16 — Regional Detail and Low-Denoise Settings

## Regional detail targets

The regional detail system can refine:

- face;
- eyes;
- mouth/teeth;
- hands;
- skin/material texture;
- hair boundary;
- fabric folds;
- prop contact edges;
- shadow/contact regions;
- minor artifact regions.

## Mask sizing

The mask should be as small as possible while still including enough feather/blend boundary to avoid harsh edges.

## Denoise defaults

| Region | Default denoise | Notes |
|---|---:|---|
| Face identity-sensitive | 0.10–0.18 | Use reference lock and identity QA |
| Hands | 0.12–0.24 | Use pose/control map when available |
| Skin/material texture | 0.12–0.24 | Avoid waxy overprocessing |
| Fabric folds | 0.14–0.28 | Keep original garment shape |
| Contact edge/shadow | 0.16–0.30 | Match lighting and contact geometry |
| Prop cleanup | 0.12–0.26 | Preserve prop placement |
| Tiny artifact repair | 0.06–0.16 | Prefer tiny mask/crop |

## Avoiding corruption

Do not use regional passes to secretly change global body shape, pose, camera, character count, outfit, or environment. Those belong to a new base-generation or reconstruction pass.

## Mask evidence

Every regional pass must record:

- mask id;
- mask file path;
- owner character/prop/environment id;
- target region;
- feather radius;
- allowed change area;
- output diff outside mask.
