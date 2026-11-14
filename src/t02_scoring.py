"""Public-input image cues for T02; no ground-truth access."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .common.image_ops import brightness_stats, laplacian_variance, to_gray


def extract_features(image: np.ndarray) -> dict[str, float]:
    """Sharpness, darkness, local glare and 8-pixel block boundary ratio."""
    gray = to_gray(image)
    height, width = gray.shape
    roi = gray[int(height * 0.55):int(height * 0.95), int(width * 0.20):int(width * 0.80)]
    if roi.size == 0 or height < 10 or width < 10:
        raise ValueError("T02 image is too small for ROI/block quality checks")
    edges_x = np.abs(np.diff(gray, axis=1))
    edges_y = np.abs(np.diff(gray, axis=0))
    boundary_x = np.arange(1, width) % 8 == 0
    boundary_y = np.arange(1, height) % 8 == 0
    boundary = (edges_x[:, boundary_x].mean() + edges_y[boundary_y, :].mean()) / 2
    inside = (edges_x[:, ~boundary_x].mean() + edges_y[~boundary_y, :].mean()) / 2
    stats = brightness_stats(image)
    return {
        "sharpness": float(laplacian_variance(image)),
        "dark_fraction": stats["frac_dark"],
        "roi_saturated_fraction": float((roi > 245).mean()),
        "block_ratio": float(boundary / max(float(inside), 1e-6)),
    }


def dev_camera_reference(rows: pd.DataFrame) -> dict[str, float]:
    """Median sharpness by camera from dev only (never tune on eval images)."""
    dev = rows.loc[rows["split"] == "dev"]
    if dev.empty:
        raise ValueError("T02 needs dev images to calibrate camera sharpness")
    return {str(k): max(float(v), 1e-6) for k, v in dev.groupby("camera_id")["sharpness"].median().items()}


def score_features(features: dict[str, float], camera_ref: float, light: str, params: dict) -> dict:
    """Combine independent suspicion cues; larger means review sooner.

    Values are fixed in configs/lab.yaml; the reference is fit on dev only.
    The strongest cue wins so local glare is not diluted by a sharp background.
    """
    if camera_ref <= 0:
        raise ValueError("camera sharpness reference must be positive")

    def clipped(value: float) -> float:
        return float(np.clip(value, 0.0, 1.0))

    dark_limits = {
        "day": float(params.get("dark_limit_day", 0.30)),
        "dusk": float(params.get("dark_limit_dusk", 0.55)),
        "night": float(params.get("dark_limit_night", 0.82)),
    }
    if light not in dark_limits:
        raise ValueError(f"unexpected light condition: {light}")
    dark_limit = dark_limits[light]
    cues = {
        "blur": clipped((1.0 - features["sharpness"] / camera_ref) / 0.95),
        "dark": clipped((features["dark_fraction"] - dark_limit) / (1.0 - dark_limit)),
        "glare": clipped((features["roi_saturated_fraction"] - float(params.get("glare_start", 0.006))) /
                         float(params.get("glare_span", 0.025))),
        "compression": clipped((features["block_ratio"] - float(params.get("block_start", 1.50))) /
                               float(params.get("block_span", 1.70))),
    }
    strongest = max(cues, key=lambda name: cues[name])
    score = cues[strongest]
    return {
        "score": score,
        "reason": f"{strongest}:{score:.3f}",
        "pred_defect_type": strongest if score >= float(params.get("action_threshold", 0.45)) else "none",
        "pred_action": "RECAPTURE" if score >= float(params.get("action_threshold", 0.45)) else "KEEP",
    }
