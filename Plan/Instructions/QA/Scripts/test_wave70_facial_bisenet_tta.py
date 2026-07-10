from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pytest
import torch


ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "Plan/07_IMPLEMENTATION/scripts/run_wave70_facial_bisenet_inference.py"
spec = importlib.util.spec_from_file_location("facial_tta", SCRIPT)
assert spec and spec.loader
tta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tta)


def test_hflip_alignment_unflips_width_and_swaps_semantics() -> None:
    logits = torch.zeros((1, 19, 1, 3), dtype=torch.float32)
    logits[0, 2, 0] = torch.tensor([1.0, 2.0, 3.0])
    logits[0, 3, 0] = torch.tensor([4.0, 5.0, 6.0])
    aligned = tta.align_hflip_logits(logits)
    assert aligned[0, 2, 0].tolist() == [6.0, 5.0, 4.0]
    assert aligned[0, 3, 0].tolist() == [3.0, 2.0, 1.0]


def test_hflip_permutation_is_complete_and_involutive() -> None:
    permutation = tta.HFLIP_CHANNEL_PERMUTATION
    assert sorted(permutation) == list(range(19))
    assert tuple(permutation[index] for index in permutation) == tuple(range(19))


def test_alignment_rejects_wrong_channel_count() -> None:
    with pytest.raises(ValueError, match="unexpected_logits_shape"):
        tta.align_hflip_logits(torch.zeros((1, 18, 2, 2)))


def test_save_masks_preserves_index_name_contract(tmp_path: Path) -> None:
    parsing = np.array([[0, 2], [3, 18]], dtype=np.uint8)
    emitted = tta.save_masks(parsing, tmp_path, "sample")
    assert emitted == ["00_background.png", "02_l_brow.png", "03_r_brow.png", "18_hat.png"]


def test_infer_logits_mean_fuses_aligned_flip() -> None:
    class Stub(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.calls = 0

        def forward(self, tensor: torch.Tensor) -> tuple[torch.Tensor]:
            self.calls += 1
            logits = torch.zeros((1, 19, 1, 2), dtype=torch.float32)
            logits[:, 2] = float(self.calls)
            return (logits,)

    net = Stub()
    result = tta.infer_logits(net, torch.zeros((1, 3, 1, 2)), "hflip_logit_mean")
    assert net.calls == 2
    assert torch.all(result[:, 2] == 0.5)
    assert torch.all(result[:, 3] == 1.0)
