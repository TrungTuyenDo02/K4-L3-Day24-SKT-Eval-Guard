# Blueprint CI/CD cho RAG và guardrails

Nhóm: SKT

Người phụ trách: Đỗ Trung Tuyến — 2A202602427

Đây là **đề xuất CI/CD**, không phải workflow đã được triển khai/chạy.
Nguồn kết quả: artifacts/ragas_50q.json, judge_results.json, guard_results.json.
Run timestamp: guard_results.json `2026-10-12T04:09:07Z`; guard models: `["gpt-4o-mini"]` (NeMo `main` model, self check input/output).
Models generation/evaluator/judge từ A/B: Phase A/B **chưa chạy** tại commit này (chưa có `artifacts/answers_50q.json`); cấu hình dự kiến: generation `gpt-4o-mini` (`config.GENERATION_MODEL`), evaluator m4 `gpt-4o-mini` + `text-embedding-3-small`, judge `gpt-4o-mini` (`config.JUDGE_MODEL`). Cập nhật theo metadata thật sau khi chạy.

## Kiến trúc và failure action

Input → Presidio → NeMo input → RAG → NeMo output → response.
Request thực dừng sớm khi bị chặn; khác phép đo input layers chạy đủ hai tầng.

Data flow đề xuất cho một request:

1. **Presidio (local, ~13 ms P50)** quét CCCD/CMND (12/9 số), SĐT VN `0[3-9]xxxxxxxx`, email, thẻ/IBAN.
   Chỉ giữ các entity dạng pattern; NER PERSON/LOCATION của model spaCy tiếng Anh bị bỏ vì gắn nhầm trên câu
   tiếng Việt. Có PII → **block**, trả câu hướng dẫn "hãy hỏi lại không kèm thông tin cá nhân"; log chỉ lưu bản
   `anonymized` (`<VN_CCCD>`, `<VN_PHONE>`...) và entity type/vị trí, không lưu chuỗi gốc.
2. **NeMo input rail** (`self check input`, gpt-4o-mini): chặn off-topic, jailbreak/role-play, mạo danh quyền,
   trích system prompt, đòi dữ liệu cá nhân/lương cá nhân hoặc giá trị bí mật. Quyết định đọc từ
   `result.log.activated_rails[].stop`, không suy từ chữ "xin lỗi". Block → trả câu từ chối trong `rails.co`.
3. **RAG** (hybrid BM25 + BGE-M3/Qdrant → bge-reranker-v2-m3 top 3 → gpt-4o-mini).
4. **NeMo output rail** (`self check output`): answer chứa định danh cá nhân, lương cá nhân, mật khẩu/credential
   → thay bằng câu từ chối (`final_answer` ≠ answer gốc, `flagged_reason="nemo_output_rail: self check output"`);
   answer sạch giữ nguyên từng ký tự. Lớp này không thay RAGAS faithfulness.

Failure action khi chính guard lỗi (timeout/API lỗi của LLM self-check): **fail-closed** cho output rail (không trả
answer chưa kiểm tra), fail-closed cho input rail với câu "hệ thống bận, thử lại"; Presidio là local nên luôn chạy.
Secrets (`OPENAI_API_KEY`) chỉ nằm trong `.env`/secret store của CI, không vào log hay artifacts. Log request chỉ
giữ input đã anonymize, rail kích hoạt, quyết định và latency từng tầng.

## Phạm vi và số đo latency

Bắt buộc Task 12: **input_layers_sequential**, Presidio + NeMo input, không
short-circuit. Engines tạo trước đo; có hai warm-up thật không tính vào mẫu.
Percentile nội suy tuyến tính từ raw samples; tổng từ tổng từng sample.

Số mẫu timed: 20; warm-up: 2;
phương pháp: linear (vị trí `(n - 1) * q` trên raw samples, 8 câu clean lặp vòng).

| Layer / scope | P50 ms | P95 ms | P99 ms | Tình trạng |
|---|---|---|---|---|
| Presidio | 13.11 | 21.72 | 25.06 | Đã đo Task 12 (local, CPU) |
| NeMo input | 685.92 | 781.25 | 828.68 | Đã đo Task 12 (1 lời gọi gpt-4o-mini/mẫu) |
| Input guard sequential | 696.47 | 795.57 | 841.79 | Đã đo Task 12; vượt target 500ms |
| RAG | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| NeMo output | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| Full guard / short-circuit request | chưa đo | chưa đo | chưa đo | Không suy từ input_guard_ms |

Input-layer budget target: 500ms; kết quả thực tế/budget_ok: P95 = 795.57 ms, `latency_budget_ok = false`.

Bottleneck là NeMo input rail: ~98% thời gian (P50 686/696 ms), mỗi mẫu là một round-trip HTTPS tới
gpt-4o-mini (min 617 ms, max 841 ms trong 20 mẫu); Presidio chỉ ~13–22 ms. Vì vậy tối ưu Presidio không giúp đạt
budget. Hướng xử lý có thể kiểm chứng: (1) thay self-check LLM bằng classifier local nhỏ (hoặc embedding +
logistic regression) cho off-topic/jailbreak và chỉ gọi LLM khi classifier không chắc; (2) chạy NeMo input song song
với retrieval rồi hủy RAG nếu bị chặn (giảm latency cảm nhận, không giảm chi phí); (3) cache quyết định theo hash input
đã chuẩn hóa. Mỗi hướng đo lại bằng đúng Task 12 (20 mẫu, 2 warm-up) và chạy lại suite 28 inputs để chắc không tăng
false positive.

Kế hoạch đo phần "chưa đo": thêm timestamps `perf_counter` quanh search/rerank/generation và output rail trong
một runner riêng, 2 warm-up + ≥50 request thật, ghi raw samples; full guard đo theo request thực (có short-circuit)
tách riêng với input_layers_sequential.

## CI gates đề xuất

- RAGAS faithfulness ≥0.75, avg_score ≥0.65 trên 50 câu.
- Attacks ≥18/20 cho CI đề xuất; clean 8/8 allowed; output cases đúng.
- Full guard P95 <500ms chỉ áp dụng sau khi thực sự đo full guard.

Mốc bắt buộc lab vẫn attacks ≥15/20; bonus ≥18/20 kèm clean controls đạt.

Đề xuất job (chưa triển khai; repo hiện **không** có workflow CI):

```yaml
# .github/workflows/eval-guard.yml (đề xuất)
on: [pull_request]   # chỉ khi đổi src/, guardrails/, data/, fixtures/
jobs:
  offline:  # không tốn API
    steps: [python -m pytest tests/ -q]
  live:     # cần secret OPENAI_API_KEY, chạy nightly hoặc khi đổi guardrails/ hoặc prompt
    steps:
      - python scripts/setup_answers.py --live
      - python scripts/run_experiments.py --phase all --live --latency-samples 20
      - python scripts/check_lab.py          # trả exit 1 nếu artifact sai hợp đồng
      - python scripts/ci_gates.py           # script đề xuất, CHƯA tồn tại
```

`check_lab.py` hiện đã trả nonzero khi attacks <15/20, có clean bị chặn, output case sai hoặc số liệu không khớp.
Các ngưỡng chất lượng cao hơn (faithfulness ≥0.75, avg ≥0.65, attacks ≥18/20) cần một script `ci_gates.py` đọc
JSON rồi `sys.exit(1)`; biến kiểu `MIN_FAITHFULNESS` chỉ là đề xuất và không tự tạo gate khi chưa có script này.
Với kết quả hiện tại: chỉ có số Phase C — attacks 20/20 (≥18 đạt), clean 8/8, output 4/4 đều qua gate đề xuất; input guard P95 795.57 ms (gate full guard chưa áp dụng vì chưa đo full guard). Gate RAGAS chưa đánh giá được vì Phase A chưa chạy.

## Monitoring và cải tiến

Đề xuất theo dõi trong production (lấy mẫu log đã anonymize):

| Metric | Cách lấy | Ngưỡng cảnh báo |
|---|---|---|
| Tỷ lệ block input theo tầng | đếm `blocked_by` / tổng request mỗi giờ | lệch >2× so với baseline 7 ngày |
| False positive | mẫu 50 request bị block/tuần, người review | >5% câu bị block là câu hợp lệ |
| Latency input guard / full request | raw `perf_counter` mỗi tầng | P95 input guard >500 ms trong 15 phút |
| RAGAS trên mẫu traffic | 50 câu/tuần + reference từ HR | faithfulness <0.75 hoặc giảm >0.05 |
| Drift chính sách | khi `data/` có bản policy mới | chạy lại 50q + kiểm tra câu version conflict |

Privacy: không lưu PII gốc, chỉ bản anonymized; key ở secret store. Người xử lý: owner RAG xử lý cảnh báo RAGAS,
owner guard xử lý false positive/latency; false positive được thêm vào clean set (không xóa attack cũ).

RAGAS mean/worst distribution: chưa có — Phase A chưa chạy (chưa sinh được 50 answers trên máy trưởng nhóm do thiếu RAM; thành viên khác sẽ chạy).
Cohen’s κ: chưa có — Phase B chưa chạy.
Attacks passed: 20/20; clean false_positive_rate: 0.0 (8/8 allowed); output cases 4/4 đúng (201/202 giữ nguyên, 203/204 bị thay).

Lịch sử thực nghiệm Phase C: lần chạy đầu với prompt self-check gốc đạt attacks 18/20 nhưng **chặn nhầm 1/8 câu sạch**
(id 107, quy định độ dài mật khẩu, false_positive_rate 0.125) và lọt 2 off-topic (id 11 bài thơ, id 15 phim Marvel);
input guard P95 lần đó 1027.9 ms. Nguyên nhân: prompt dùng từ "credentials" mơ hồ (không tách *giá trị* mật khẩu với
*quy định* mật khẩu) và không liệt kê rõ phạm vi. Prompt được viết lại theo quy tắc tổng quát (phạm vi + 5 nhóm cần chặn
+ ví dụ được phép), fixtures giữ nguyên, rồi chạy lại toàn bộ batch C; artifact hiện tại là lần chạy thứ hai.
Giới hạn: bộ 20 attacks/8 clean/4 outputs rất nhỏ và prompt đã được chỉnh sau khi xem lần chạy đầu, nên 20/20 và 8/8
có nguy cơ overfit; cần một bộ held-out mới để xác nhận.

Cải tiến đề xuất (kiểm tra được):

1. **Giảm latency input guard:** thay self-check LLM bằng classifier local cho off-topic/jailbreak, chỉ gọi LLM khi không chắc;
   kiểm tra bằng Task 12 (mục tiêu P95 input guard <500 ms) và suite 28 inputs (giữ ≥18/20 attacks, 8/8 clean).
2. **Chống overfit prompt guard:** viết thêm bộ held-out (≥20 attacks diễn đạt khác, ≥20 câu sạch mới, gồm câu có số/email công ty
   hợp lệ) mà không chỉnh prompt theo nó; báo cáo pass rate và false-positive rate trên bộ này.
3. **Output rail có lớp Presidio:** chạy `pii_scan` trên answer trước NeMo output để redact CCCD/SĐT tất định (không phụ thuộc LLM),
   whitelist email helpdesk công ty; kiểm tra bằng 4 output cases + case mới chứa SĐT cá nhân.
4. **Đo phần "chưa đo":** thêm timestamps cho RAG và output rail, ≥50 request thật sau 2 warm-up, báo P50/P95/P99 theo request có
   short-circuit; chỉ khi đó mới bật gate full guard P95 <500 ms.
5. **Phase A/B:** sau khi có `ragas_50q.json`/`judge_results.json`, bổ sung cải tiến RAG gắn với bottom 10 và κ thật.
