# Nhóm thực hiện K4 Track 3A

Tên nhóm: SKT

Repo chung: https://github.com/TrungTuyenDo02/K4-Track-3A-Day24-DoTrungTuyen-2A202602427-EvalGuard

Trưởng nhóm/người nộp: Đỗ Trung Tuyến — 2A202602427

Ngày lab/deadline áp dụng: 12/10/2026, 23:59 — Asia/Ho_Chi_Minh (UTC+07:00)

Commit dùng để chấm: commit cuối trên nhánh `main` tại thời điểm nộp (SHA gửi kèm link qua vlearn; lấy bằng `git rev-parse HEAD`).

Mỗi thành viên tự thêm một row vào bảng dưới và một mục INDIVIDUAL (tiêu đề: họ tên không dấu, gạch nối, MSSV),
ghi đúng phần mình đã làm; mỗi người cần có commit trong repo chung.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Đỗ Trung Tuyến | 2A202602427 | Trưởng nhóm. Chuẩn bị môi trường, tích hợp m1–m5; code Tasks 1–12 trong `src/phase_a_ragas.py`, `src/phase_b_judge.py`, `src/phase_c_guard.py`; cấu hình `guardrails/config.yml`; chạy batch Phase C; viết blueprint (kiến trúc guard, latency, CI/monitoring); phần phân tích không cần số liệu của `failure_clusters.md` (bẫy adversarial) và `bias_report.md` (nguồn cặp A/B, 10 model_answer, độ nhạy κ) | Commits trên `main`; `artifacts/guard_results.json`; `doc/reports/*.md` |

Người tích hợp/nộp link: Đỗ Trung Tuyến — đã chạy batch Phase C
(`scripts/run_experiments.py --phase c --live --latency-samples 20`), sẽ nộp link bản cuối. Sinh 50 answers, chạy Phase A/B,
điền các mục "CHỜ KẾT QUẢ" trong `failure_clusters.md`/`bias_report.md` và chạy `scripts/check_lab.py`: giao cho thành viên có máy đủ RAM
(máy trưởng nhóm không chạy được setup, xem mục dưới); người thực hiện tự ghi vào bảng và INDIVIDUAL của mình.

## Môi trường và chuẩn bị trước lớp

OS/Python/compiler: Windows 11 Home 10.0.26300, CPU Intel i5-8250U, RAM 12 GB, Python 3.11.9; `annoy==1.17.3` đã cài thành công trong virtualenv.
Virtualenv/dependencies/imports: dùng chung virtualenv Python 3.11 đã tạo cho repo Track 3B cùng đề (cùng requirements/constraints),
gọi trực tiếp `.venv/Scripts/python.exe`; cài bằng `requirements/requirements.txt -c requirements/constraints-core.txt`
(ragas 0.1.22, langchain 0.2.17, nemoguardrails 0.10.0, openai 1.109.1, presidio 2.2.364, spaCy 3.8 + `en_core_web_lg` 3.8.0,
qdrant-client 1.9.2, numpy 1.26.4). Thêm pin `pyarrow==20.0.0`, `pandas==2.3.3` vào constraints vì bản mới hơn đòi NumPy 2.
`python -m pytest tests/ -q`: 86 passed, 3 deselected (integration).
Models/Qdrant/50 answers đã chuẩn bị: Qdrant `qdrant/qdrant:v1.9.7` qua Docker; embedding `BAAI/bge-m3`, reranker
`BAAI/bge-reranker-v2-m3` (cache HuggingFace local). **50 answers chưa sinh được trên máy trưởng nhóm** (xem dưới).
Bước enrichment (m5, có cache) và indexing 130 chunks vào Qdrant chạy thành công.
Hai PDF (`BCTC.pdf`, Nghị định 13) là ảnh scan không có text layer nên m1 bỏ qua (không OCR).
Hai lần chạy `scripts/setup_answers.py --live` đầu bị dừng khi nạp reranker do thiếu bộ nhớ (commit còn trống ~4.7 GB; lần 1 segmentation fault,
lần 2 "memory allocation failed"). Đã thêm `config.EMBEDDING_TORCH_DTYPE`/`RERANK_TORCH_DTYPE` (mặc định `float32`).
Thử cả hai model bfloat16 thì CPU không có lệnh BF16 nên rerank quá chậm, đã dừng. Lần thử thứ tư đặt
`EMBEDDING_TORCH_DTYPE=bfloat16` (chỉ BGE-M3, reranker float32): indexing xong (768 s) nhưng phần trả lời 50 câu vẫn quá chậm
và chiếm ~4 GB RAM nên đã dừng, chuyển cho thành viên khác chạy setup với mặc định float32 trên máy đủ RAM.

## INDIVIDUAL

### DoTrungTuyen-2A202602427

- Phần được giao và phần thực tế đã làm:
  - **Chuẩn bị/tích hợp:** chép m1–m5 từ bài Day 18 và chỉnh adapter theo `doc/PIPELINE_INTERFACE.md`: m2 dùng `search()`
    của qdrant-client 1.9 (khớp server v1.9.7); m4 không nuốt lỗi, không đổi NaN thành 0, chấm lại riêng các câu NaN và trả
    `metadata.evaluator_models` (gpt-4o-mini + text-embedding-3-small); thêm tùy chọn dtype cho BGE-M3/reranker để chạy được
    trên máy ít RAM (chưa đủ để sinh xong answers trên máy này).
  - **Phase A (Tasks 1–4):** `group_by_distribution` kiểm tra distribution lạ; `run_ragas_50q` gọi m4, kiểm tra số dòng và
    từng metric hữu hạn trong [0,1], lấy `evaluator_models` từ m4 (không dùng JUDGE_MODEL); `bottom_10`;
    `cluster_analysis` đếm worst_metric của mọi câu, chọn nhóm yếu theo mean avg_score thấp nhất, bỏ nhóm rỗng.
  - **Phase B (Tasks 5–8):** prompt pairwise có reference và tiêu chí accuracy/completeness/conciseness, `temperature=0`,
    JSON mode, kiểm tra winner/reasoning/scores; `swap_and_average` quy winner và scores lượt 2 về A/B gốc;
    `cohen_kappa` tính tay p_o/p_e, báo lỗi khi κ không xác định; `bias_report` đếm position inconsistency và verbosity
    chỉ trên case decisive.
  - **Phase C (Tasks 9a–12):** `pii_scan` chỉ giữ entity dạng pattern (CCCD/CMND, SĐT VN, email, thẻ, IBAN);
    `check_input_rail`/`check_output_rail` đọc quyết định từ `result.log.activated_rails[].stop`; suite 28 inputs trong
    một event loop, Presidio chặn thì không gọi NeMo; đo latency 2 warm-up + 20 mẫu, luôn đo cả hai tầng.
    Viết lại prompt `self_check_input` trong `guardrails/config.yml`.
  - Code Phase A/B mới được kiểm bằng unit tests (mock); **chưa chạy live** vì chưa có `answers_50q.json`.
  - **Báo cáo nhóm:** `doc/reports/blueprint.md` — kiến trúc guard, failure action, bảng latency, CI gates và monitoring đề xuất
    (phần số liệu Phase A/B để trống chờ lần chạy của thành viên khác).
  - **Phần chuẩn bị báo cáo Phase A/B (không cần chạy model):** trong `failure_clusters.md`, phân tích 10 câu bẫy adversarial
    từ đề và corpus (version conflict 41–45, 49; phủ định 46–48; mâu thuẫn chính sách 50), phát hiện `nghi_phep_nam_v2023.md`
    không ghi trạng thái hết hiệu lực trong khi `mat_khau_v1.md` có, và dòng ngữ cảnh m5 chỉ ghi tên phiên bản; đề xuất sửa.
    Trong `bias_report.md`, đối chiếu 5 candidate B và 10 model_answer với reference, nêu ca dễ lệch (1, 12, 29) và tính độ
    nhạy κ theo số nhãn lệch.
- Bằng chứng: commits trên `main`; `doc/reports/failure_clusters.md`, `doc/reports/bias_report.md` (phần đã viết);
  `artifacts/guard_results.json`
  (attacks 20/20, clean 8/8 allowed, false_positive_rate 0.0, output 4/4, input guard P95 795.57 ms);
  `doc/reports/blueprint.md`.
- Cách kiểm tra: `python -m pytest tests/ -q` → 86 passed (mock, không gọi API); chạy thật Presidio trên 28 inputs trước khi
  chạy batch để chắc 8 câu sạch không bị gắn PII; `python scripts/run_experiments.py --phase c --live --latency-samples 20`
  (runner tự validate schema/counts/percentile trước khi ghi file).
- Điều đã học: guard phải đo bằng cả attacks lẫn clean controls vì hàm luôn chặn cũng đạt 20/20; quyết định block phải lấy
  từ rail đã kích hoạt, không đoán từ chữ "xin lỗi" (câu sạch 102 có chính chữ đó); NER tiếng Anh của Presidio gắn nhầm
  PERSON/LOCATION trên câu tiếng Việt nên phải giới hạn entity; latency input guard bị chi phối bởi lời gọi LLM của NeMo
  (~98%) chứ không phải Presidio; percentile tổng phải tính từ tổng từng mẫu, không cộng P95 từng tầng; trong Phase A,
  matrix worst_metric chỉ mô tả còn nhóm yếu phải chọn theo mean; trong Phase B, winner A/B khác nhãn 0/1.
- Giới hạn/cách xử lý: lần chạy Phase C đầu chặn nhầm 1/8 câu sạch (id 107, quy định độ dài mật khẩu) và lọt 2 câu
  off-topic (id 11, 15); nguyên nhân là prompt dùng "credentials" mơ hồ và không nêu rõ phạm vi. Đã viết lại prompt theo quy tắc
  tổng quát, không sửa fixtures, rồi chạy lại toàn bộ batch C. Vì prompt được chỉnh sau khi xem kết quả trên chính bộ 28 câu,
  20/20 và 8/8 có nguy cơ overfit, cần bộ held-out để xác nhận. Input-layer P95 vượt budget 500 ms, ghi đúng số đo.
  Không sinh được answers do thiếu RAM (mục Môi trường); đã thêm tùy chọn dtype nhưng chưa đủ, giao lại cho thành viên khác.
- Nguồn/AI hỗ trợ nếu có: Claude Code (Claude Opus 5.5) hỗ trợ đọc đề, viết code các Task và soạn báo cáo. Kiểm chứng bằng
  unit tests, chạy thật Presidio, đọc lại JSON do runner sinh; mọi số trong báo cáo lấy từ artifacts,
  không điền tay. Mã m1–m5 lấy từ bài Day 18 (`K4-Track3A-Day18-DoTrungTuyen-2A202602427-ProductionRAG`).

## Cập nhật sau khi nộp

Không có cập nhật sau khi nộp.
