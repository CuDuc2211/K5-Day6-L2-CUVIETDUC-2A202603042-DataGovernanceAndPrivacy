# reports/

| File | Ai tạo | Cách tạo |
|---|---|---|
| `group_report.md` | nhóm | điền template |
| `metric_contract.md` | nhóm | điền ở phút 30 |
| `metrics_baseline.json` | **script** | `python -m src.evaluate --track tXX --pred out/baseline/<file> --run-name baseline --out reports/metrics_baseline.json` |
| `metrics_poc.json` | **script** | `python -m src.evaluate --track tXX --pred out/poc/<file> --run-name poc --out reports/metrics_poc.json` |
| `table1_baseline_vs_poc.md` | **script** | `python -m src.compare reports/metrics_baseline.json reports/metrics_poc.json --out reports/table1_baseline_vs_poc.md` |
| `review_queue.csv` | pipeline + AI demo | bản queue demo trước self-review; không phải bằng chứng human review hiện hành |
| `decision_log.csv` | pipeline | quyết định demo trước self-review |
| `review_queue_human.csv` | Cù Việt Đức + AI hỗ trợ diễn đạt | 20 quyết định do người học chọn, notes được viết lại theo xác nhận của người học; 6 mục vẫn `escalate` |
| `audit_log_t02_human_review.jsonl` | pipeline | 23 sự kiện review/override/decision phát sinh đúng lần chạy human review |
| `decision_log_t02_human.csv` | pipeline | lịch sử quyết định đến sau human review; dòng cuối `HOLD / REVIEW_ESCALATED` |
| `team_contributions.csv` | nhóm/cá nhân | khớp với `git shortlog -sne --all`; repo starter có tác giả upstream |
| `metrics_dev_baseline.json`, `metrics_dev_poc.json` | **script** | `src.evaluate --gt reports/dev_visual_labels_t02.csv --split dev`; chỉ nhãn proxy AI-assisted, không phải official GT |
| `table_dev_proxy_baseline_vs_poc.md` | **script** | `src.compare` trên hai JSON dev-proxy ở trên |
| `dev_visual_labels_t02.csv` | AI-assisted visual review | nhãn dev tạm; cần người học xác nhận trước khi dùng làm gold set nội bộ |
| `audit_log_t02_demo.jsonl` | pipeline | trích 3 sự kiện review/decision cuối; AI-assisted, không phải human sign-off |

Các file metrics/table **không được sửa tay** — giảng viên sẽ chạy lại lệnh để đối chiếu.
