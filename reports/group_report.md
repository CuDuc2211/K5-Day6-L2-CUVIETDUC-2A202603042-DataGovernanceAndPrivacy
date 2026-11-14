# Báo cáo T02 — Raw QC Triage (bài làm cá nhân)

> **Trạng thái:** PoC chạy được offline; người học đã tự review 20/20 mục nhưng 6 mục còn `escalate`, nên quyết định vẫn `HOLD`. **Chưa có ground truth chính thức và chưa có người review độc lập**. Mọi con số dưới đây chỉ là đối chiếu trên nhãn thị giác *tạm thời do AI hỗ trợ gán* cho `dev`, không phải điểm `eval`/heldout hay chứng nhận release. Ngày lập: 14/11/2026 (UTC+07).

## 00. Thông tin

| Mục | Giá trị |
|---|---|
| Mã bài | SOLO (mã tạm vì làm cá nhân; thay nếu lớp cấp mã chính thức) |
| Chủ đề | T02 · ảnh mờ/lóa/tối/nén, xếp hàng đợi review B=20 |
| Người chịu trách nhiệm | Cù Việt Đức, mã học viên 2A202603042; Git author cấu hình: CuDuc2211 |
| Repo | https://github.com/CuDuc2211/K5-Day6-L2-CUVIETDUC-2A202603042-DataGovernanceAndPrivacy |
| Demo/final tag | |
| Deadline | |

## 01. Vấn đề, người chịu rủi ro và quyết định

Ảnh đầu vào bị lỗi chất lượng có thể làm người gán nhãn hoặc mô hình thị giác nhầm lẫn; người kiểm duyệt dữ liệu và người sử dụng dữ liệu chịu hậu quả. Đầu vào là `images.csv`, ảnh JPEG và manifest; đầu ra là `ranked_review.csv` (96 điểm nghi lỗi), queue 20 ảnh, trang xem ảnh offline, quyết định và audit log. Pipeline đi qua `load → process → rank → review → decide`.

Quy tắc quyết định **trước official eval**: chưa hoàn tất review 20 ảnh hoặc có ca escalated → `HOLD`; đã review xong mà còn ảnh `RECAPTURE` → `REWORK`; chỉ `GO` nội bộ khi đã review đủ top 20, không còn escalated/recapture. Mỗi quyết định có `reason_code`, `owner`, bằng chứng. Pipeline không kiểm chứng danh tính reviewer hay điểm GT; `GO` nội bộ **không thay thế** phê duyệt độc lập/đánh giá chính thức. Khi chưa có người kiểm độc lập, **không release**. Vai trò owner/mã nhóm là tạm và phải được lớp xác nhận nếu có yêu cầu riêng.

## 02. Data & provenance

| Split | N ảnh | Nguồn | License | Loại |
|---|---:|---|---|---|
| dev | 56 | `fixtures/t02_raw_qc/images.csv` và ảnh tương ứng | CC0 theo README | synthetic; 14 cảnh |
| eval | 40 | cùng fixture; nhãn giữ riêng | CC0 theo README | synthetic; 10 cảnh, không giao cảnh dev |

Các cột input: `image_id,path,camera_id,light,split`. Không có PII thật, không dùng `data/real`. `manifest.csv` gắn SHA-256 vào file; `python -m tools.verify_manifests` kiểm tra 14/14 manifests hợp lệ. Trên Windows đã khôi phục byte LF đúng hash; `.gitattributes` mới giữ LF cho text khi checkout về sau và loại trừ ảnh nhị phân. Không tắt provenance guard. Nhãn GT của giảng viên `fixtures/t02_raw_qc/gt/labels.csv` **không có** ở bản học viên; pipeline không đọc `gt/`.

`reports/dev_visual_labels_t02.csv` là **nhãn proxy AI-assisted**, gán từ việc nhìn montage 56 ảnh `dev`: 28 ảnh nghi lỗi, 28 ảnh sạch. File ghi từng ID, loại lỗi ước lượng, đường dẫn evidence và cảnh báo “human confirmation pending”; không phải gold set độc lập. Không gán nhãn eval để tune. Chia dev/eval theo cảnh gốc (4 ảnh/cảnh).

## 03. Thiết kế và trade-off

- **Baseline** `src/baseline_t02.py`: `score = -laplacian_variance(image)` trên toàn ảnh. Không có ngưỡng; score cao = ảnh ít nét. Có kiểm manifest, queue và quyết định `HOLD / BASELINE_ONLY`.
- **PoC** `src/t02_scoring.py` + `src/pipeline.py`: tính độ nét Laplacian, tỷ lệ pixel tối, tỷ lệ pixel chói `>245` trong vùng giữa-phía dưới ảnh (`x 20–80%`, `y 55–95%`), và tỷ lệ biên lưới 8-pixel so với biên nội bộ để bắt nén. Độ nét so với trung vị **chỉ của dev** theo camera (`cam_A`/`cam_B`), tránh coi mọi ảnh từ camera mềm hơn là mờ. Ngưỡng tối riêng day/dusk/night để không tự loại ảnh đêm. Lấy cue lớn nhất để lóa cục bộ không bị trung bình toàn ảnh che mất. `score` nằm trong [0,1], ngưỡng gợi ý `RECAPTURE` là 0.45; tất cả giá trị ở `configs/lab.yaml`.
- **Trade-off:** các heuristic CPU nhẹ, không tải model/network và dễ giải thích nhưng nhạy với nội dung cảnh, vị trí ROI và ảnh nén không theo lưới 8 px. Calibration camera theo dev không đảm bảo tổng quát cho camera chưa biết; trường hợp đó dùng trung vị dev tổng thể.
- **Data flow:** manifest/hash → `images.csv`/ảnh → feature/scoring → `ranked_review.csv` toàn bộ → queue top 20 + contact sheet → CSV reviewer/override → `audit_log.jsonl` + `decision.json`/`decision_log.csv`. `raw_ranked_review.csv` giữ bản trước override. Review thay `pred_action`, **không thay score** để tránh sửa metric sau khi nhìn ảnh.
- **Nguồn đọc** (URL và ý nghĩa ở mục 11): OpenCV Laplacian, ACDC về điều kiện bất lợi, BRISQUE như hướng blind quality assessment khác; PoC này **không triển khai** BRISQUE và không dùng ảnh ACDC.

## 04. Baseline vs PoC — **chỉ dev proxy, không phải official eval**

Chạy cả hai trên cùng 96 ảnh đầu vào, seed 42, B=20; phép so sánh dưới đây gọi `src.evaluate --gt reports/dev_visual_labels_t02.csv --split dev` nên **lọc 56 ảnh dev trước khi lấy top 20**, không phải queue top 20 toàn bộ. Bảng được sinh bởi `src.compare`, lưu nguyên tại `reports/table_dev_proxy_baseline_vs_poc.md`:

Baseline: `baseline-dev-proxy` (git b0ce8bf, seed 42) · PoC: `poc-dev-proxy` (git b0ce8bf, seed 42)

| Metric (unit) | Slice | Baseline | PoC | Δ abs | Δ rel | Better | N |
|---|---|---|---|---|---|---|---|
| **Defect Recall@B** (GT defects in top-B / GT defects) | all | 0.5714 | 0.7143 | 0.1429 | +25.0% | higher | 56 |
| Precision@B (GT defects in top-B / B) | all | 0.8000 | 1.0000 | 0.2000 | +25.0% | higher | 56 |
| Defect-type accuracy (GT defects) (fraction) | all | n/a | 0.8214 | n/a | n/a | higher | 28 |
| False alarm in top-B (clean images in top-B / clean images) | light=day | 0.1667 | 0.0000 | -0.1667 | -100.0% | lower | 36 |
| False alarm in top-B (clean images in top-B / clean images) | light=dusk | 0.1250 | 0.0000 | -0.1250 | -100.0% | lower | 16 |
| False alarm in top-B (clean images in top-B / clean images) | light=night | 0.0000 | 0.0000 | 0.0000 | baseline=0 | lower | 4 |
| Runtime / 100 items (s) | all | 0.3574 | 0.5715 | | | lower | |

Số đo được tạo bằng script (`reports/metrics_dev_baseline.json`, `reports/metrics_dev_poc.json`), không phải giá trị của giảng viên. Ở dev proxy, PoC cải thiện Recall@20 từ 16/28 lên 20/28, nhưng kết quả thiên lệch vì chính người thiết kế đã nhìn ảnh để chọn heuristic. **Không ngoại suy sang eval**. `run_info.json` và bảng ghi SHA `b0ce8bf` của commit starter tại thời điểm chạy; mã lab mới khi đó vẫn chưa commit, vì vậy SHA này **không phải** phiên bản đầy đủ của PoC.

## 05. Giao thức đánh giá

`reports/metric_contract.md` quy định primary `Defect Recall@B = số ảnh lỗi thật trong top 20 / tổng số ảnh lỗi thật` trên **eval 40 ảnh**, ghép chính xác bằng `image_id`. Secondary: `Precision@B`, false alarm theo light, defect-type accuracy nếu có. Không đổi B/split/weights theo eval; seed 42. Trên dev proxy có 28 positives và 20 budget; vì nhãn này chưa được người độc lập xác nhận, không tuyên bố khoảng tin cậy/Wilson là độ tin cậy của official eval. Khi có GT thật, báo N, numerator/denominator và CI (nếu phù hợp); không giấu kết quả âm/0.

Lệnh official *chỉ giảng viên/overlay GT mới chạy được*:

```powershell
.\.venv\Scripts\python.exe -m src.evaluate --track t02 --pred out/baseline/ranked_review.csv --run-name baseline --out reports/metrics_baseline.json
.\.venv\Scripts\python.exe -m src.evaluate --track t02 --pred out/poc/ranked_review.csv --run-name poc --out reports/metrics_poc.json
.\.venv\Scripts\python.exe -m src.compare reports/metrics_baseline.json reports/metrics_poc.json --out reports/table1_baseline_vs_poc.md
```

Không tạo ba file official trên khi thiếu `gt/`.

## 06. Slices, failure cases và tốc độ

Bảng script cho dev proxy báo `light=day/dusk/night` với N; riêng night chỉ **4 ảnh dev**, không thể kết luận ổn định. Xem `reports/slices_dev_baseline.csv` và `reports/slices_dev_poc.csv`.

1. **Baseline false alarm — `img_09_0`**, `cam_B`, day: ảnh tham chiếu nhìn còn dùng được nhưng Laplacian toàn ảnh thấp do quang học mềm, lọt top 20 dev của baseline. PoC chuẩn hóa theo camera nên không xem chỉ số thô này là lỗi. Evidence: `fixtures/t02_raw_qc/images/img_09_0.jpg` và top-20 baseline.
2. **Baseline miss — `img_20_3`**, day: vùng sáng chói nhỏ gần xe, phần lớn ảnh còn nét nên baseline không đưa vào top 20 dev. PoC thấy tỷ lệ pixel bão hòa trong ROI và đưa ảnh vào queue; người học đã chọn `approve` cho đề xuất `RECAPTURE`. Evidence: `fixtures/t02_raw_qc/images/img_20_3.jpg`.
3. **PoC còn miss — `img_22_3`**, dusk: vùng lóa lệch khỏi ROI giữa-phía dưới, không lọt top 20 dev của PoC. Cần thử nhiều ROI hoặc detector vùng sáng có kiểm soát false positive, không sửa sau khi xem official eval. Evidence: `fixtures/t02_raw_qc/images/img_22_3.jpg`.

Runtime máy Windows 11 / Intel64 Family 6 Model 140 / Python 3.13.17, số giây/100 ảnh ở bảng script. Số runtime đơn lẻ không phải benchmark ổn định; đo nhiều lần nếu cần.

## 07. Review, override, audit và risk gate

`out/poc/review_queue.csv` là top 20; `out/poc/contact_sheet.html` mở offline và export `review_queue_reviewed.csv`. **Cù Việt Đức đã tự chọn quyết định cho 20/20 ảnh**: 12 `approve` giữ `RECAPTURE`, 2 `edit → KEEP` (`img_10_2`, `img_22_2`) và 6 `escalate` chưa chốt. Xác nhận nhận định rằng hai ảnh KEEP còn đủ dùng ở mức tổng quan, còn sáu ảnh mờ không nặng toàn cục nhưng chi tiết vẫn không rõ.review_note` dựa trên các nhận định đó và các quyết định đã xuất; không coi đây là review độc lập. Evidence hiện hành: `reports/review_queue_human.csv`, `reports/audit_log_t02_human_review.jsonl` (23 sự kiện của lần chạy này), `reports/decision_log_t02_human.csv`; các file `*_demo`/`reports/review_queue.csv` là bản minh họa trước đó. `out/poc/decision.json` hiện `HOLD / REVIEW_ESCALATED`, owner `Cù Việt Đức (2A202603042)`, vì 6 ca chưa được giải quyết. Test tự động chứng minh `edit` đổi `pred_action` nhưng không đổi `score`, `edit` thiếu giá trị bị từ chối, và `skip` không thể release. **Chưa có phê duyệt độc lập hay quyết định release**; cần giải quyết các ca escalate theo rủi ro thực tế, không ép `GO`.

## 08. Reproduce & tests (PowerShell tại gốc repo)

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m tools.preflight
.\.venv\Scripts\python.exe -m tools.verify_manifests
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m src.main --config configs/lab.yaml --track t02 --pipeline src.baseline_t02 --output out/baseline --run-name baseline --offline --seed 42
.\.venv\Scripts\python.exe -m src.main --config configs/lab.yaml --track t02 --output out/poc --run-name poc --offline --seed 42
.\.venv\Scripts\python.exe -m src.evaluate --track t02 --gt reports/dev_visual_labels_t02.csv --split dev --pred out/baseline/ranked_review.csv --run-name baseline-dev-proxy --out reports/metrics_dev_baseline.json
.\.venv\Scripts\python.exe -m src.evaluate --track t02 --gt reports/dev_visual_labels_t02.csv --split dev --pred out/poc/ranked_review.csv --run-name poc-dev-proxy --out reports/metrics_dev_poc.json
.\.venv\Scripts\python.exe -m src.compare reports/metrics_dev_baseline.json reports/metrics_dev_poc.json --out reports/table_dev_proxy_baseline_vs_poc.md
```

`pytest` chạy không lỗi; một số test có marker `requires_gt` được skip hợp lệ vì thiếu GT. `preflight` 0 FAIL, 2 WARN tùy chọn (real data/model không cần T02). Chạy offline/seed 42; thiếu ảnh, manifest sai, reviewer thiếu tên/giá trị hoặc GT access sẽ thất bại rõ. `out/` gitignored; repo báo cáo giữ bản CSV/JSON dev-proxy và queue demo. Mở `demo/t02_showcase.html` để trình bày 5 slide offline (phím ←/→, có thể in PDF).

## 09. Giới hạn và đạo đức

Không được suy luận “đạt GDPR/luật Việt Nam” từ pipeline QC này. Fixture là synthetic; trước khi dùng ảnh thật phải kiểm nguồn/license, quyền riêng tư, retention, quyền truy cập và nhờ DPO/legal/domain owner xác nhận. Nhãn proxy AI-assisted có thể sai; bốn ảnh cùng cảnh không độc lập; budget B=20 trên 40 ảnh eval có thể làm sai lệch nhận định. ROI lóa cố định, block 8px không tổng quát, ngưỡng/camera mới có thể drift. Nếu quy mô ×10, phải đánh giá lại thời gian, sampling review và slices. Gate trong pipeline xử lý review/override, **không kiểm GT hay danh tính reviewer**; do đó không tự xem trạng thái `GO` nội bộ là quyền release khi còn thiếu đánh giá và phê duyệt ngoài pipeline.

## 10. Đóng góp & trạng thái nộp

Bài làm cá nhân: Cù Việt Đức (2A202603042); `CuDuc2211` là Git identity hiện được cấu hình; mã sửa ở `src/pipeline.py`, `src/t02_scoring.py`, `src/baseline_t02.py`, `tests/test_t02_*.py`, config và báo cáo. `reports/team_contributions.csv` ghi một người; lịch sử repo sẵn có chứa tác giả khác từ upstream nên **không gán commit cũ cho người học**. Commit/tag cuối và URL push chỉ xác nhận sau khi người học xem lại; không giả tạo bằng chứng đóng góp. Dùng `git shortlog -sne --all` và `git log --oneline` để xác minh commit thực tế.

## 11. References (truy cập 14/11/2026)

| Nguồn gốc | URL | Vì sao liên quan |
|---|---|---|
| OpenCV, image gradients/Laplacian tutorial (source chính thức) | https://github.com/opencv/opencv/blob/4.x/doc/py_tutorials/py_imgproc/py_gradients/py_gradients.markdown | Laplacian nhạy với biên/chi tiết; dùng làm baseline độ nét, nhưng không đại diện cho mọi dạng lỗi. |
| Sakaridis, Dai, Van Gool, ACDC (ICCV 2021, bản tác giả) | https://arxiv.org/abs/2104.13395 | Ảnh điều kiện khó, đặc biệt nighttime, cho thấy cần đánh giá theo domain; không dùng dataset này để tune. |
| Mittal et al., No-Reference Image Quality Assessment in the Spatial Domain (bản tác giả) | https://live.ece.utexas.edu/publications/2012/TIP%20BRISQUE.pdf | Hướng IQA blind đối chứng khái niệm; PoC chọn cues nhẹ, có giải thích, không triển khai BRISQUE. |

## Checklist thật sự

- [x] Run offline một lệnh, manifest hợp lệ, baseline/PoC, queue/contact sheet/audit/decision, test tự động.
- [x] So sánh dev proxy cùng B/split/seed, ghi rõ N và giới hạn.
- [x] Người học tự review đủ top 20, có note (AI hỗ trợ diễn đạt), giữ 6 ca `escalate` ở trạng thái HOLD.
- [ ] Giải quyết 6 ca `escalate`/phê duyệt độc lập nếu cần release; xác nhận nhãn dev proxy nếu dùng làm gold set nội bộ.
- [ ] Chạy official eval với overlay GT của giảng viên, tạo `metrics_baseline.json`/`metrics_poc.json`/bảng official.
- [ ] Xác nhận mã nhóm chính thức (nếu có)/deadline, commit và tag theo yêu cầu lớp, sau đó push khi người học đồng ý.
