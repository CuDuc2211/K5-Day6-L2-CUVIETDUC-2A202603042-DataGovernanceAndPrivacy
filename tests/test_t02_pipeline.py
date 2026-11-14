"""T02 PoC end-to-end contract, without instructor ground truth."""
import json

import pandas as pd

from src import main as runner


def run_poc(out):
    return runner.main([
        "--track", "t02", "--output", str(out), "--run-name", "poc",
        "--offline", "--seed", "42",
    ])


def test_t02_poc_writes_predictions_review_and_safe_decision(tmp_path):
    assert run_poc(tmp_path) == 0
    pred = pd.read_csv(tmp_path / "ranked_review.csv")
    q = pd.read_csv(tmp_path / "review_queue.csv")
    assert len(pred) == pred.image_id.nunique() == 96
    assert {"image_id", "score", "pred_action", "reason"}.issubset(pred.columns)
    assert pred.score.between(0, 1).all()
    assert len(q) == 20 and q.item_id.tolist() == pred.nlargest(20, "score").image_id.tolist()
    assert q.evidence_path.str.startswith("images/").all()
    assert (tmp_path / "contact_sheet.html").exists()
    assert (tmp_path / "decision_log.csv").exists()
    assert json.loads((tmp_path / "decision.json").read_text(encoding="utf-8"))["status"] == "HOLD"
    info = json.loads((tmp_path / "run_info.json").read_text(encoding="utf-8"))
    assert info["status"] == 0 and info["offline"] is True and info["seed"] == 42


def test_review_edit_updates_action_without_changing_ranking(tmp_path):
    assert run_poc(tmp_path) == 0
    queue = pd.read_csv(tmp_path / "review_queue.csv", dtype=str).fillna("")
    item = queue.loc[0, "item_id"]
    queue.loc[0, ["reviewer", "reviewer_decision", "override_value", "review_note"]] = [
        "AI_assisted_demo", "edit", "KEEP", "manual inspection demo; human sign-off pending",
    ]
    queue.to_csv(tmp_path / "review_queue_reviewed.csv", index=False)
    before = pd.read_csv(tmp_path / "ranked_review.csv").set_index("image_id")
    assert run_poc(tmp_path) == 0
    after = pd.read_csv(tmp_path / "ranked_review.csv").set_index("image_id")
    assert after.loc[item, "pred_action"] == "KEEP"
    assert before.score.equals(after.score)
    assert '"action": "override:edit"' in (tmp_path / "audit_log.jsonl").read_text(encoding="utf-8")
    assert json.loads((tmp_path / "decision.json").read_text(encoding="utf-8"))["reason_code"] == "REVIEW_PENDING"


def test_edit_without_value_is_rejected_instead_of_silently_ignored(tmp_path):
    assert run_poc(tmp_path) == 0
    queue = pd.read_csv(tmp_path / "review_queue.csv", dtype=str).fillna("")
    queue.loc[0, ["reviewer", "reviewer_decision", "override_value"]] = ["demo", "edit", ""]
    queue.to_csv(tmp_path / "review_queue_reviewed.csv", index=False)
    assert run_poc(tmp_path) == 2


def test_skip_cannot_release_batch(tmp_path):
    assert run_poc(tmp_path) == 0
    queue = pd.read_csv(tmp_path / "review_queue.csv", dtype=str).fillna("")
    queue["reviewer"] = "demo"
    queue["reviewer_decision"] = "skip"
    queue.to_csv(tmp_path / "review_queue_reviewed.csv", index=False)
    assert run_poc(tmp_path) == 0
    decision = json.loads((tmp_path / "decision.json").read_text(encoding="utf-8"))
    assert decision["status"] == "HOLD" and decision["reason_code"] == "REVIEW_PENDING"


def test_escalation_is_reported_even_when_other_reviews_pending(tmp_path):
    assert run_poc(tmp_path) == 0
    queue = pd.read_csv(tmp_path / "review_queue.csv", dtype=str).fillna("")
    queue.loc[0, ["reviewer", "reviewer_decision", "review_note"]] = [
        "demo", "escalate", "uncertain image quality",
    ]
    queue.to_csv(tmp_path / "review_queue_reviewed.csv", index=False)
    assert run_poc(tmp_path) == 0
    decision = json.loads((tmp_path / "decision.json").read_text(encoding="utf-8"))
    assert decision["status"] == "HOLD" and decision["reason_code"] == "REVIEW_ESCALATED"
