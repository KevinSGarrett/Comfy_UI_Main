# Inpaint, Detail, Upscale, and Rerun Plan

Regional detail failures should preserve the passing base image, narrow masks, lower denoise, adjust feather/grow, and rerun the local pass instead of rebuilding everything.

Upscale failures should fall back to the approved pre-upscale image and reduce polish strength.
