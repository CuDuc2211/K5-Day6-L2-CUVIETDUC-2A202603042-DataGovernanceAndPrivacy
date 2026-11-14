"""T02 baseline: rank each image by whole-image Laplacian sharpness.

Lower sharpness means a higher suspicion score. This deliberately ignores
illumination and local glare; the PoC will address those limitations.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .common.contact_sheet import render_contact_sheet
from .common.context import RunContext
from .common.decision import Decision, write_decision
from .common.image_ops import laplacian_variance, load_rgb
from .common.manifest import verify_manifest
from .common.review import make_review_queue, write_review_queue


def score_image(path: str | Path) -> float:
    """Higher score = more suspicious (less sharp). Fail on missing input."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"T02 image not found: {path}")
    return -laplacian_variance(load_rgb(path))


def run(ctx: RunContext) -> None:
    if ctx.track != "t02":
        raise ValueError("src.baseline_t02 only supports track t02")
    manifest = ctx.input_dir / "manifest.csv"
    problems = verify_manifest(manifest)
    if problems:
        raise ValueError(f"T02 input provenance failed: {problems[:3]}")

    images = pd.read_csv(ctx.input_dir / "images.csv")
    required = {"image_id", "path", "camera_id", "light", "split"}
    if missing := required.difference(images.columns):
        raise ValueError(f"images.csv missing columns: {sorted(missing)}")
    if images.image_id.isna().any() or images.image_id.duplicated().any():
        raise ValueError("images.csv must have unique, nonempty image_id values")
    images["score"] = [score_image(ctx.input_dir / p) for p in images["path"]]
    images["reason"] = "low_whole_image_sharpness"
    ctx.stats["n_items"] = len(images)

    budget = int(ctx.param("budget", 20))
    queue = make_review_queue(
        images, "image_id", "score", budget,
        reason_col="reason", evidence_col="path",
    )
    write_review_queue(queue, ctx.out("review_queue.csv"))
    render_contact_sheet(
        queue, ctx.out("contact_sheet.html"), image_root=ctx.input_dir,
        title="T02 baseline - low sharpness review",
    )
    ranked = images.sort_values("score", ascending=False, kind="mergesort")
    pred_path = ctx.out("ranked_review.csv")
    ranked[["image_id", "score"]].to_csv(pred_path, index=False)
    if ctx.audit is not None:
        ctx.audit.log(actor="baseline", action="review_queue_created", item_id="t02", after={"budget": budget})
    write_decision(
        Decision(
            status="HOLD", reason_code="BASELINE_ONLY",
            reason="Single whole-image sharpness signal is not enough to release data.",
            owner=ctx.config["owner"], scope="t02", evidence=[str(pred_path)],
        ),
        ctx.out("decision.json"), ctx.out("decision_log.csv"),
    )
