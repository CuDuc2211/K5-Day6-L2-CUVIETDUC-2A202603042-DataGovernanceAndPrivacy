# Metric contract (khai báo bắt buộc — chốt ở phút 30, trước khi chạy eval)

> Các metric chuẩn đã được cài trong `src/metrics/tracks.py`. File này là nơi nhóm **cam kết** cách dùng chúng.
> Không đổi testset, threshold hay trọng số sau khi đã thấy kết quả eval.

| Mục | Khai báo của nhóm |
|---|---|
| Track | T02 · Raw QC Triage |
| Primary metric (tên đúng như evaluator in ra) | `Defect Recall@B` |
| Tăng tốt hay giảm tốt? | higher (càng cao càng tốt) |
| Đơn vị đánh giá (image / region / pair / release / batch / case …) | image (ảnh) |
| Công thức + numerator / denominator | Số `image_id` có `is_defect=1` trong top-B theo `score` / tổng số `image_id` có `is_defect=1` thuộc split `eval`. Nếu mẫu số bằng 0: metric không xác định, không điền 0 giả. |
| Cách ghép prediction ↔ GT (IoU? id? tolerance?) | Ghép chính xác theo `image_id`; lọc prediction về các ID trong GT của split `eval`, sau đó xếp `score` giảm dần. Không dùng GT trong pipeline. |
| Candidate pool cố định | `fixtures/t02_raw_qc/images.csv`: 96 ảnh duy nhất; `dev` 56, `eval` 40; các cảnh gốc không giao nhau giữa hai split. Pipeline chấm điểm toàn bộ 96 ảnh, evaluator chỉ chấm 40 ảnh `eval`. |
| Review budget B / K | B=20 ảnh. Queue dùng top 20 của toàn bộ input để review; evaluator dùng top 20 **trong 40 ảnh eval** sau khi lọc split. Cùng B cho baseline và PoC. |
| Seed | 42 cho cả baseline và PoC |
| Threshold policy (chọn trên dev như thế nào) | `Recall@20` xếp hạng bằng score, không dùng ngưỡng để tính metric. Baseline `-Laplacian variance`; PoC: median sharpness theo `camera_id` từ **dev** (không nhìn nhãn eval), độ tối theo `light`, ROI lóa và blockiness 8 px; lấy cue lớn nhất. Tham số đã ghi trong `configs/lab.yaml`: dark limit day/dusk/night = 0.30/0.55/0.82; glare start/span = 0.006/0.025; block start/span = 1.50/1.70; ngưỡng hành động 0.45. Chọn từ kiểm tra ảnh dev và đóng băng trước official eval; không đảm bảo tối ưu ngoài dữ liệu này. |
| Eval split (không dùng để tune) | `eval`, 40 ảnh; không đọc nhãn `gt/` trong pipeline, không chọn tham số theo kết quả eval. |
| Chỉ số lỗi xấu (miss / false alarm / false reject) | Miss = ảnh lỗi `eval` ngoài top 20; báo `Precision@B` = ảnh lỗi trong top 20 / số ảnh thực có trong top 20; false alarm theo `light` = ảnh sạch trong top 20 / tổng ảnh sạch của slice đó. |
| Slices sẽ báo cáo (≥2) | `light=day`, `light=dusk`, `light=night` (evaluator sẵn có); phân tích thêm `camera_id=cam_A/cam_B` thủ công nếu có nhãn và đủ mẫu. Ghi N từng slice, không kết luận quá mức từ slice nhỏ. |
| Cách báo độ bất định khi N nhỏ (Wilson CI / bootstrap) | Khi có nhãn thật, báo numerator/denominator và Wilson 95% CI cho Recall@20; nếu tính CI bằng bootstrap, lấy mẫu theo cảnh gốc để tránh coi bốn ảnh cùng cảnh là độc lập. Không tạo CI khi chưa có GT. |
| Ngày giờ chốt + người chốt | 14/11/2026 15:26 UTC+07; Cù Việt Đức (mã học viên 2A202603042, Git author `CuDuc2211`). Chốt tham số trong `configs/lab.yaml` trước official eval; mã đang ở bản local, commit/push do người học xác nhận sau. |

Nếu baseline = 0 thì ghi rõ "baseline = 0" thay vì phần trăm cải thiện.
