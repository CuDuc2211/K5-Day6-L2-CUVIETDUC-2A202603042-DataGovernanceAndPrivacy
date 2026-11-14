"""T02 baseline: measurable, reproducible, and not a random score."""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src import main as runner
from src.common.image_ops import laplacian_variance, load_rgb


INPUT = Path("fixtures/t02_raw_qc")


def test_laplacian_baseline_writes_all_predictions_and_top20(tmp_path):
    out = tmp_path / "baseline"
    rc = runner.main([
        "--track", "t02", "--pipeline", "src.baseline_t02",
        "--output", str(out), "--run-name", "baseline", "--offline", "--seed", "42",
    ])
    assert rc == 0
    source = pd.read_csv(INPUT / "images.csv")
    pred = pd.read_csv(out / "ranked_review.csv")
    queue = pd.read_csv(out / "review_queue.csv")
    assert len(pred) == len(source) == 96
    assert pred.image_id.is_unique
    assert set(pred.image_id) == set(source.image_id)
    assert np.isfinite(pred.score).all()
    assert pred.score.is_monotonic_decreasing
    assert len(queue) == 20
    assert queue.item_id.tolist() == pred.image_id.head(20).tolist()
    first_id = source.iloc[0].image_id
    first_path = INPUT / source.iloc[0].path
    assert pred.set_index("image_id").loc[first_id, "score"] == pytest.approx(
        -laplacian_variance(load_rgb(first_path))
    )
    for name in ("contact_sheet.html", "decision.json", "decision_log.csv", "run_info.json"):
        assert (out / name).exists()


def test_laplacian_baseline_missing_image_fails_loudly(tmp_path):
    from src.baseline_t02 import score_image

    with pytest.raises(FileNotFoundError):
        score_image(tmp_path / "missing.jpg")
