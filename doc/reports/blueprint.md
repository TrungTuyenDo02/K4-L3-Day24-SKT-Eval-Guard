# Blueprint CI/CD cho RAG và guardrails

Nhóm: SKT

Người phụ trách: Đỗ Trung Tuyến — 2A202602427.

Đây là đề xuất CI/CD, không phải workflow đã được triển khai/chạy. Số liệu hiện tại lấy từ artifacts/ragas_50q.json, artifacts/judge_results.json và artifacts/guard_results.json. Phase A chạy lúc 2026-10-12 18:25:03 ICT, Phase B lúc 18:27:10 ICT, Phase C lúc 18:28:33 ICT. Answers hiện tại là 50/50 LLM, model gpt-4o-mini-2024-07-18; judge và guard là gpt-4o-mini. Context trong answers có enrichment prefix M5. Những ghi chú cũ về Gemini, điểm Phase A và latency Phase C không mô tả các artifact hiện tại.

Lịch sử Git có commit 150cff2 với 50/50 answers extractive_fallback dù tên commit ghi Gemini. HEAD hiện tại bb86e4b có 50/50 answers Gemini/LLM được ghi lần cuối ở e51a24e, nhưng context chưa có tiền tố M5. Số liệu blueprint này lấy từ artifacts mới hơn trong working tree; chúng chưa được commit.

## Kiến trúc và failure action

Luồng đề xuất: input → Presidio → NeMo input → RAG → NeMo output → response. Request thật dừng sớm nếu bị chặn; phép đo latency input hiện tại chạy tuần tự qua cả Presidio và NeMo input.

1. Presidio chạy local để quét CCCD/CMND, số điện thoại Việt Nam, email và các pattern PII đã cấu hình. Chỉ giữ các entity dạng pattern đáng tin cậy; NER tiếng Anh có thể nhận nhầm tên/địa điểm trong tiếng Việt. Khi có PII, block và log bản đã ẩn danh cùng loại entity/vị trí, không lưu chuỗi gốc.
2. NeMo input rail dùng self-check để chặn off-topic, jailbreak/role-play, mạo danh quyền, yêu cầu system prompt và yêu cầu dữ liệu cá nhân/mật khẩu.
3. RAG dùng hybrid BM25 + BGE-M3/Qdrant, bge-reranker-v2-m3 top 3, rồi generation bằng gpt-4o-mini-2024-07-18 trong artifact hiện tại.
4. NeMo output rail kiểm tra answer. Hai output chứa CCCD hoặc mật khẩu trong test bị thay bằng câu từ chối; hai output sạch được giữ nguyên.

Khi self-check LLM lỗi hoặc timeout, hướng đề xuất là fail-closed: không trả answer chưa kiểm tra; input rail trả thông báo thử lại. Secrets chỉ nằm trong environment/secret store, không ghi vào artifact. Luồng này cần được triển khai và kiểm thử nếu dùng trong production.

## Phạm vi latency và số đo Phase C

Artifact đo 20 mẫu timed sau 2 warm-up. Scope là input_layers_sequential; percentile dùng nội suy tuyến tính trên raw samples. Tổng input guard là tổng từng mẫu Presidio + NeMo, không phải tổng hai percentile.

| Layer / scope | P50 ms | P95 ms | P99 ms | Tình trạng |
|---|---:|---:|---:|---|
| Presidio | 5.86 | 6.46 | 6.61 | Đã đo |
| NeMo input | 639.71 | 802.22 | 895.89 | Đã đo |
| Input guard sequential | 645.96 | 808.09 | 901.50 | Đã đo; vượt budget 500 ms |
| RAG | chưa đo | chưa đo | chưa đo | Ngoài phạm vi |
| NeMo output | chưa đo | chưa đo | chưa đo | Ngoài phạm vi |
| Full request / short-circuit | chưa đo | chưa đo | chưa đo | Không suy ra từ input layers |

Phase C: attacks 20/20 đạt expected result; clean controls 8/8 được cho qua (false-positive rate 0%); output cases 4/4 đúng. Input guard P95 là 808.09 ms nên không đạt budget 500 ms. NeMo self-check chiếm gần như toàn bộ độ trễ; tối ưu Presidio riêng sẽ không đủ để đạt target.

Hướng xử lý có thể đo lại: thử classifier local cho off-topic/jailbreak và chỉ gọi LLM khi không chắc; đo lại đúng suite 28 input và latency 20 mẫu. Có thể đo thêm RAG, output rail và full request riêng với tối thiểu 2 warm-up cùng ít nhất 50 timed samples; không gộp kết quả đó vào input_layers_sequential.

## CI gates đề xuất

Các gate sau là ngưỡng đề xuất, hiện không phải toàn bộ gate của checker:

- Phase A: faithfulness mean ≥0.75 và avg_score ≥0.65 trên 50 câu.
- Phase C: attacks ≥18/20, clean 8/8 không bị chặn nhầm, output cases đúng.
- Full guard P95 <500 ms chỉ bật sau khi đo full request thực sự.

Đối chiếu artifact hiện tại:

- Phase A faithfulness mean = 0.689, thấp hơn ngưỡng đề xuất 0.75; avg_score = 0.748, cao hơn 0.65. Vì vậy một gate kết hợp cả hai sẽ không đạt.
- Distribution avg_score: factual 0.859, multi_hop 0.677, adversarial 0.667. Adversarial thấp nhất; khoảng cách với multi_hop chỉ 0.011.
- Bảy answers là “Không tìm thấy.”; có trường hợp context đủ để trả lời phủ định (44, 48, 50) và trường hợp retrieval thiếu một phần (22, 33, 39). Cần thêm kiểm tra answer/context theo reference, không chỉ mean.
- Phase B: κ = 1.000 trên 10 nhãn; position inconsistency 1/5; verbosity win rate 3/4 decisive pairs. Mẫu nhỏ nên tie hoặc reasoning sai cần người review.
- Phase C đạt 20/20 attacks, 8/8 clean controls và 4/4 output cases; latency input P95 chưa đạt target.

Workflow dưới đây là minh họa, chưa có trong repo:

    .github/workflows/eval-guard.yml — đề xuất
    pull request: khi đổi src/, guardrails/, data/ hoặc fixtures/
    offline: chạy unit tests
    live: chỉ chạy khi có secret OPENAI_API_KEY
    setup: setup_answers.py --live
    experiments: run_experiments.py --phase all --live --latency-samples 20
    validate: check_lab.py
    quality_gates: script ci_gates.py cần được viết; hiện chưa tồn tại

Checker xác nhận hợp đồng và các tiêu chí bắt buộc của lab; checker không tự thay rubric bằng các gate chất lượng đề xuất ở trên.

## Monitoring và cải tiến

| Metric | Cách lấy | Ngưỡng cảnh báo đề xuất |
|---|---|---|
| Tỷ lệ block input theo tầng | blocked_by / tổng request mỗi giờ | Lệch hơn 2 lần baseline 7 ngày |
| False positive | Review 50 request bị block mỗi tuần | Trên 5% câu hợp lệ bị block |
| Input guard latency | Raw perf_counter theo tầng | P95 >500 ms trong 15 phút |
| RAG quality | 50 câu/tuần với reference đã duyệt | Faithfulness <0.75 hoặc giảm >0.05 |
| Policy drift | Khi data/ có phiên bản mới | Chạy lại test version-conflict và multi-hop |

Privacy: chỉ lưu input đã ẩn danh, loại entity, rail và latency; secrets ở secret store. Owner RAG xử lý cảnh báo chất lượng; owner guard xử lý false positive và latency. False positives đã xác nhận nên được thêm vào clean set, không xóa attack cũ.

Cải tiến ưu tiên:

1. Sửa prompt generation để trả lời phần có căn cứ, nêu rõ phần context còn thiếu, tính toán khi đủ dữ kiện và không bỏ qua quy định phủ định.
2. Gắn metadata phiên bản/trạng thái bằng quy tắc xác định từ tài liệu; kiểm tra các context v2023 đang bị gắn “hiện hành” dù v2024 nói đã thay thế.
3. Cải thiện chunk bảng và truy vấn multi-hop; đo lại context recall trên các câu 22, 33, 39 và đọc thủ công câu 41–44, 49.
4. Điều tra chênh lệch giữa RAGAS và đọc context ở các câu 5, 31; không coi faithfulness=0 là bằng chứng hallucination khi answer được context hỗ trợ.
5. Giảm latency NeMo input hoặc dùng tầng classifier local; giữ clean controls và thêm bộ held-out để hạn chế overfit prompt.
