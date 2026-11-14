"""YOUR PoC PIPELINE — this is the file your group owns.

Lab contract = 5 automated steps, run by `python -m src.main ...`:
    01 load      input + provenance check (manifest.csv)
    02 process   your algorithm / model (the research part)
    03 rank      prioritise for a fixed review budget B
    04 review    human-in-the-loop: queue -> reviewer decisions -> overrides + audit log
    05 decide    GO / HOLD / REWORK (or track equivalent) with reason_code + owner, write outputs

Required output: out/<pred_file> with the columns listed for your track in
docs/tracks/TXX.md (also in src/metrics/tracks.py::TRACKS). Then evaluate with
    python -m src.evaluate --track tXX --pred out/<pred_file>

Rules: never read fixtures/*/gt/ here (the GT guard will stop you); seed everything via ctx.rng;
no network calls; fail loudly on missing models instead of downloading.
See src/examples/random_baseline.py for a minimal end-to-end wiring example.
"""
from __future__ import annotations

import pandas as pd
import numpy as np

from .common.context import RunContext
from .common.contact_sheet import render_contact_sheet
from .common.decision import Decision, write_decision
from .common.image_ops import load_rgb
from .common.manifest import verify_manifest
from .common.review import apply_overrides, load_review_decisions, make_review_queue, write_review_queue
from .metrics.tracks import get_track
from .t02_scoring import dev_camera_reference, extract_features, score_features


# ---------------------------------------------------------------- 01 load
def load(ctx: RunContext) -> dict:
    manifest = ctx.input_dir / "manifest.csv"
    problems = verify_manifest(manifest) if manifest.exists() else [{"problem": "no_manifest"}]
    if problems:
        ctx.audit.log(actor="pipeline", action="provenance_problems", item_id=str(manifest), after=problems[:20])
        if ctx.config.get("strict_provenance", True):
            raise ValueError(f"provenance check failed ({len(problems)} problems), first: {problems[:3]}")
    if ctx.track != "t02":
        raise ValueError(f"This PoC implements t02 only, not {ctx.track}")
    images = pd.read_csv(ctx.input_dir / "images.csv")
    required = {"image_id", "path", "camera_id", "light", "split"}
    if missing := required.difference(images.columns):
        raise ValueError(f"images.csv missing columns: {sorted(missing)}")
    if images.image_id.isna().any() or images.image_id.duplicated().any():
        raise ValueError("images.csv must have nonempty unique image_id values")
    data = {"manifest": pd.read_csv(manifest), "images": images}
    return data


# ---------------------------------------------------------------- 02 process
def process(ctx: RunContext, data: dict) -> pd.DataFrame:
    images = data["images"].copy()
    rows = []
    for path in images["path"]:
        image_path = (ctx.input_dir / path).resolve()
        if not image_path.is_relative_to(ctx.input_dir.resolve()) or "gt" in image_path.parts:
            raise ValueError(f"image path leaves the input folder: {path}")
        rows.append(extract_features(load_rgb(image_path)))
    images = pd.concat([images.reset_index(drop=True), pd.DataFrame(rows)], axis=1)
    reference = dev_camera_reference(images)
    fallback = float(images.loc[images.split == "dev", "sharpness"].median())
    scored = [score_features(r._asdict(), reference.get(r.camera_id, fallback), r.light,
                             ctx.config.get("params") or {}) for r in images.itertuples(index=False)]
    images = pd.concat([images, pd.DataFrame(scored)], axis=1)
    if not np.isfinite(images["score"].to_numpy(dtype=float)).all():
        raise ValueError("non-finite T02 suspicion score")
    ctx.stats["dev_camera_sharpness_reference"] = reference
    return images


# ---------------------------------------------------------------- 03 rank
def rank(ctx: RunContext, scored: pd.DataFrame) -> pd.DataFrame:
    """Default: top-B by `score`. Adapt id/score/reason columns to your track."""
    budget = int(ctx.param("budget", 20))
    if "score" not in scored.columns:
        raise ValueError("rank(): process() output needs a numeric `score` column (higher = review first), "
                         "or adapt rank() to your track")
    q = make_review_queue(scored, id_col="image_id", score_col="score", budget=budget,
                          reason_col="reason", action_col="pred_action",
                          slice_col="light", evidence_col="path")
    write_review_queue(q, ctx.out("review_queue.csv"))
    render_contact_sheet(q, ctx.out("contact_sheet.html"), image_root=ctx.input_dir,
                         title="T02 · ảnh nghi lỗi cần xem")
    return q


# ---------------------------------------------------------------- 04 review
def review(ctx: RunContext, scored: pd.DataFrame, queue: pd.DataFrame) -> pd.DataFrame:
    """Apply only explicit human action overrides; never alter ranking scores."""
    ctx.stats["review_queue_items"] = len(queue)
    ctx.stats["n_reviewed"] = 0
    ctx.stats["n_escalated"] = 0
    reviewed_path = ctx.output_dir / "review_queue_reviewed.csv"
    if reviewed_path.exists():
        reviewed = load_review_decisions(reviewed_path)
        if reviewed.item_id.duplicated().any() or not set(reviewed.item_id).issubset(set(queue.item_id)):
            raise ValueError("reviewed item IDs must be unique and belong to the current top-B queue")
        if ((reviewed.reviewer_decision == "edit") & reviewed.override_value.eq("")).any():
            raise ValueError("reviewer edit requires a nonempty override_value")
        changed = reviewed[reviewed.reviewer_decision.isin(["edit", "reject"]) &
                           reviewed.override_value.ne("")]
        if not set(changed.override_value).issubset({"KEEP", "RECAPTURE"}):
            raise ValueError("override_value must be KEEP or RECAPTURE")
        completed = reviewed[~reviewed.reviewer_decision.eq("skip") &
                             ~(reviewed.reviewer_decision.eq("reject") & reviewed.override_value.eq(""))]
        ctx.stats["n_reviewed"] = len(completed)
        ctx.stats["n_escalated"] = int((reviewed.reviewer_decision == "escalate").sum())
        if ctx.audit is not None:
            for row in reviewed.itertuples(index=False):
                ctx.audit.log(actor=row.reviewer, action=f"review:{row.reviewer_decision}",
                              item_id=row.item_id, after=row.override_value or None,
                              reason=row.review_note)
        return apply_overrides(scored, reviewed, id_col="image_id", value_col="pred_action", audit=ctx.audit)
    return scored


# ---------------------------------------------------------------- 05 decide
def decide(ctx: RunContext, final: pd.DataFrame) -> Decision:
    if ctx.stats.get("n_escalated", 0):
        status, code, reason = "HOLD", "REVIEW_ESCALATED", "A reviewer escalated a case."
    elif ctx.stats.get("n_reviewed", 0) < ctx.stats.get("review_queue_items", 0):
        status, code, reason = "HOLD", "REVIEW_PENDING", "Top-B review is incomplete."
    elif (final.pred_action == "RECAPTURE").any():
        status, code, reason = "REWORK", "RECAPTURE_REQUIRED", "A flagged image needs recapture."
    else:
        status, code, reason = "GO", "REVIEW_APPROVED", "All top-B items were reviewed; no recapture remains."
    return Decision(status=status, reason_code=code, reason=reason,
                    owner=ctx.config["owner"], scope=ctx.track,
                    evidence=[str(ctx.out("review_queue.csv")), str(ctx.out("ranked_review.csv"))],
                    metrics={"n_reviewed": ctx.stats["n_reviewed"], "n_items": len(final)})


def run(ctx: RunContext) -> None:
    spec = get_track(ctx.track)
    data = load(ctx)
    scored = process(ctx, data)
    ctx.stats["n_items"] = len(scored)
    queue = rank(ctx, scored)
    scored.sort_values("score", ascending=False, kind="mergesort").to_csv(ctx.out("raw_ranked_review.csv"), index=False)
    final = review(ctx, scored, queue)
    final = final.sort_values("score", ascending=False, kind="mergesort")
    final[spec.pred_columns + [c for c in final.columns if c not in spec.pred_columns]].to_csv(ctx.out(spec.pred_file), index=False)
    decision = decide(ctx, final)
    write_decision(decision, ctx.out("decision.json"), ctx.out("decision_log.csv"))
    if ctx.audit is not None:
        ctx.audit.log(actor=decision.owner, action="release_decision", item_id=ctx.track,
                      after=decision.status, reason=decision.reason_code)
