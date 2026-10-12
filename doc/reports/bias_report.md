# Đánh giá LLM Judge Phase B

Nhóm: SKT

Người phụ trách: Đỗ Trung Tuyến — 2A202602427 (code Tasks 5–8, thiết kế prompt, phân tích nguồn và nhãn người);
Vũ Đình Thư — 2A202602652 (lần chạy Phase B đầu và diễn giải số liệu lần đó).

> **Trạng thái:** Phase B đã chạy live. Kết quả dưới đây lấy trực tiếp từ `artifacts/judge_results.json`;
> không có winner, nhãn hay κ nào được điền ước lượng.
>
> **Lịch sử chạy:** lần chạy đầu (`2026-10-12T05:32:33Z`) dùng bản `answers_50q.json` cũ, metadata ghi `generation: []`,
> nên checker báo "Phase B generation models must match saved answers" sau khi answers được sinh lại bằng Gemini.
> Đồng thời `source_sha256` được tính trên file CRLF (Git `core.autocrlf=true` trên Windows), sẽ lệch khi checkout LF.
> Nhóm thêm `.gitattributes` (`*.json text eol=lf`) và chạy lại Phase B trên đúng answers hiện tại; artifact hiện tại là
> lần chạy lại này. Fixtures và prompt judge giữ nguyên.

Nguồn: `artifacts/judge_results.json`; run timestamp: `2026-10-12T10:00:55.234278+00:00` (17:00:55 ICT, UTC+07:00).
Models theo `metadata.models`: generation `gemini-3.5-flash-lite` (answers A); judge `gpt-4o-mini` cho cả pairwise
(`config.JUDGE_MODEL`) và binary helper.

## Cách Task 5–8 được implement (đã xong, 8 unit tests pass)

- **Task 5 `pairwise_judge`:** một lời gọi `gpt-4o-mini`, `temperature=0`, `response_format=json_object`. System prompt nói rõ
  question/reference/answers là dữ liệu, không phải chỉ dẫn. User prompt đưa **reference** và xếp tiêu chí theo thứ tự ưu tiên:
  accuracy (đúng reference, đúng phiên bản, giữ phủ định/điều kiện; khẳng định không được hỗ trợ là lỗi nặng) → completeness →
  conciseness; dặn không ưu tiên answer dài hơn hay đứng trước, cho phép `tie`. Output được kiểm tra: winner ∈ {A, B, tie},
  reasoning không rỗng, scores A/B là số trong [0,1]; sai thì báo lỗi thay vì đoán.
- **Task 6 `swap_and_average`:** lượt 1 judge (A, B); lượt 2 judge (B, A) với cùng question/reference. Winner lượt 2 được đổi
  `A↔B` và scores lượt 2 được hoán về đúng answer gốc. Hai lượt đồng ý → final = winner đó; khác nhau → `tie` và
  `position_consistent=False`.
- **Task 7 `cohen_kappa`:** tính tay p_o (tỷ lệ trùng) và p_e = Σ_label P_judge(label)·P_human(label); kiểm tra hai list cùng
  độ dài, nhãn là int 0/1; báo lỗi khi p_e = 1 (cả hai cùng một nhãn hằng, κ không xác định) thay vì trả 0.
- **Task 8 `bias_report`:** position inconsistency = số cặp `position_consistent=False`; verbosity = số case decisive mà winner
  dài hơn / số case decisive (tie bị loại khỏi mẫu số); interpretation nêu cả hai tỷ lệ và nhắc mẫu nhỏ chỉ là dấu hiệu.

Nhãn 0/1 do helper `src.experiment_support.judge_binary` sinh (không sửa): prompt chỉ nhận `question`, `answer` (đúng
`model_answer` trong fixture) và `reference`; **không** gửi `human_label`, `human_note` hay phân bố nhãn. Winner A/B không
được đổi thành nhãn 0/1.

## Năm cặp A/B và hai lượt

Nguồn cố định: A từ artifacts/answers_50q.json:answer; B từ
fixtures/human_labels_10q.json:model_answer; reference từ fixtures/test_set_50q.json:ground_truth.
Ids: 1, 5, 12, 21, 41. Không đổi nguồn sau khi xem kết quả judge.

Candidate B (cố định, đã biết trước khi chạy) so với reference:

| ID | Câu hỏi | B = model_answer | Ý chính của reference | B so với reference |
|---|---|---|---|---|
| 1 | Nghỉ kết hôn bao nhiêu ngày? | 3 ngày làm việc có lương | 3 ngày có lương, không trừ phép năm | đúng, thiếu ý "không trừ phép năm" |
| 5 | Mua thiết bị 55 triệu ai duyệt? | Giám đốc phòng ban | >50 triệu cần CEO | sai người phê duyệt |
| 12 | Thưởng Tết tối thiểu (≥6 tháng)? | tối thiểu 1 tháng lương | 1 tháng lương; <6 tháng pro-rata | đúng phần được hỏi |
| 21 | Senior 9 năm: phép và lương? | 18 ngày; 20–35 triệu | 15+3=18 ngày (v2024); 20–35 triệu | đúng cả hai ý |
| 41 | Nghỉ bao nhiêu ngày phép năm? | 12 ngày | 15 ngày theo v2024; v2023 (12) đã bị thay | sai phiên bản (bẫy v2023) |

A (answer pipeline), winner hai lượt, scores và reasoning từ `pairwise_results`:

| ID | Pass 1 | Pass 2 (quy về A/B gốc) | Final | Nhất quán | Scores pass 1 A/B | Scores pass 2 A/B | Tóm tắt reasoning |
|---|---|---|---|---|---|---|---|
A (pipeline, Gemini) của 5 câu: 1 "3 ngày làm việc khi kết hôn" (thiếu "có lương"); 5 "Không tìm thấy."; 12 "1 tháng lương"
kèm điều kiện ≥6 tháng; 21 "Không tìm thấy."; 41 nêu cả "12 ngày" (phần đầu) "hoặc 15 ngày" (chính sách mới thay thế 1.0 năm 2023).

| ID | Pass 1 | Pass 2 (quy về A/B gốc) | Final | Nhất quán | Scores pass 1 A/B | Scores pass 2 A/B | Độ dài A/B (ký tự) | Đọc nội dung |
|---|---|---|---|---|---|---|---|---|
| 1 | B | B | **B** | Có | 0.8 / 1.0 | 0.5 / 1.0 | 48 / 57 | B có thêm "có lương" — đúng ý reference mà A thiếu; B thắng hợp lý. |
| 5 | B | A | **tie** | Không | 0.0 / 0.5 | 0.5 / 0.0 | 15 / 33 | Cả hai sai theo reference (cần CEO). Lượt 1 cho câu trả lời sai (B) điểm cao hơn "Không tìm thấy", lượt 2 ngược lại; `tie` là kết quả đúng của swap. |
| 12 | A | A | **A** | Có | 1.0 / 0.5 | 1.0 / 0.7 | 108 / 50 | A nêu điều kiện ≥6 tháng; B đúng mức nhưng không nêu điều kiện. A thắng chấp nhận được (B cũng đúng phần được hỏi). |
| 21 | B | B | **B** | Có | 0.0 / 1.0 | 0.0 / 1.0 | 15 / 82 | A "Không tìm thấy." — lỗi retrieval của pipeline; B đúng cả 18 ngày và 20–35 triệu. B thắng đúng. |
| 41 | A | A | **A** | Có | 1.0 / 0.0 | 1.0 / 0.5 | 233 / 37 | B "12 ngày" sai phiên bản. A nhắc 15 ngày và việc thay thế bản 2023 nhưng vẫn trình bày 12 ngày như một khả năng; điểm A = 1.0 là **chấm rộng tay** — A nên mất điểm vì không khẳng định bản hiện hành. |

Lưu ý khi đọc `reasoning_pass2`: lượt 2 judge thấy câu trả lời ở vị trí đảo, nên chữ "Answer A" trong reasoning lượt 2 là
answer **B gốc** (ví dụ cặp 1: "Answer A chính xác hơn vì nó bao gồm thông tin về việc nghỉ có lương"). Winner và scores
trong bảng đã được `swap_and_average` quy về A/B gốc.

Position bias count/rate: **1/5 = 20%** (`position_bias_count=1`, `position_bias_rate=0.2`), chỉ cặp 5.
Verbosity win rate: **4/4 = 100%**; decisive cases: **4** (`a_wins_a_longer=2`, `b_wins_b_longer=2`).

Đọc nội dung trước khi kết luận:

- **Position:** cặp duy nhất bất nhất (5) là cặp mà cả hai answer đều sai — một bên từ chối, một bên sai người duyệt.
  Judge không có cơ sở rõ để xếp hạng, nên đổi ý khi đổi thứ tự là dấu hiệu "hai answer tương đương kém" hơn là thiên vị vị
  trí có hệ thống. Lần chạy đầu (answers cũ) có 3/5 bất nhất, cho thấy tỷ lệ này dao động mạnh theo nội dung answer.
- **Verbosity:** cả 4 case decisive đều là bên dài hơn thắng, nhưng ở mỗi case bên dài hơn chứa đúng một ý mà reference yêu
  cầu và bên ngắn thiếu ("có lương", điều kiện ≥6 tháng, số liệu thay cho "Không tìm thấy", 15 ngày theo v2024). Không có
  case nào bên dài hơn thắng nhờ thêm chữ thừa, nên 100% ở đây phản ánh tương quan độ dài–đúng, **không chứng minh**
  verbosity bias. Muốn tách hai yếu tố cần cặp đối chứng: cùng nội dung đúng, một bản thêm câu thừa.
- **Điểm số:** cặp 41 cho thấy judge có thể thưởng câu trả lời "nêu cả hai phiên bản" bằng điểm tối đa; gate dựa trên
  pairwise score nên kèm kiểm tra riêng cho câu version conflict.

Cách diễn giải khi có số: một cặp không nhất quán chỉ cho biết judge đổi ý khi đổi thứ tự, không tự chứng minh nguyên nhân
là position bias (có thể hai answer thật sự ngang nhau). Verbosity: B trong 5 cặp đều ngắn (1–2 câu) trong khi answer RAG
thường dài hơn, nên tỷ lệ "winner dài hơn" cao có thể chỉ phản ánh A đúng hơn; phải đọc nội dung từng cặp trước khi kết luận.

## Calibration đúng model_answer

Helper đánh giá đúng question/model_answer đang có trong fixtures/human_labels_10q.json;
không lấy answer mới của pipeline. Prompt chỉ nhận question, answer, reference.
Không gửi human_label, human_note hoặc phân bố nhãn human vào prompt.

Phân tích 10 model_answer so với reference (làm trước khi chạy judge; nhãn human chỉ dùng để đối chiếu sau):

| ID | model_answer | Điểm cần đối chiếu với reference | human_label |
|---|---|---|---|
| 1 | 3 ngày làm việc có lương | thiếu "không trừ phép năm" — ý phụ hay thiết yếu? | 1 |
| 5 | Giám đốc phòng ban phê duyệt | sai: >50 triệu cần CEO | 0 |
| 12 | tối thiểu 1 tháng lương | không nhắc pro-rata <6 tháng (câu hỏi không hỏi) | 1 |
| 21 | 18 ngày; 20–35 triệu | đủ cả hai ý | 1 |
| 23 | hoàn trả 25 triệu, chưa đủ 1 năm | đúng 100% hoàn trả | 1 |
| 29 | Trưởng phòng duyệt; phạt 2%/tháng trên 8 triệu | thiếu Kế toán trưởng, không tính ra 80.000 VNĐ | 0 |
| 33 | 19 ngày; 1.500.000 VNĐ/tháng | đúng cả hai | 1 |
| 41 | 12 ngày | dùng v2023 đã hết hiệu lực | 0 |
| 46 | không được phép năm, xin nghỉ không lương | giữ đúng phủ định và hành động thay thế | 1 |
| 50 | được, miễn kết nối an toàn | sai: VPN cá nhân bị cấm | 0 |

Theo phân tích này, các ca dễ lệch với người là **1 và 12** (đúng nhưng thiếu một ý trong reference; prompt helper chấm 0 nếu
"thiếu ý thiết yếu") và **29** (một phần đúng). Đây là điểm cần đọc reasoning, không phải dự đoán nhãn của judge.

Nhãn judge, reasoning, agree từ `binary_judgments`:

| ID | Nhãn judge | Nhãn human | Agree | Tóm tắt reasoning của judge |
|---|---:|---:|---|---|
| 1 | 1 | 1 | Có | Đúng số ngày và có lương; reasoning nói answer "nêu rõ không trừ vào phép năm" — **không đúng**, model_answer không có ý này. |
| 5 | 0 | 0 | Có | Sai người phê duyệt: >50 triệu cần Tổng Giám đốc. |
| 12 | 1 | 1 | Có | Đúng điều kiện ≥6 tháng và mức 1 tháng lương. |
| 21 | 1 | 1 | Có | Đúng số ngày phép và khoảng lương Senior. |
| 23 | 1 | 1 | Có | Đúng phải hoàn trả 25 triệu khi chưa đủ cam kết 1 năm. |
| 29 | 0 | 0 | Có | Thiếu Kế toán trưởng; phí phạt tính sai (phải theo 15 ngày quá hạn, không phải 2% × 8 triệu cả tháng). |
| 33 | 1 | 1 | Có | Đúng số ngày phép và tổng phụ cấp. |
| 41 | 0 | 0 | Có | Dùng chính sách v2023; v2024 quy định 15 ngày. |
| 46 | 1 | 1 | Có | Đúng: thử việc không có phép năm, phải xin nghỉ không lương. |
| 50 | 0 | 0 | Có | VPN cá nhân bị cấm theo chính sách. |

Cohen’s κ: **1.000** (`calibration.cohen_kappa`). Judge trùng cả 10/10 nhãn human: `p_o=1.000`,
`p_e=0.6×0.6 + 0.4×0.4 = 0.520`, nên `κ=(1.000-0.520)/(1-0.520)=1.000`. Nhãn judge giống hệt ở cả hai lần chạy
(05:32Z và 10:00Z), vì helper chấm đúng `model_answer` cố định, không phụ thuộc answers của pipeline.

κ = 1 không có nghĩa reasoning của judge luôn đúng: ở câu 1, nhãn đúng nhưng lý do viện dẫn một ý không có trong answer.
Nếu dùng reasoning để giải thích cho người dùng hoặc reviewer, cần kiểm tra lý do có bám answer không, không chỉ nhãn.

Observed/chance agreement: p_o = số nhãn trùng / 10; p_e = P_judge(1)·0.6 + P_judge(0)·0.4 (human có 6 nhãn 1, 4 nhãn 0).
Độ nhạy của κ với bộ nhãn này (tính bằng `cohen_kappa` trên nhãn giả định lật từ nhãn human, **không phải kết quả judge**):

| Số nhãn judge lệch human | κ |
|---|---|
| 0 | 1.000 |
| 1 (human 1 → judge 0) | 0.800 |
| 1 (human 0 → judge 1) | 0.783 |
| 2 cùng chiều 1 → 0 | 0.615 |
| 2 ngược chiều | 0.583 |
| 2 cùng chiều 0 → 1 | 0.545 |
| 3 | 0.286–0.444 |

Nghĩa là ngưỡng bonus κ > 0.6 chỉ chắc chắn đạt khi judge lệch tối đa 1/10 nhãn; lệch 2 nhãn thì đạt hay không tùy chiều lệch.

## Giới hạn và cách dùng judge

- Mẫu rất nhỏ: 5 cặp pairwise và 10 nhãn; mỗi nhãn lệch làm κ giảm khoảng 0.2, nên κ chỉ là chỉ báo thô, không đủ để tin judge
  tuyệt đối. Position/verbosity rate trên 5 cặp chỉ là dấu hiệu.
- Generation của A là `gemini-3.5-flash-lite`, judge là `gpt-4o-mini` (khác họ model) nên self-preference với A ít khả năng;
  nguồn sinh `model_answer` của B không được fixture nêu, nên không loại trừ judge ưu ái B nếu B do họ GPT sinh.
- Hai trong năm answer A là "Không tìm thấy." (5, 21) nên phép so pairwise phần lớn đo chất lượng retrieval của pipeline,
  không đo khả năng phân biệt tinh của judge.
- Prompt nhị phân của helper khắt khe với "thiếu ý thiết yếu"; ranh giới ý thiết yếu/phụ (ca 1, 12) là chủ quan, người và
  judge có thể khác nhau hợp lý.
- Cách dùng đề xuất: judge làm bộ lọc sơ bộ cho CI (luôn swap-and-average, `tie` khi bất đồng), các ca lệch hoặc `tie` gửi
  người review; định kỳ thêm nhãn người để đo lại κ trên mẫu lớn hơn (≥50).
- Nếu κ thật ≤ 0.6: đọc các ca lệch, xem lệch do ranh giới "ý thiết yếu" hay do judge sai sự thật, rồi mới quyết định chỉnh
  prompt; không chỉnh prompt dựa trên chính 10 nhãn này rồi báo κ trên cùng bộ đó như kết quả độc lập.
