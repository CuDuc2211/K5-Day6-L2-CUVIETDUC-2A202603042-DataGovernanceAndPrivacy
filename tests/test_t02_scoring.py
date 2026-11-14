"""Behavioral tests for T02 cues, using only public dev images."""
from pathlib import Path

import pandas as pd

from src.common.image_ops import load_rgb
from src.t02_scoring import extract_features, dev_camera_reference, score_features


ROOT = Path("fixtures/t02_raw_qc")


def feature(image_id):
    return extract_features(load_rgb(ROOT / "images" / f"{image_id}.jpg"))


def test_cues_detect_distinct_dev_defects():
    assert feature("img_21_2")["sharpness"] < feature("img_21_0")["sharpness"]
    assert feature("img_20_2")["dark_fraction"] > feature("img_20_0")["dark_fraction"]
    assert feature("img_20_3")["roi_saturated_fraction"] > feature("img_20_0")["roi_saturated_fraction"]
    assert feature("img_11_2")["block_ratio"] > feature("img_11_0")["block_ratio"]


def test_reference_uses_dev_only_not_eval():
    rows = pd.DataFrame({
        "camera_id": ["cam_A", "cam_A", "cam_A"],
        "split": ["dev", "dev", "eval"],
        "sharpness": [100.0, 300.0, 10000.0],
    })
    assert dev_camera_reference(rows)["cam_A"] == 200.0


def test_score_flags_different_defects_but_not_usable_night():
    normal = {"sharpness": 250.0, "dark_fraction": 0.0,
              "roi_saturated_fraction": 0.001, "block_ratio": 1.2}
    normal_score = score_features(normal, 250.0, "day", {})["score"]
    for change, expected_type in (
        ({"sharpness": 3.0}, "blur"),
        ({"dark_fraction": 0.8}, "dark"),
        ({"roi_saturated_fraction": 0.04}, "glare"),
        ({"block_ratio": 3.2}, "compression"),
    ):
        scored = score_features(normal | change, 250.0, "day", {})
        assert scored["score"] > normal_score
        assert scored["pred_defect_type"] == expected_type
    night = normal | {"dark_fraction": 0.63}
    assert score_features(night, 250.0, "night", {})["score"] == normal_score
