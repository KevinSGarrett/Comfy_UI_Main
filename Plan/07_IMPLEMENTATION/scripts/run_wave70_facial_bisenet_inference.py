#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image


CLASS_NAMES = (
    "background", "skin", "l_brow", "r_brow", "l_eye", "r_eye", "eye_g", "l_ear", "r_ear", "ear_r",
    "nose", "mouth", "u_lip", "l_lip", "neck", "neck_l", "cloth", "hair", "hat",
)
HFLIP_CHANNEL_PERMUTATION = (0, 1, 3, 2, 5, 4, 6, 8, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18)
EAR_CLASS_INDICES = (7, 8, 9)
EAR_MULTISCALE_SIZES = (384, 512, 640)
MEAN = torch.tensor((0.485, 0.456, 0.406), dtype=torch.float32).view(3, 1, 1)
STD = torch.tensor((0.229, 0.224, 0.225), dtype=torch.float32).view(3, 1, 1)


def image_tensor(path: Path) -> torch.Tensor:
    with Image.open(path) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    tensor = torch.from_numpy(rgb).permute(2, 0, 1)
    return ((tensor - MEAN) / STD).unsqueeze(0)


def align_hflip_logits(logits: torch.Tensor) -> torch.Tensor:
    if logits.ndim != 4 or logits.shape[1] != len(CLASS_NAMES):
        raise ValueError(f"unexpected_logits_shape:{tuple(logits.shape)}")
    spatially_aligned = torch.flip(logits, dims=(3,))
    permutation = torch.tensor(HFLIP_CHANNEL_PERMUTATION, device=logits.device)
    return spatially_aligned.index_select(1, permutation)


def infer_logits(net: torch.nn.Module, tensor: torch.Tensor, mode: str) -> torch.Tensor:
    original = net(tensor)[0]
    if mode == "single_pass":
        return original
    if mode != "hflip_logit_mean":
        raise ValueError(f"unsupported_inference_mode:{mode}")
    flipped = net(torch.flip(tensor, dims=(3,)))[0]
    return 0.5 * (original + align_hflip_logits(flipped))


def infer_ear_multiscale_masks(net: torch.nn.Module, tensor: torch.Tensor) -> tuple[torch.Tensor, dict[int, np.ndarray]]:
    base_size = tensor.shape[-2:]
    base_logits: torch.Tensor | None = None
    ear_masks = {class_index: np.zeros(base_size, dtype=bool) for class_index in EAR_CLASS_INDICES}
    for size in EAR_MULTISCALE_SIZES:
        scaled = tensor if tuple(base_size) == (size, size) else F.interpolate(
            tensor, size=(size, size), mode="bilinear", align_corners=False
        )
        logits = net(scaled)[0]
        if logits.shape[-2:] != base_size:
            logits = F.interpolate(logits, size=base_size, mode="bilinear", align_corners=False)
        if size == 512:
            base_logits = logits
        parsing = logits.argmax(dim=1).squeeze(0).cpu().numpy()
        for class_index in EAR_CLASS_INDICES:
            ear_masks[class_index] |= parsing == class_index
    if base_logits is None:
        raise ValueError("ear_multiscale_missing_canonical_scale")
    return base_logits, ear_masks


def save_masks(
    parsing: np.ndarray,
    output_root: Path,
    sample_name: str,
    class_mask_overrides: dict[int, np.ndarray] | None = None,
) -> list[str]:
    sample_dir = output_root / "masks" / sample_name
    sample_dir.mkdir(parents=True, exist_ok=True)
    emitted: list[str] = []
    class_indices = {int(value) for value in np.unique(parsing)}
    if class_mask_overrides:
        for index, mask in class_mask_overrides.items():
            if index < 0 or index >= len(CLASS_NAMES):
                raise ValueError(f"override_class_index_out_of_range:{index}")
            if mask.shape != parsing.shape:
                raise ValueError(f"override_mask_shape_mismatch:{index}:{mask.shape}!={parsing.shape}")
        class_indices.update(index for index, mask in class_mask_overrides.items() if np.any(mask))
    for class_index in sorted(class_indices):
        index = int(class_index)
        if index < 0 or index >= len(CLASS_NAMES):
            raise ValueError(f"predicted_class_index_out_of_range:{index}")
        path = sample_dir / f"{index:02d}_{CLASS_NAMES[index]}.png"
        mask = class_mask_overrides.get(index) if class_mask_overrides else None
        if mask is None:
            mask = parsing == index
        Image.fromarray(mask.astype(np.uint8) * 255, mode="L").save(path)
        emitted.append(path.name)
    return emitted


def main() -> int:
    parser = argparse.ArgumentParser(description="Run BiSeNet facial parsing with bounded inference variants.")
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument(
        "--mode", choices=("single_pass", "hflip_logit_mean", "ear_multiscale_union_v1"), required=True
    )
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()

    from face_parsing.model import BiSeNet

    device = torch.device(args.device)
    if device.type == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("cuda_required_but_unavailable")
    checkpoint = Path(args.checkpoint).resolve()
    net = BiSeNet(n_classes=len(CLASS_NAMES)).to(device)
    state = torch.load(checkpoint, map_location=device, weights_only=True)
    net.load_state_dict(state)
    net.eval()

    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    images = sorted(path for path in input_dir.iterdir() if path.suffix.lower() in (".jpg", ".jpeg", ".png"))
    if not images:
        raise ValueError("route_input_images_empty")
    records = []
    with torch.inference_mode():
        for path in images:
            tensor = image_tensor(path).to(device)
            ear_overrides = None
            if args.mode == "ear_multiscale_union_v1":
                logits, ear_overrides = infer_ear_multiscale_masks(net, tensor)
            else:
                logits = infer_logits(net, tensor, args.mode)
            parsing = logits.argmax(dim=1).squeeze(0).cpu().numpy().astype(np.uint8)
            emitted = save_masks(parsing, output_dir, path.stem, ear_overrides)
            records.append({"sample_id": path.stem, "emitted_masks": emitted})
    print(json.dumps({"result": "pass_facial_bisenet_inference", "mode": args.mode, "samples": records}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
