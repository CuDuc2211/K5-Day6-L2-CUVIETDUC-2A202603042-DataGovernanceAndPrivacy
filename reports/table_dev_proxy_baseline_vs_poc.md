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
