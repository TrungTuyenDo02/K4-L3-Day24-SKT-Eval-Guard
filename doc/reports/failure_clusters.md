# Phân tích lỗi Phase A

Nhóm: SKT

Người phụ trách: Đỗ Trung Tuyến — 2A202602427 (code Tasks 1–4, sửa adapter m4, chạy Phase A, phân tích bottom 10 và bẫy);
answers do Đỗ Trịnh Huy Hoàng — 2A202602392 sinh.

Nguồn: `artifacts/ragas_50q.json`; run timestamp: `2026-10-12T10:12:21.484496+00:00` (17:12:21 ICT, UTC+07:00).
Generation mode/fallback: 50/50 câu `generation_mode=llm`, `generation_model=gemini-3.5-flash-lite`; 0 câu
`extractive_fallback`. Answers sinh bởi `scripts/setup_answers.py --live` (hybrid BM25 + BGE-M3/Qdrant → bge-reranker-v2-m3
top 3 → Gemini), system prompt "Trả lời CHỈ dựa trên context. Nếu không có → nói 'Không tìm thấy.'".
Models theo `metadata.models`: generation `gemini-3.5-flash-lite`; evaluator `gpt-4o-mini` + `text-embedding-3-small`
(do m4 báo, không dùng JUDGE_MODEL thay).

## Cách Task 1–4 được implement (6 unit tests pass)

- **Task 1 `group_by_distribution`:** chia theo trường `distribution`, báo lỗi nếu gặp distribution lạ; test xác nhận 20/20/10.
- **Task 2 `run_ragas_50q`:** gọi `m4_eval.evaluate_ragas` một lần cho 50 câu, kiểm tra m4 trả đúng 50 dòng, chuyển từng metric
  sang `float` và từ chối giá trị NaN/ngoài [0,1] (không thay bằng 0). `evaluator_models` lấy từ `raw["metadata"]`; thiếu
  thì báo lỗi, không dùng `JUDGE_MODEL` thay. Adapter m4 chấm lại tối đa 2 lượt riêng các câu RAGAS trả NaN.
- **Task 3 `bottom_10`:** sắp tăng dần `avg_score`, lấy tối đa 10 câu, kèm rank, worst_metric, diagnosis/suggested_fix từ
  `DIAGNOSTIC_TREE`.
- **Task 4 `cluster_analysis`:** matrix đếm worst_metric của **mọi** câu (tổng cột 20/20/10 chỉ là kích thước nhóm);
  nhóm yếu = distribution có mean `avg_score` thấp nhất, nhóm rỗng bị bỏ khỏi phép chia; insight nêu xếp hạng mean,
  metric chủ đạo và số câu của nó trong nhóm yếu.

**Sửa adapter m4 trước khi có artifact (ghi lại để người chấm biết vì sao số liệu chạy được):** hai lần chạy đầu dừng vì
faithfulness NaN không hết sau 2 lượt chấm lại (lần 1: câu 18; lần 2: câu 18, 46; chạy debug: câu 19). Truy vết câu 19
(`- Thời gian thử việc tiêu chuẩn là: **60 ngày**`): faithfulness của ragas 0.1.22 chỉ giữ câu **kết thúc bằng "."**
(`_create_statements_prompt`), answer dạng gạch đầu dòng không có dấu chấm nên danh sách câu rỗng → LLM trả `[]` → không có
statement → NaN; lỗi tất định nên retry không cứu được. `src/m4_eval.py` thêm `_LineSentenceSegmenter` cho faithfulness: tách
theo dòng, bỏ `**`/gạch đầu dòng, thêm "." cho câu thiếu dấu kết câu, bỏ dòng dẫn kết thúc bằng ":". Answer gốc vẫn vào
prompt nguyên văn; segmenter áp dụng **đồng loạt cho cả 50 câu**, không riêng câu lỗi. Không đổi NaN thành 0. Lần chạy dùng
cho artifact vẫn còn 1 câu NaN ở lượt đầu và hết sau 1 lượt chấm lại.

## Điểm theo distribution

| Distribution | n | faithfulness | answer_relevancy | context_precision | context_recall | avg_score |
|---|---:|---:|---:|---:|---:|---:|
| factual | 20 | 0.933 | 0.479 | 0.929 | 0.900 | **0.810** |
| multi_hop | 20 | 0.665 | 0.377 | 0.975 | 0.779 | **0.699** |
| adversarial | 10 | 0.717 | 0.445 | 0.967 | 0.650 | **0.695** |

Đọc nhanh: context_precision cao đều (0.93–0.98), nghĩa là reranker ít đưa chunk lạc đề; điểm thấp đến từ faithfulness
(multi_hop/adversarial) và context_recall (adversarial). answer_relevancy thấp **ở mọi nhóm**, kể cả câu trả lời đúng
(câu 18 đúng hoàn toàn: 0.376; câu 3 "1.000.000 VNĐ/tháng.": 0.410). Metric này sinh câu hỏi ngược từ answer rồi so embedding
với câu hỏi gốc, nên answer tiếng Việt ngắn (chỉ một con số) bị điểm thấp có hệ thống; vì vậy nó không phải tín hiệu lỗi chính.

## Bottom 10 và nguyên nhân

Điểm theo thứ tự faithfulness / answer_relevancy / context_precision / context_recall. Diagnosis/fix là cột tự động từ
`DIAGNOSTIC_TREE`; cột "Đọc answer/contexts" là phân loại sau khi đọc `answer`, `contexts`, `ground_truth` trong `per_question`.

| Rank | ID | Distribution | avg | F / AR / CP / CR | worst_metric → diagnosis (tự động) | Đọc answer/contexts | Loại lỗi thật |
|---|---|---|---:|---|---|---|---|
| 1 | 5 | factual | 0.146 | 0.00 / 0.00 / 0.58 / 0.00 | faithfulness → LLM hallucinating | Answer "Không tìm thấy.". Chunk bảng thẩm quyền chỉ có 2 dòng đầu (<5 triệu, 5–50 triệu); dòng ">50 triệu → CEO" nằm ở chunk khác không được lấy. Từ chối là **đúng** với contexts. | Retrieval (recall) — bảng bị cắt giữa chừng |
| 2 | 39 | multi_hop | 0.250 | 0.00 / 0.00 / 1.00 / 0.00 | faithfulness → LLM hallucinating | Cả 3 contexts là tiêu đề/ghi chú phiên bản ("ĐÃ THAY THẾ bởi v2.0", "Văn bản này thay thế…"), không có con số 8/12 ký tự, 90/120 ngày, MFA. | Retrieval (recall) — chunk metadata chiếm hết top 3 |
| 3 | 50 | adversarial | 0.333 | 0.00 / 0.00 / 1.00 / 0.33 | faithfulness → LLM hallucinating | Context 1 có nguyên văn "Không sử dụng VPN cá nhân (NordVPN, ExpressVPN)" nhưng answer "Không tìm thấy.". | Generation — từ chối dù đủ căn cứ |
| 4 | 21 | multi_hop | 0.333 | 0.00 / 0.00 / 0.83 / 0.50 | faithfulness → LLM hallucinating | Contexts có quy tắc thâm niên (+1/3 năm, ví dụ 9 năm) và 12 ngày v2023; thiếu 15 ngày v2024 và khung lương Senior. Answer "Không tìm thấy." thay vì trả lời phần có căn cứ. | Cả hai — recall thiếu + generation không trả lời một phần |
| 5 | 33 | multi_hop | 0.375 | 0.00 / 0.00 / 1.00 / 0.50 | faithfulness → LLM hallucinating | Contexts có 15 ngày v2024 + quy tắc thâm niên (đủ tính 19 ngày); thiếu phụ cấp ăn trưa/điện thoại. Answer "Không tìm thấy.". | Cả hai — như câu 21 |
| 6 | 46 | adversarial | 0.417 | 0.00 / 0.00 / 1.00 / 0.67 | faithfulness → LLM hallucinating | Context 1: "Nhân viên thử việc **KHÔNG được nghỉ phép năm** … phải xin nghỉ không lương". Answer "Không tìm thấy.". | Generation — bỏ lỡ câu phủ định có sẵn |
| 7 | 24 | multi_hop | 0.500 | 0.00 / 0.00 / 1.00 / 1.00 | faithfulness → LLM hallucinating | Contexts đủ cả 3 dữ kiện (hạn 15 ngày, phạt 2%/tháng, số tiền); câu hỏi cần tính 2% × 15tr × 5/30 ≈ 50.000 VNĐ. Answer "Không tìm thấy.". | Generation — không suy luận/tính toán |
| 8 | 44 | adversarial | 0.500 | 0.50 / 0.00 / 0.83 / 0.67 | answer_relevancy → Answer doesn't match question | Contexts có "mỗi 120 ngày" (v2.0), "mỗi 90 ngày" (v1.0) và ghi chú "đã được thay thế bởi v2.0". Answer: "120 ngày (hoặc **90 ngày theo chính sách mới**)" — gán nhầm bản cũ là bản mới. | Generation — version conflict |
| 9 | 30 | multi_hop | 0.625 | 1.00 / 0.00 / 1.00 / 0.50 | answer_relevancy → Answer doesn't match question | Có chunk thử việc (BHXH, chưa có PVI) nhưng không có chunk PVI 200 triệu/năm cho nhân viên chính thức; 1/3 context là tiêu đề trống "## Quyền lợi trong thử việc". Answer nói đúng là context thiếu. | Retrieval (recall) — thiếu tài liệu thứ hai |
| 10 | 34 | multi_hop | 0.659 | 0.57 / 0.40 / 1.00 / 0.67 | answer_relevancy → Answer doesn't match question | Answer đúng cả hai mức phê duyệt so với reference, chỉ thiếu ý "hạn hoàn ứng 15 ngày"; 1/3 context là tiêu đề trống "## Quy trình phê duyệt". Faithfulness 0.57 là evaluator chấm chặt câu "cần trưởng phòng phê duyệt và thêm Kế toán trưởng". | Nhẹ — evaluator chặt + thiếu một ý phụ |

Tổng hợp 10 câu:

- **7/10 câu là "Không tìm thấy."** (5, 21, 24, 33, 39, 46, 50) — đó cũng là **toàn bộ** 7 câu "Không tìm thấy." trong 50 câu.
  RAGAS cho các câu này faithfulness = 0 và answer_relevancy = 0, nên nhãn tự động "LLM hallucinating" **sai bản chất**:
  không có câu nào bịa thông tin. Trong 7 câu, 2 câu là lỗi retrieval thật (5, 39: context_recall = 0, từ chối là hợp lý),
  3 câu là lỗi generation thuần (24, 46, 50: context đã chứa đáp án hoặc đủ dữ kiện để tính), 2 câu lẫn cả hai (21, 33).
- **Retrieval:** 5 và 39 cho thấy hai lỗi chunking cụ thể: bảng Markdown bị cắt khiến dòng cuối tách khỏi header, và các
  chunk chỉ có tiêu đề/metadata phiên bản chiếm suất trong top 3 (39; tương tự tiêu đề trống ở 30, 34). Chunk tiêu đề có
  embedding gần câu hỏi nhưng không mang dữ kiện.
- **Generation:** prompt "Nếu không có → nói 'Không tìm thấy.'" là tất-cả-hoặc-không. Gemini flash-lite từ chối khi context thiếu
  một phần (21, 33) hoặc khi phải tính toán (24), và cả khi đáp án nằm trong một câu phủ định (46, 50).
- Bỏ 7 câu "Không tìm thấy." thì avg_score còn factual 0.845 (n=19), multi_hop 0.783 (n=16), adversarial 0.774 (n=8): phần lớn
  khoảng cách giữa các nhóm đến từ việc từ chối, chủ yếu ở multi_hop (4 câu).

## Matrix và nhóm yếu nhất

Matrix worst_metric × distribution (`failure_clusters.matrix`, đếm mọi câu; tổng cột 20/20/10 chỉ là kích thước nhóm):

| worst_metric | factual | multi_hop | adversarial | Tổng |
|---|---:|---:|---:|---:|
| faithfulness | 2 | 6 | 2 | 10 |
| answer_relevancy | 17 | 13 | 5 | 35 |
| context_precision | 1 | 0 | 0 | 1 |
| context_recall | 0 | 1 | 3 | 4 |
| **Tổng** | 20 | 20 | 10 | 50 |

Nhóm yếu nhất theo mean avg_score (`distribution_avg_scores`): **adversarial 0.695** < multi_hop 0.699 < factual 0.810.
Metric chủ đạo của nhóm này theo artifact là answer_relevancy (5/10 câu). Lưu ý khi đọc:

- Adversarial chỉ thấp hơn multi_hop **0.005**. Với 10 câu, một câu đổi 0.05 điểm là đủ đảo thứ tự, nên "adversarial yếu
  nhất" chỉ đúng với lần chạy này. Khoảng cách chắc chắn là cả hai nhóm khó đều thấp hơn factual khoảng 0.11.
- answer_relevancy là worst_metric của 35/50 câu vì thang của nó thấp hơn ba metric còn lại (xem mục trên), không phải vì
  35 câu lạc đề. Đọc theo nội dung, lỗi chủ đạo của adversarial là **context_recall** (3/10 câu, mean 0.65 — thấp nhất trong
  mọi cặp metric × nhóm) và **trả lời sai/không chọn phiên bản**; của multi_hop là **faithfulness** (6/20 câu, mean 0.665, do
  4 câu "Không tìm thấy.").

## Bẫy adversarial (bonus: adversarial mean < factual mean)

Adversarial mean **0.695 < factual 0.810** (chênh 0.115). Phân tích bên dưới chỉ ra điểm thấp đến từ đâu, và vì sao **RAGAS
đánh giá thấp mức độ sai thật** của nhóm này.

Bảng dự đoán (viết từ `fixtures/test_set_50q.json` và corpus `data/` trước khi có điểm), đối chiếu với answer thực tế:

| ID | Loại bẫy | Đáp án đúng | Answer pipeline (tóm tắt) | Mắc bẫy? | F / AR / CP / CR | avg |
|---|---|---|---|---|---|---:|
| 41 | Version conflict | 15 ngày theo v2024 | "12 ngày … hoặc 15 ngày (chính sách mới thay thế bản 2023)" | **Một phần** — không khẳng định bản hiện hành | 1.00 / 0.84 / 1.00 / 0.67 | 0.877 |
| 42 | Version conflict | từ 3 năm, +1/3 năm | "từ 5 năm trở lên (hoặc từ 3 năm trở lên)" | **Một phần** — nêu bản cũ trước | 1.00 / 0.76 / 1.00 / 0.67 | 0.858 |
| 43 | Version conflict | tối thiểu 12 ký tự | "Yêu cầu thứ nhất: 12 ký tự; yêu cầu thứ hai: 8 ký tự" | **Một phần** — không nói bản nào hiệu lực | 1.00 / 0.53 / 1.00 / 0.67 | 0.798 |
| 44 | Version conflict | mỗi 120 ngày | "120 ngày (hoặc 90 ngày theo chính sách mới)" | **Có** — gán nhầm 90 ngày là bản mới | 0.50 / 0.00 / 0.83 / 0.67 | 0.500 |
| 45 | Version conflict | MFA bắt buộc | "Có, bắt buộc MFA cho email, VPN, hệ thống nội bộ" | Không | 1.00 / 0.59 / 1.00 / 0.50 | 0.772 |
| 46 | Phủ định | KHÔNG được phép năm, xin nghỉ không lương | "Không tìm thấy." (context có câu phủ định) | **Có** — bỏ lỡ phủ định | 0.00 / 0.00 / 1.00 / 0.67 | 0.417 |
| 47 | Phủ định | KHÔNG tự xử lý, báo CNTT | "Không. Tuyệt đối không tự ý xử lý malware…" | Không | 1.00 / 0.71 / 0.83 / 1.00 | 0.885 |
| 48 | Phủ định ngầm | KHÔNG có PVI, chỉ BHXH | "Không. Nhân viên thử việc chưa được hưởng gói PVI." | Không | 1.00 / 0.61 / 1.00 / 0.67 | 0.818 |
| 49 | Version (hỏi cả hai) | v2023 12 ngày (hết hiệu lực); v2024 15 ngày | Nêu đúng cả hai, ghi rõ bản 2024 thay thế hoàn toàn | Không | 0.67 / 0.42 / 1.00 / 0.67 | 0.688 |
| 50 | Mâu thuẫn chính sách | KHÔNG dùng VPN cá nhân | "Không tìm thấy." (context có dòng cấm) | **Có** — không dám bác bỏ giả định | 0.00 / 0.00 / 1.00 / 0.33 | 0.333 |

Kết luận về bẫy:

- **Version conflict là bẫy hiệu quả nhất:** 4/5 câu (41–44) mắc toàn phần hoặc một phần. Retrieval lấy **cả hai phiên bản**
  vào top 3 (context_precision 1.0, vì cả hai chunk đều "liên quan"), và LLM liệt kê cả hai, có lúc gán sai nhãn (44). Chỉ câu
  45 thoát, vì v1.0 không nhắc MFA nên không có mâu thuẫn trực tiếp.
- **RAGAS không bắt được version conflict:** 41, 42, 43 có faithfulness 1.0 và avg 0.80–0.88 (cao hơn factual mean), dù
  người dùng không biết nên theo 12 hay 15 ngày. Faithfulness chỉ kiểm tra answer có bám context, mà context chứa cả bản
  cũ. Vì vậy mean adversarial 0.695 vẫn **đánh giá cao hơn thực tế**; nếu chấm theo reference, chỉ 45, 47, 48, 49 đúng hoàn toàn (4/10).
- **Phủ định:** retrieval làm tốt (46, 48 đều lấy được `thu_viec.md`, 47 có recall 1.0). Pipeline trả đúng khi câu hỏi là
  yes/no rõ ràng (47, 48), nhưng **từ chối** ở 46 và 50, nơi đáp án là một câu "KHÔNG …" bác bỏ giả định của câu hỏi.
  Đây là lỗi generation chứ không phải hallucination: model không bịa "được nghỉ 15 ngày", nhưng cũng không trả lời.
- **Dự đoán trước khi chạy không đúng hoàn toàn:** nhóm dự đoán 41/42 (cặp nghỉ phép, v2023 không ghi "hết hiệu lực") dễ sai
  hơn 43/44 (cặp mật khẩu, v1.0 ghi "ĐÃ THAY THẾ"). Thực tế 44 sai nặng nhất. Chunk "Chu kỳ thay đổi … 90 ngày" của v1.0 không
  mang dòng trạng thái, còn chunk "Lưu ý: đã được thay thế" có trong context nhưng LLM không nối nó với chunk 90 ngày. Nhãn
  trạng thái ở **đầu tài liệu** không đủ; nó phải đi theo **từng chunk**.

Quan sát từ corpus (viết trước khi chạy, vẫn đúng sau khi đối chiếu):

- `nghi_phep_nam_v2023.md` **không ghi đã hết hiệu lực**, chỉ `v2024.md` nói "thay thế hoàn toàn phiên bản 1.0".
- m1 cắt child ~256 ký tự nên dòng `Phiên bản/Ngày hiệu lực` ở đầu tài liệu không nằm trong phần lớn child chunk. Dòng ngữ
  cảnh do m5 sinh chỉ ghi tên phiên bản, không ghi trạng thái hiệu lực.
- Prompt generation không yêu cầu so sánh phiên bản, và cho phép từ chối toàn bộ khi thiếu một phần.

## Đề xuất sửa cụ thể

Xếp theo số câu bottom 10 mỗi đề xuất nhắm tới:

1. **Prompt generation (24, 46, 50; một phần 21, 33):** thay "Nếu không có → nói 'Không tìm thấy.'" bằng: "Trả lời phần có căn
   cứ trong context và nói rõ phần nào không có. Được tính toán từ số liệu trong context. Nếu context có quy định phủ định
   (KHÔNG, cấm, chỉ khi) liên quan, trả lời bằng quy định đó. Chỉ nói 'Không tìm thấy' khi context không có dữ kiện nào liên
   quan." Kiểm tra: số câu "Không tìm thấy." giảm từ 7/50; 5 và 39 (thiếu context thật) vẫn phải từ chối hoặc trả lời một phần,
   không bịa.
2. **Phiên bản trong từng chunk (41–44):** m1 đọc header `Phiên bản/Ngày hiệu lực/Trạng thái`, ghi `version`, `effective_date`,
   `superseded_by` vào metadata **mọi** child chunk và prepend một dòng tất định "[Chính sách mật khẩu v1.0 — ĐÃ THAY THẾ bởi
   v2.0 từ 01/07/2024]". Với cặp nghỉ phép, `superseded_by` suy từ câu "thay thế hoàn toàn phiên bản 1.0" trong v2024. Mặc
   định filter bỏ chunk đã bị thay thế, trừ khi câu hỏi nêu rõ phiên bản cũ hoặc đòi so sánh (39, 49). Prompt: "Nếu context có
   nhiều phiên bản, trả lời theo bản đang hiệu lực và ghi tên phiên bản."
3. **Chunking bảng và tiêu đề (5, 39, 30, 34):** không cắt bảng Markdown giữa các dòng (giữ cả bảng hoặc lặp header cho mỗi phần);
   gộp chunk chỉ có tiêu đề/metadata (< ~60 ký tự hoặc chỉ một dòng `#`) vào chunk nội dung kế tiếp để chúng không chiếm suất
   top 3.
4. **Câu multi-hop/so sánh (21, 30, 33, 39):** tăng top_k sau rerank từ 3 lên 5 cho câu có nhiều mệnh đề hoặc chữ "so sánh",
   hoặc tách truy vấn theo từng ý (phép năm / lương / phụ cấp) rồi gộp contexts; đo bằng context_recall của multi_hop (hiện 0.779).

Cách biết sửa có hiệu quả: chạy lại `setup_answers.py --live` rồi Phase A. So sánh trước/sau: số câu "Không tìm thấy.";
faithfulness multi_hop (0.665); context_recall adversarial (0.65); **và đọc tay** 41–44, vì RAGAS không phạt được câu trả lời nêu
cả hai phiên bản. Đồng thời kiểm tra factual (0.810) không giảm.

## Giới hạn

- Mỗi nhóm nhỏ (10 câu adversarial): một câu đổi điểm làm mean nhóm đổi 0.1 × chênh lệch. Adversarial và multi_hop chỉ cách
  nhau 0.005.
- Evaluator `gpt-4o-mini` không ổn định tuyệt đối: lần chạy debug cho câu 46 context_precision 0.83 và 1.0 ở hai lượt liên tiếp.
  Mức chênh dưới ~0.05 giữa hai lần chạy không nên coi là cải thiện.
- answer_relevancy bị lệch thấp với answer tiếng Việt ngắn; không nên dùng nó làm gate đơn lẻ.
- Segmenter của adapter m4 thay đổi cách faithfulness tách câu so với ragas mặc định, nên điểm faithfulness không so trực tiếp
  được với lần chạy dùng segmenter gốc (lần chạy đó cũng không hoàn thành được vì NaN).
- Hai PDF scan (`BCTC.pdf`, Nghị định 13) không có text layer nên m1 bỏ qua; không ảnh hưởng 10 câu adversarial nhưng giới hạn corpus.
