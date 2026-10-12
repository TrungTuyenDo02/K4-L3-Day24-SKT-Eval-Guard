# Phân tích lỗi Phase A

Nhóm: SKT

Người phụ trách: Đỗ Trung Tuyến — 2A202602427 (code Tasks 1–4, phân tích bẫy từ đề/corpus); số liệu và phân tích
bottom 10 do thành viên chạy Phase A bổ sung.

> **Trạng thái tại commit này:** Phase A **chưa chạy**. Chưa có `artifacts/answers_50q.json` (máy trưởng nhóm thiếu RAM khi
> sinh answers, xem `doc/TEAM.md`) nên chưa có `artifacts/ragas_50q.json`. Mọi mục ghi "CHỜ KẾT QUẢ" phải được điền từ JSON
> do runner sinh; không điền số ước lượng.

Nguồn: `artifacts/ragas_50q.json`; run timestamp: CHỜ KẾT QUẢ (lấy `metadata.created_at`).
Generation mode/fallback và điều kiện chạy: CHỜ KẾT QUẢ (đếm `generation_mode` trong answers; ghi số câu `extractive_fallback` nếu có).
Models generation/evaluator: dự kiến generation `gpt-4o-mini`; evaluator do m4 báo `gpt-4o-mini` + `text-embedding-3-small`.
Ghi lại đúng theo `metadata.models` sau khi chạy.

## Cách Task 1–4 được implement (đã xong, 6 unit tests pass)

- **Task 1 `group_by_distribution`:** chia theo trường `distribution`, báo lỗi nếu gặp distribution lạ; test xác nhận 20/20/10.
- **Task 2 `run_ragas_50q`:** gọi `m4_eval.evaluate_ragas` một lần cho 50 câu, kiểm tra m4 trả đúng 50 dòng, chuyển từng metric
  sang `float` và từ chối giá trị NaN/ngoài [0,1] (không thay bằng 0). `evaluator_models` lấy từ `raw["metadata"]`; thiếu
  thì báo lỗi, không dùng `JUDGE_MODEL` thay. Adapter m4 chấm lại tối đa 2 lượt riêng các câu RAGAS trả NaN.
- **Task 3 `bottom_10`:** sắp tăng dần `avg_score`, lấy tối đa 10 câu, kèm rank, worst_metric, diagnosis/suggested_fix từ
  `DIAGNOSTIC_TREE`.
- **Task 4 `cluster_analysis`:** matrix đếm worst_metric của **mọi** câu (tổng cột 20/20/10 chỉ là kích thước nhóm);
  nhóm yếu = distribution có mean `avg_score` thấp nhất, nhóm rỗng bị bỏ khỏi phép chia; insight nêu xếp hạng mean,
  metric chủ đạo và số câu của nó trong nhóm yếu.

## Điểm theo distribution

CHỜ KẾT QUẢ — điền bảng 4 metric + avg_score × factual (20) / multi_hop (20) / adversarial (10) từ `per_distribution`.

## Bottom 10 và nguyên nhân

CHỜ KẾT QUẢ — điền đúng 10 rows từ `bottom_10` (rank, id, question, distribution, avg_score, worst_metric, diagnosis,
suggested_fix). Với mỗi câu, đọc `answer`, `contexts` và `ground_truth` trong `per_question` rồi phân loại:

| Dấu hiệu khi đọc | Loại lỗi | Hướng sửa cụ thể |
|---|---|---|
| contexts không chứa ý trong reference (context_recall thấp) | Retrieval thiếu | tăng top_k trước rerank, thêm BM25 cho số liệu, chunk nhỏ hơn cho bảng |
| contexts có nhiều chunk không liên quan (context_precision thấp) | Retrieval nhiễu | filter metadata theo tài liệu/phiên bản, giữ reranker |
| contexts đúng nhưng answer thêm/sai ý (faithfulness thấp) | Generation hallucinate | prompt bắt trích dẫn, `temperature=0`, cấm suy diễn ngoài context |
| answer lạc đề hoặc chỉ nói "Không tìm thấy" (answer_relevancy thấp) | Generation/prompt | prompt yêu cầu trả lời thẳng câu hỏi, nêu phiên bản áp dụng |
| contexts có cả v2023 và v2024, answer chọn bản cũ | Version conflict | metadata `effective_date`/`superseded`, prompt ưu tiên bản mới nhất |

Lưu ý khi đọc điểm: RAGAS chấm faithfulness theo contexts, không theo reference. Một answer trả "12 ngày" bám đúng chunk v2023
vẫn có thể có faithfulness cao dù sai so với reference; lỗi đó lộ ra ở context_precision/recall hoặc phải đọc tay.

## Matrix và nhóm yếu nhất

CHỜ KẾT QUẢ — điền matrix 4 metric × 3 distribution từ `failure_clusters.matrix`, nhóm yếu theo
`distribution_avg_scores`, metric chủ đạo và số câu của nó. Không dùng tổng cột 20/20/10 để chọn nhóm yếu.

## Bẫy adversarial và giới hạn

Phân tích dưới đây làm từ `fixtures/test_set_50q.json` và corpus `data/`, **trước khi có điểm**; dùng để đối chiếu khi đọc
answers. Điểm adversarial thấp hơn chỉ cho thấy nhóm khó hơn, không chứng minh pipeline đã nhận ra (hoặc mắc) bẫy.

| ID | Loại bẫy | Tài liệu liên quan | Đáp án đúng | Kiểu sai dễ gặp |
|---|---|---|---|---|
| 41 | Version conflict | `nghi_phep_nam_v2023.md` vs `v2024.md` | 15 ngày (+1/3 năm) theo v2024 | trả 12 ngày theo v2023 |
| 42 | Version conflict | như trên | từ 3 năm, mỗi 3 năm +1 ngày | trả 5 năm theo v2023 |
| 43 | Version conflict | `mat_khau_v1.md` vs `mat_khau_v2.md` | tối thiểu 12 ký tự | trả 8 ký tự theo v1.0 |
| 44 | Version conflict | như trên | đổi mỗi 120 ngày | trả 90 ngày theo v1.0 |
| 45 | Version conflict | như trên | MFA bắt buộc (email, VPN, hệ thống nội bộ) | nói không bắt buộc vì v1.0 không nhắc MFA |
| 46 | Phủ định | `thu_viec.md` | KHÔNG được phép năm, xin nghỉ không lương | áp dụng 15 ngày phép cho thử việc |
| 47 | Phủ định | `bao_mat_su_co.md` | KHÔNG tự xử lý, báo trong 1 giờ | hướng dẫn tự quét/xóa malware |
| 48 | Phủ định ngầm | `thu_viec.md` (+ `bao_hiem_suc_khoe.md`) | KHÔNG được PVI, chỉ BHXH | nói "có" vì tài liệu PVI ghi "toàn diện" |
| 49 | Version conflict có chủ đích | v2023 + v2024 | v2023: 12 ngày (+1/5 năm, hết hiệu lực); hiện hành v2024: 15 ngày (+1/3 năm) | chỉ trả một bản hoặc không nói bản nào hiệu lực |
| 50 | Mâu thuẫn chính sách | `vpn_truy_cap.md` | KHÔNG dùng VPN cá nhân, bắt buộc WireGuard | đồng ý vì "tăng bảo mật" nghe hợp lý |

Quan sát từ corpus giải thích vì sao các bẫy này khó với pipeline hiện tại:

- **Hai cặp phiên bản đánh dấu không giống nhau.** `mat_khau_v1.md` ghi rõ "Trạng thái: ĐÃ THAY THẾ bởi v2.0", nên nếu chunk tiêu đề
  được lấy cùng nội dung thì LLM có tín hiệu loại bản cũ. Ngược lại `nghi_phep_nam_v2023.md` **không ghi đã hết hiệu lực**; chỉ
  `v2024.md` nói "thay thế hoàn toàn phiên bản 1.0". Nếu retrieval chỉ lấy chunk v2023 (hoặc chunk v2024 không chứa câu "thay
  thế"), không có gì trong context cho biết 12 ngày là sai. Dự đoán cần kiểm chứng: câu 41/42 dễ sai hơn 43/44.
- **Chunk có nhãn phiên bản nhưng không có trạng thái hiệu lực.** m1 cắt child ~256 ký tự nên dòng
  `Phiên bản/Ngày hiệu lực` ở đầu tài liệu không nằm trong phần lớn child chunk. m5 bù lại bằng một dòng ngữ cảnh do LLM sinh
  (kiểm tra trong `.cache/enrichment_cache.json`: "Đoạn văn thuộc tài liệu chính sách nghỉ phép năm, phiên bản 2023, …"),
  nhưng dòng này chỉ ghi tên phiên bản, không ghi "đã hết hiệu lực". Prompt generation hiện tại ("Trả lời CHỈ dựa trên
  context") cũng không yêu cầu so sánh phiên bản, nên khi context có cả "phiên bản 2023" và "phiên bản 2024", việc chọn bản
  nào phụ thuộc vào LLM.
- **Phủ định nằm ở tài liệu khác.** Câu 48 hỏi về PVI nhưng điều kiện loại trừ nằm trong `thu_viec.md`; `bao_hiem_suc_khoe.md`
  chỉ nói "cho tất cả nhân viên chính thức". Nếu reranker chỉ giữ top 3 từ tài liệu PVI, answer dễ thành "có" và vẫn
  faithful với contexts → faithfulness cao nhưng sai.
- **Câu 50** là câu hỏi dẫn dắt; tài liệu có dòng cấm rõ, nên lỗi (nếu có) là generation chiều theo giả định của câu hỏi.

Đề xuất sửa cụ thể (cần chạy lại `setup_answers.py` + Phase A để đo):

1. m1 đọc dòng header `Phiên bản/Ngày hiệu lực/Trạng thái` của tài liệu, đưa `version`, `effective_date`, `superseded_by`
   vào metadata của mọi child chunk và prepend một dòng tất định "[Tài liệu: …, phiên bản …, hiệu lực từ …, trạng thái …]"
   (thay vì dựa vào dòng ngữ cảnh do LLM của m5 sinh). Với cặp nghỉ phép, `superseded_by` suy từ câu "thay thế hoàn toàn
   phiên bản 1.0" trong v2024.
2. Filter mặc định bỏ tài liệu đã bị thay thế, trừ khi câu hỏi nêu rõ phiên bản cũ (như câu 49).
3. Prompt generation: "nếu context có nhiều phiên bản, dùng phiên bản có ngày hiệu lực mới nhất và nói rõ phiên bản";
   "giữ nguyên các câu phủ định/điều kiện (KHÔNG, chỉ khi, trừ)".
4. Với câu có chủ thể đặc biệt (thử việc, Manager), mở rộng truy vấn để lấy thêm tài liệu về chủ thể đó (`thu_viec.md`).

Cách biết sửa có hiệu quả: so sánh adversarial mean và faithfulness/context_precision của 10 câu 41–50 trước/sau, đọc lại
answers của 41, 42, 46, 48; đồng thời kiểm tra factual/multi_hop không giảm.

Giới hạn: chỉ 10 câu adversarial nên một câu thay đổi làm mean nhóm đổi 0.1 × chênh lệch điểm câu đó; RAGAS dùng
gpt-4o-mini làm evaluator nên chính evaluator có thể chấm sai câu phủ định; hai PDF scan (`BCTC.pdf`, Nghị định 13) không
có text layer nên bị m1 bỏ qua, không ảnh hưởng 10 câu trên nhưng giới hạn corpus.
