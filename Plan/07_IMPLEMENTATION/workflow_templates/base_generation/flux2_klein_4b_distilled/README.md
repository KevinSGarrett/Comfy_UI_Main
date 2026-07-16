# FLUX.2 Klein 4B Distilled

This module keeps text-to-image and single-reference editing as separate API graphs while sharing the exact official distilled FP8 diffusion model, Qwen 3 4B text encoder, and FLUX.2 VAE.

`workflow.api.json` is the package-compatible canonical alias of `text_to_image.api.json`; the two files must remain byte-identical. `smoke_test_request.json` is the corresponding single-request package contract, while `smoke_test_requests.json` retains the two-capability catalog.

The first proof envelope is deliberately bounded to four steps and 512-class output on the local 8 GB GPU. Failure to load or execute locally may route the same exact stack to the approved A10G target, but it does not authorize a different model or a production claim.

FLUX.2 Dev remains an eligible higher-quality lane for this non-commercial, non-distributed project. Its non-commercial license is recorded as a use boundary, not treated as a technical disqualifier.
