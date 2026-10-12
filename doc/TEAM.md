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
| 1 | Đỗ Trịnh Huy Hoàng | 2A202602392 | Chuẩn bị môi trường, chép m1–m5 vào `src/`, kiểm tra imports, tải model, khởi động Qdrant, chạy setup sinh 50 answers; phụ trách thực nghiệm Phase C (Tasks 9a–12) | `artifacts/answers_50q.json`, `artifacts/guard_results.json`; log setup và Phase C |
| 2 | Đỗ Trung Tuyến | 2A202602427 | Trưởng nhóm. Chuẩn bị môi trường, tích hợp m1–m5; code Tasks 1–12 trong `src/phase_a_ragas.py`, `src/phase_b_judge.py`, `src/phase_c_guard.py`; cấu hình `guardrails/config.yml`; sửa adapter m4 (segmenter faithfulness); chuẩn hóa LF cho JSON (`.gitattributes`); chạy Phase A và chạy lại Phase B/C; viết `failure_clusters.md`, blueprint, cập nhật `bias_report.md` | Commits trên `main`; `artifacts/ragas_50q.json`, `judge_results.json`, `guard_results.json`; ba báo cáo trong `doc/reports/` |
| 3 | Ngô Thế Khanh | 2A202602503 | Phụ trách thực nghiệm Phase A trên bộ 50 answers hiện tại: chạy đánh giá RAGAS và theo dõi batch hoàn tất 200/200 lượt metric | `artifacts/answers_50q.json`, `artifacts/ragas_50q.json`; lệnh `python scripts/run_experiments.py --phase a --live` |
| 4 | Vũ Đình Thư | 2A202602652 | Phụ trách Phase B (Tasks 5–8): pairwise judge, swap-and-average, đối chiếu nhãn nhị phân, Cohen’s κ và phân tích bias; chạy Phase B lần đầu | Commit `b67ba29`; `artifacts/judge_results.json`; log Phase B |

Người tích hợp/nộp link: Đỗ Trung Tuyến. Đỗ Trịnh Huy Hoàng chạy setup tạo 50 answers; artifact hiện tại ghi generation_model là gpt-4o-mini-2024-07-18 (máy trưởng nhóm thiếu RAM ở lần setup ban đầu, xem dưới).
Vũ Đình Thư chạy Phase B lần đầu (commit `b67ba29`). Trưởng nhóm chạy Phase A, rồi chạy lại Phase B và C trên answers hiện tại
sau khi chuẩn hóa LF (lý do ở mục INDIVIDUAL), cập nhật ba báo cáo và chạy `scripts/check_lab.py --with-tests`.

Lịch sử artifact cần phân biệt: commit 150cff2 có 50/50 answers extractive_fallback dù tiêu đề commit ghi Gemini; HEAD bb86e4b hiện tại có 50/50 answers Gemini/LLM được ghi lần cuối ở e51a24e, nhưng context chưa có prefix M5. Các artifacts trong working tree hiện tại là một lần chạy mới: 50/50 GPT/LLM với enrichment context và kết quả Phase A/B/C tương ứng; các cập nhật này chưa được commit.

## Môi trường và chuẩn bị trước lớp

OS/Python/compiler: Windows 11 Home 10.0.26300, CPU Intel i5-8250U, RAM 12 GB, Python 3.12.10; `annoy==1.17.3` đã cài thành công trong virtualenv.
Virtualenv/dependencies/imports: dùng virtualenv Python 3.12 hiện tại của repo (đã xác nhận .venv/Scripts/python.exe là 3.12.10),
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

### DoTrinhHuyHoang-2A202602392

- Phần được giao và phần thực tế đã làm:
  - Chuẩn bị môi trường, chép m1–m5 vào `src/` và kiểm tra imports.
  - Tải model embedding/reranker, khởi động Qdrant và index 130 chunks.
  - Chạy setup tạo đủ 50 answers; artifact hiện tại ghi generation_model là gpt-4o-mini-2024-07-18.
- Phase C (Tasks 9a–12): phụ trách thực nghiệm guardrails trên 20 attacks, 8 clean controls, 4 output cases và đo 20 mẫu latency; log batch input cho thấy 28/28 cases đạt expected result.
- Bằng chứng: `artifacts/answers_50q.json` có 50/50 câu, `generation_mode=llm`,
  `generation_model=gpt-4o-mini-2024-07-18`.
  `artifacts/guard_results.json`; lệnh `python scripts/run_experiments.py --phase c --live --latency-samples 20`.
- Điều đã học: cần kiểm tra cả attacks và clean controls để phát hiện việc chặn nhầm; phải dựa vào rail được kích hoạt để quyết định block; latency của input guard cần ghi rõ phạm vi đo và warm-up.

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
  - **Chạy và tích hợp kết quả cuối (sau khi có answers của Huy Hoàng):**
    - Checker báo Phase B lệch generation model (lần chạy đầu dùng answers cũ). Phát hiện thêm: Git `core.autocrlf=true` khiến
      JSON trên Windows là CRLF, nên mọi `source_sha256` (cả Phase C) sẽ lệch khi người chấm checkout LF. Thêm `.gitattributes`
      (`*.json text eol=lf`), checkout lại, chạy lại Phase B và C; artifacts hiện tại ghi Phase C đạt 20/20, 8/8, 4/4 và input guard P95 808.09 ms.
    - Phase A dừng hai lần vì faithfulness NaN. Truy vết: ragas 0.1.22 chỉ giữ câu kết thúc bằng "." nên answer dạng gạch đầu
      dòng không có statement → NaN tất định. Thêm `_LineSentenceSegmenter` trong `src/m4_eval.py` (áp dụng cho cả 50 câu,
      không đổi NaN thành 0), rồi chạy Phase A thành công.
    - Điền `failure_clusters.md` (bottom 10 phân loại retrieval/generation, matrix, phân tích bẫy adversarial đối chiếu dự đoán),
      cập nhật `bias_report.md` và `blueprint.md` theo artifacts mới.
  - **Báo cáo nhóm:** `doc/reports/blueprint.md` — kiến trúc guard, failure action, bảng latency, CI gates và monitoring đề xuất
    (số liệu Phase A/B/C đã đồng bộ theo artifacts hiện tại).
  - **Phần chuẩn bị báo cáo Phase A/B (không cần chạy model):** trong `failure_clusters.md`, phân tích 10 câu bẫy adversarial
    từ đề và corpus (version conflict 41–45, 49; phủ định 46–48; mâu thuẫn chính sách 50), phát hiện `nghi_phep_nam_v2023.md`
    không ghi trạng thái hết hiệu lực trong khi `mat_khau_v1.md` có, và dòng ngữ cảnh m5 chỉ ghi tên phiên bản; đề xuất sửa.
    Trong `bias_report.md`, đối chiếu 5 candidate B và 10 model_answer với reference, nêu ca dễ lệch (1, 12, 29) và tính độ
    nhạy κ theo số nhãn lệch.
- Bằng chứng: commits trên `main`; `artifacts/ragas_50q.json` (adversarial 0.667 < multi_hop 0.677 < factual 0.859; faithfulness mean toàn bộ 0.689);
  `artifacts/judge_results.json` (κ = 1.000, position inconsistency 1/5 (cặp 12); verbosity win rate 3/4); `artifacts/guard_results.json` (attacks 20/20,
  clean 8/8 allowed, false_positive_rate 0.0, output 4/4, input guard P95 808.09 ms); ba báo cáo trong `doc/reports/`.
- Cách kiểm tra: `python scripts/check_lab.py --with-tests` (86 unit tests + đối chiếu hợp đồng 4 JSON); chạy thật Presidio trên 28 inputs trước khi
  chạy batch để chắc 8 câu sạch không bị gắn PII; `python scripts/run_experiments.py --phase c --live --latency-samples 20`
  (runner tự validate schema/counts/percentile trước khi ghi file).
- Điều đã học: guard phải đo bằng cả attacks lẫn clean controls vì hàm luôn chặn cũng đạt 20/20; quyết định block phải lấy
  từ rail đã kích hoạt, không đoán từ chữ "xin lỗi" (câu sạch 102 có chính chữ đó); NER tiếng Anh của Presidio gắn nhầm
  PERSON/LOCATION trên câu tiếng Việt nên phải giới hạn entity; latency input guard bị chi phối bởi lời gọi LLM của NeMo
  (~98%) chứ không phải Presidio; percentile tổng phải tính từ tổng từng mẫu, không cộng P95 từng tầng; trong Phase A,
  matrix worst_metric chỉ mô tả còn nhóm yếu phải chọn theo mean; trong Phase B, winner A/B khác nhãn 0/1.
  Từ artifacts hiện tại: RAGAS faithfulness cao không đảm bảo xử lý đúng phiên bản (câu 41–42 nêu cả hai phiên bản và đạt 1.0; câu 43 từ chối dù context có cả hai mức), và nhãn
  "hallucinating" tự động sai với câu "Không tìm thấy."; bằng chứng hash phụ thuộc cả line ending, nên artifact sinh trên
  Windows phải được kiểm tra với bản checkout LF.
- Giới hạn/cách xử lý: lần chạy Phase C đầu chặn nhầm 1/8 câu sạch (id 107, quy định độ dài mật khẩu) và lọt 2 câu
  off-topic (id 11, 15); nguyên nhân là prompt dùng "credentials" mơ hồ và không nêu rõ phạm vi. Đã viết lại prompt theo quy tắc
  tổng quát, không sửa fixtures, rồi chạy lại toàn bộ batch C. Vì prompt được chỉnh sau khi xem kết quả trên chính bộ 28 câu,
  20/20 và 8/8 có nguy cơ overfit, cần bộ held-out để xác nhận. Input-layer P95 vượt budget 500 ms, ghi đúng số đo.
  Không sinh được answers do thiếu RAM (mục Môi trường); đã thêm tùy chọn dtype nhưng chưa đủ, giao lại cho thành viên khác.
- Nguồn/AI hỗ trợ nếu có: Claude Code (Claude Opus 5.5) hỗ trợ đọc đề, viết code các Task và soạn báo cáo. Kiểm chứng bằng
  unit tests, chạy thật Presidio, đọc lại JSON do runner sinh; mọi số trong báo cáo lấy từ artifacts,
  không điền tay. Mã m1–m5 lấy từ bài Day 18 (`K4-Track3A-Day18-DoTrungTuyen-2A202602427-ProductionRAG`).

### NgoTheKhanh-2A202602503

- Phần được giao và phần thực tế đã làm:
  - Phụ trách thực nghiệm Phase A trên bộ 50 answers hiện tại, chạy `python scripts/run_experiments.py --phase a --live`.
  - Theo dõi quá trình chấm bốn metric RAGAS cho 50 câu (200 lượt đánh giá) đến khi hoàn tất và lưu kết quả.
- Bằng chứng: `artifacts/answers_50q.json` chứa bộ 50 câu đầu vào; `artifacts/ragas_50q.json` chứa kết quả Phase A.
- Điều đã học: bốn metric RAGAS phản ánh các phần khác nhau của pipeline — độ hỗ trợ của context cho answer, độ phù hợp của answer với câu hỏi, và độ chính xác/độ bao phủ của retrieval. Vì vậy cần đọc các câu điểm thấp cùng contexts và reference trước khi kết luận nguyên nhân.
- Giới hạn: hai PDF scan ảnh (`BCTC.pdf` và Nghị định 13) không có text layer nên bị bỏ qua khi tạo dữ liệu đầu vào; kết quả Phase A không đánh giá nội dung của hai tài liệu này.

### VuDinhThu-2A202602652

- Phần được giao và phần thực tế đã làm:
  - Phụ trách Phase B (Tasks 5–8), chạy lần đầu pairwise judge và quy trình swap-and-average cho các cặp A/B.
  - Đối chiếu nhãn tốt/xấu của judge với nhãn người đánh giá, tính Cohen’s κ và tổng hợp dấu hiệu position/verbosity bias.
- Bằng chứng: commit `b67ba29`; `artifacts/judge_results.json` là kết quả Phase B được lưu trong repo.
- Điều đã học: winner A/B của một cặp khác với nhãn tốt/xấu 0/1 của một answer riêng lẻ; đổi vị trí A/B giúp nhận diện kết quả thiếu ổn định; κ hiệu chỉnh mức đồng thuận ngẫu nhiên. Tỷ lệ bias trên mẫu nhỏ là dấu hiệu để đọc lại câu trả lời, không phải kết luận nguyên nhân.
- Giới hạn: Phase B dùng 5 cặp pairwise và 10 nhãn nhị phân nên kết quả bias/đồng thuận chỉ phản ánh mẫu kiểm thử này.

## Cập nhật sau khi nộp

Không có cập nhật sau khi nộp.
