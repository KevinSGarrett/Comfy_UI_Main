# Wave 17 — Large Mask Body Correction Strategy

## Why large masks are needed
Body shape and proportion corrections are not micro-detail tasks. Fixing stomach, waist, hips, thighs, and silhouette requires large coherent masks so the model can reshape the region without leaving seams or warped anatomy.

## Mask hierarchy used by Wave 17
- Person-instance mask: defines which character owns the correction.
- Major body-region masks: abdomen, waist, hips, thighs, outer silhouette.
- Minor protection masks: hands, face, props, clothing edges.
- Edge masks: silhouette cleanup and fabric boundary repair.
- Preservation masks: regions that must stay unchanged.

## Large-mask rules
1. Always start from a person-instance mask.
2. Add only the target body regions needed by the request.
3. Add protection masks for face, hands, important props, and background.
4. Use feathering/dilation/blur settings appropriate to the size of the body change.
5. Keep left/right paired regions synchronized.
6. Run silhouette QA before promotion.
7. Run clothing and skin continuity QA after any shape pass.

## Safe denoise guidance
- 0.06–0.16: cleanup / edge blend.
- 0.10–0.22: fabric and skin continuity repair.
- 0.14–0.24: subtle stomach/waist correction.
- 0.18–0.34: hip/thigh/silhouette correction.
- 0.22–0.38: high-risk silhouette repair only with review.

## Anti-corruption rules
- Do not let body masks touch the face unless the face is explicitly targeted by another pass.
- Do not let body masks include another person.
- Do not let body masks include hands/contact regions unless a separate contact pass owns them.
- Do not use the same mask for stomach, waist, hips, and thighs if separate control is needed.
