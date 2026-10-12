# Phân tích lỗi Phase A

Nhóm: SKT

Người phụ trách phân tích: Đỗ Trung Tuyến — 2A202602427. Thực nghiệm Phase A: Ngô Thế Khanh — 2A202602503.

Nguồn số liệu: artifacts/ragas_50q.json và artifacts/answers_50q.json. Thời điểm Phase A: 2026-10-12 18:25:03 ICT (UTC+07:00).

## Phân biệt các phiên bản trong Git

Nhận xét về fallback đúng với commit 150cff2 (feat: add Gemini generation and 50 answers): artifact trong commit đó có 50/50 generation_mode=extractive_fallback, generation_model=null; answer câu 41 trùng nguyên văn context đầu tiên, và contexts chưa có tiền tố M5. Không dùng artifact của commit này để diễn giải các số liệu hiện tại.

ASSIGNMENT.md cho phép fallback nếu ghi rõ. Nếu chấm Phase A/B trên artifact của 150cff2 thì phải công khai đó là extractive fallback; Phase A khi ấy đo retrieval/context copying, còn Phase B so sánh đoạn trích với candidate B, nên không đại diện cho chất lượng câu trả lời do LLM/RAG sinh.

Ở HEAD bb86e4b (answers được ghi lần cuối trong commit e51a24e), file answers có 50/50 generation_mode=llm, model gemini-3.5-flash-lite; Phase A/B trong HEAD cũng ghi model Gemini. Tuy nhiên contexts ở bản HEAD vẫn chưa có tiền tố enrichment M5. Báo cáo hiện tại mô tả các artifacts mới hơn đang có trong working tree: 50/50 câu do gpt-4o-mini-2024-07-18 sinh, contexts có enrichment prefix; các file này chưa được commit. Như vậy lịch sử từng có một commit fallback thật, nhưng nó khác cả HEAD và bộ kết quả hiện tại.

## Xác nhận bộ answers và enrichment

Trong bộ artifacts hiện có, 50/50 câu có generation_mode là llm và generation_model là gpt-4o-mini-2024-07-18; không có câu nào là extractive_fallback. Trong scripts/setup_answers.py, nhánh llm chỉ trả về sau khi lời gọi chat completion thành công; ngoại lệ sẽ được in ra và kết quả được đánh dấu extractive_fallback với generation_model là null. Vì vậy metadata và code của bản này cùng xác nhận câu trả lời được sinh qua API, không phải chép nguyên context đầu tiên.

Ví dụ câu 41: answer là “Mỗi nhân viên chính thức được hưởng 15 ngày phép năm có lương”, trong khi context thứ nhất nêu 12 ngày và context thứ hai nêu 15 ngày. Answer không bằng context đầu tiên.

Enrichment M5 đã chạy trong lần setup này: scripts/setup_answers.py gọi enrich_chunks trước khi index, log setup ghi 130 chunks enriched, và retrieved contexts có tiền tố mô tả tài liệu/mục như “Đoạn văn thuộc tài liệu ...”. Tuy nhiên, một số tiền tố có trạng thái phiên bản mâu thuẫn với nội dung nguồn: context v2023 có chỗ ghi “trạng thái: hiện hành” dù context v2024 nói đã thay thế chính sách 2023. Đây là vấn đề về chất lượng metadata enrichment, không phải bằng chứng M5 bị bỏ qua.

Ghi chú cấu hình: ENRICH_PREFIX_MIN_CHARS và GEMINI_EMBEDDING_MODEL hiện chỉ được khai báo trong config.py, không có nơi sử dụng khác. Hai biến chưa được nối vào luồng hiện tại; điều đó không phủ định lời gọi enrich_chunks. Embedding trong pipeline này dùng cấu hình BGE-M3/FastEmbed, còn generation model được ghi thực tế trong artifact là gpt-4o-mini-2024-07-18.

## Cách Task 1–4 được implement

- Task 1 group_by_distribution: nhóm theo distribution và kiểm tra phân phối ngoài dự kiến.
- Task 2 run_ragas_50q: chấm đủ 50 câu bằng bốn metric; kiểm tra số lượng, giá trị hữu hạn và miền [0,1], giữ metadata model evaluator.
- Task 3 bottom_10: sắp tăng theo avg_score, đính kèm metric thấp nhất và chẩn đoán tự động.
- Task 4 cluster_analysis: đếm worst_metric trên toàn bộ câu, tính avg_score theo distribution và chọn nhóm có trung bình thấp nhất.
- Adapter m4 có _LineSentenceSegmenter để xử lý câu trả lời dạng bullet khi RAGAS faithfulness parser bỏ qua dòng không có dấu chấm. Metric NaN được chấm lại riêng; không đổi NaN thành 0.

## Điểm theo distribution

| Distribution | n | Faithfulness | Answer relevancy | Context precision | Context recall | Avg score |
|---|---:|---:|---:|---:|---:|---:|
| factual | 20 | 0.933 | 0.551 | 1.000 | 0.950 | 0.859 |
| multi_hop | 20 | 0.490 | 0.465 | 0.933 | 0.821 | 0.677 |
| adversarial | 10 | 0.600 | 0.391 | 0.958 | 0.717 | 0.667 |
| Toàn bộ | 50 | 0.689 | 0.485 | 0.965 | 0.852 | 0.748 |

Adversarial là nhóm thấp nhất (0.667), sát với multi_hop (0.677); factual đạt 0.859. Context precision cao ở cả ba nhóm, nhưng không đồng nghĩa mọi ý cần trả lời đều được retrieve. Faithfulness toàn bộ là 0.689, thấp hơn ngưỡng 0.75 được đề xuất trong blueprint; checker qua không có nghĩa chất lượng RAG đạt ngưỡng đó.

## Bottom 10 và nguyên nhân đọc thủ công

Bảng xếp hạng/metric lấy từ artifact; nhận định nguyên nhân dựa trên đối chiếu answer, context và ground truth. Diagnosis tự động “LLM hallucinating” không nên xem là kết luận: có câu trả lời đúng hoặc refusal hợp lý nhưng faithfulness bằng 0.

| Rank | ID | Nhóm | Avg | F / AR / CP / CR | Worst metric | Diagnosis tự động → suggested_fix | Đọc answer và context |
|---:|---:|---|---:|---|---|---|---|
| 1 | 39 | multi_hop | 0.000 | 0 / 0 / 0 / 0 | faithfulness | LLM hallucinating → Tighten system prompt, lower temperature | Refusal. Context có ghi chính sách cũ bị thay thế và một phần MFA, nhưng thiếu các giá trị cần so sánh về độ dài/thời hạn đổi mật khẩu; retrieval chưa đủ cho toàn câu hỏi. |
| 2 | 33 | multi_hop | 0.375 | 0 / 0 / 1 / 0.5 | faithfulness | LLM hallucinating → Tighten system prompt, lower temperature | Refusal dù context có 15 ngày và quy tắc thâm niên; chưa có đủ phụ cấp ăn trưa và điện thoại Manager. Retrieval thiếu một phần, refusal toàn bộ làm mất phần có thể trả lời. |
| 3 | 44 | adversarial | 0.396 | 0 / 0 / 0.583 / 1 | faithfulness | LLM hallucinating → Tighten system prompt, lower temperature | Refusal dù contexts có cả 90 ngày và 120 ngày, cùng ghi chú v1.0 bị thay thế bởi v2.0. Cần ưu tiên 120 ngày. |
| 4 | 43 | adversarial | 0.417 | 0 / 0 / 1 / 0.667 | faithfulness | LLM hallucinating → Tighten system prompt, lower temperature | Refusal; contexts có cả 12 và 8 ký tự nhưng nhãn phiên bản chưa rõ/không nhất quán. Có dữ kiện để trả lời theo v2.0 nếu metadata phiên bản được xử lý đúng. |
| 5 | 48 | adversarial | 0.417 | 0 / 0 / 1 / 0.667 | faithfulness | LLM hallucinating → Tighten system prompt, lower temperature | Refusal dù context nói rõ nhân viên thử việc chưa được hưởng PVI. Lỗi trả lời phủ định có căn cứ. |
| 6 | 50 | adversarial | 0.417 | 0 / 0 / 1 / 0.667 | faithfulness | LLM hallucinating → Tighten system prompt, lower temperature | Refusal dù context cấm NordVPN/ExpressVPN và yêu cầu VPN WireGuard công ty. Lỗi trả lời phủ định có căn cứ. |
| 7 | 22 | multi_hop | 0.417 | 0 / 0 / 1 / 0.667 | faithfulness | LLM hallucinating → Tighten system prompt, lower temperature | Refusal dù context xác nhận cấu hình laptop cần CNTT và 30 triệu thuộc thẩm quyền Director; context không có yêu cầu 3 báo giá. Nên trả lời phần có căn cứ và nêu phần chưa tìm được. |
| 8 | 31 | multi_hop | 0.539 | 0 / 0.489 / 1 / 0.667 | faithfulness | LLM hallucinating → Tighten system prompt, lower temperature | Answer tính đúng 1.200.000 × 2 = 2.400.000 VNĐ; context hỗ trợ trực tiếp. Faithfulness=0 là bất đồng đáng ngờ của evaluator, không phải lỗi câu trả lời hiển nhiên. |
| 9 | 21 | multi_hop | 0.548 | 0.857 / 0 / 0.833 / 0.5 | answer_relevancy | Answer doesn't match question → Improve prompt template | Answer ra tổng 18 ngày nhưng giải thích sai thành 12+6 thay vì 15+3; không có context mức lương Senior nên thiếu phần lương. Cả version handling và retrieval đều cần cải thiện. |
| 10 | 5 | factual | 0.592 | 0 / 0.367 / 1 / 1 | faithfulness | LLM hallucinating → Tighten system prompt, lower temperature | Answer nói CEO và context có dòng “trên 50 triệu → CEO”, khớp ground truth. Faithfulness=0 cho thấy diagnosis tự động có thể sai. |

Có 7 answer “Không tìm thấy” trong 50 câu: 22, 33, 39, 43, 44, 48, 50. Chúng không cùng một loại lỗi: 39 thiếu nhiều dữ kiện; 33/22 thiếu một phần context; 44/48/50 có dữ kiện quan trọng; 43 có dữ kiện nhưng version metadata nhập nhằng. Các refusal cũng không phải hallucination. Ngược lại, câu 5 và 31 có answer được context hỗ trợ nhưng faithfulness bằng 0. Vì vậy cần đọc tay các ca thấp điểm thay vì coi metric/chẩn đoán tự động là sự thật.

## Matrix worst_metric × distribution

| Worst metric | factual | multi_hop | adversarial | Tổng |
|---|---:|---:|---:|---:|
| faithfulness | 2 | 12 | 4 | 18 |
| context_recall | 1 | 0 | 3 | 4 |
| context_precision | 0 | 0 | 0 | 0 |
| answer_relevancy | 17 | 8 | 3 | 28 |
| Tổng | 20 | 20 | 10 | 50 |

Answer relevancy là worst_metric thường gặp nhất (28/50), còn nhóm yếu nhất theo avg_score là adversarial. Hai con số trả lời hai câu hỏi khác nhau: metric nào thường thấp nhất và loại câu nào có điểm trung bình thấp nhất. Context recall adversarial là 0.717, thấp hơn factual và multi_hop.

## Đối chiếu 10 câu adversarial

| ID | Bẫy | Answer thực tế | Đánh giá nội dung |
|---:|---|---|---|
| 41 | Hai phiên bản phép năm | Trả lời 15 ngày | Đúng giá trị hiện hành; context cũng chứa 12 ngày của v2023 nên cần giữ rõ nhãn phiên bản. |
| 42 | Hai phiên bản thâm niên | Nêu 5 năm theo 2023 và 3 năm theo 2024 | Có cả hai giá trị nhưng chưa nhấn mạnh câu hỏi nên ưu tiên v2024; tiền tố enrichment gọi v2023 là hiện hành gây nhiễu. |
| 43 | Mật khẩu tối thiểu | Không tìm thấy | Context có cả 12 và 8; cần chọn 12 theo v2.0 và nhận diện 8 là bản cũ. |
| 44 | Chu kỳ đổi mật khẩu | Không tìm thấy | Context có 90 và 120 ngày, có ghi v1.0 đã bị thay thế; đáp án đúng là 120. |
| 45 | MFA | Trả lời bắt buộc cho email, VPN, hệ thống nội bộ | Đúng nội dung được hỏi. |
| 46 | Phủ định nghỉ phép thử việc | Trả lời không được nghỉ phép năm | Đúng ý chính, thiếu điều kiện xin nghỉ không lương và trưởng phòng phê duyệt. |
| 47 | Malware | Khuyên không tự xử lý | Đúng ý chính, thiếu yêu cầu báo sự cố trong 1 giờ và kênh liên hệ. |
| 48 | Phủ định PVI | Không tìm thấy | Context nêu rõ thử việc chưa được hưởng PVI; nên trả lời không. |
| 49 | Hỏi bản cũ và hiện hành | Nêu 12 ngày v2023 và 15 ngày v2024 | Đúng hai mức cơ bản; chưa nêu các quy tắc thâm niên theo từng phiên bản. |
| 50 | VPN cá nhân | Không tìm thấy | Context cấm VPN cá nhân và yêu cầu WireGuard công ty; nên bác bỏ giả định. |

RAGAS không tự phát hiện được mọi sai sót phiên bản: câu 41 và 42 có faithfulness 1.0 dù cần diễn giải trạng thái chính sách cẩn thận. Cần đánh giá theo reference và kiểm tra thủ công các câu version conflict.

## Đề xuất sửa có thể kiểm tra

1. Prompt generation: trả lời phần được context hỗ trợ, nêu rõ phần còn thiếu, tính toán khi đủ số liệu, và dùng thông tin phủ định khi context có lệnh cấm/không được. Chỉ từ chối toàn bộ khi không có dữ kiện liên quan.
2. Version metadata: đưa version/effective status/superseded_by vào từng child chunk bằng dữ liệu xác định từ tài liệu; không để enrichment suy đoán “hiện hành”. Đo lại bằng câu 41–44, 49.
3. Retrieval: giữ nguyên hàng/header khi chunk bảng; không để chunk tiêu đề hoặc note thay thế chiếm top-k; thử tăng top-k hay tách truy vấn cho multi-hop. Đo context recall và kiểm tra các câu 22, 33, 39.
4. Evaluator: kiểm tra thủ công các answer được context hỗ trợ nhưng faithfulness=0 (5, 31) và các refusal có context nhưng metric=0. Không dùng worst_metric tự động làm nhãn nguyên nhân cuối cùng.
5. Chạy lại setup_answers và Phase A sau thay đổi; so sánh faithfulness, context_recall, số refusal và đọc lại bộ adversarial. Giữ nguyên test set để so sánh trực tiếp.

## Giới hạn

- 10 câu adversarial là mẫu nhỏ; chênh biệt giữa adversarial và multi_hop chỉ khoảng 0.011.
- Một số câu trả lời chính xác theo context lại có faithfulness=0; diễn giải điểm cần đối chiếu thủ công.
- Hai PDF scan BCTC.pdf và Nghị định 13 không có text layer nên bị bỏ qua, không được đánh giá bằng bộ này.
