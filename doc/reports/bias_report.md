# Đánh giá LLM Judge Phase B

Nhóm: SKT

Người phụ trách: Đỗ Trung Tuyến — 2A202602427 (code Tasks 5–8, thiết kế prompt, phân tích nguồn và nhãn người); kết quả chạy
và diễn giải số liệu do thành viên chạy Phase B bổ sung.

> **Trạng thái:** Phase B đã chạy live thành công. Kết quả dưới đây lấy trực tiếp từ
> `artifacts/judge_results.json`; không có winner, nhãn hay κ nào được điền ước lượng.

Nguồn: `artifacts/judge_results.json`; run timestamp: `2026-10-12T05:32:33.849528+00:00`
(12:32:33 ICT, UTC+07:00). Metadata không khai báo model generation (mảng `generation` rỗng); model judge thực tế là
`gpt-4o-mini` cho cả pairwise (`config.JUDGE_MODEL`) và binary helper.

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
| 1 | A | A | A | Có | 1.0 / 0.8 | 1.0 / 0.7 | Cả hai lượt ưu tiên A vì đầy đủ hơn về nghỉ phép đặc biệt; B vẫn đúng số ngày kết hôn. |
| 5 | B | A | tie | Không | 0.3 / 0.5 | 0.7 / 0.0 | Cả A và B đều không nêu CEO theo reference; judge đổi lựa chọn khi đảo thứ tự nên giữ `tie`. |
| 12 | A | A | A | Có | 1.0 / 0.5 | 1.0 / 0.7 | A bổ sung điều kiện ≥6 tháng và pro-rata dưới 6 tháng; B đúng mức tối thiểu nhưng ngắn hơn. |
| 21 | tie | B | tie | Không | 1.0 / 1.0 | 0.8 / 1.0 | Lượt đầu xem hai đáp án tương đương; lượt đảo vị trí nghiêng về B nên kết quả cuối là `tie`. |
| 41 | B | A | tie | Không | 0.0 / 0.0 | 1.0 / 0.0 | Cả hai dùng 12 ngày theo v2023, trái reference v2024 là 15 ngày; judge đổi lựa chọn khi đảo vị trí. |

Khi đọc kết quả, cặp 5 và 41 là phép thử rõ nhất: B sai theo reference, nên nếu A đúng mà judge vẫn chọn B hoặc tie thì cần
đọc reasoning. Cặp 1, 12, 21 có B đúng, nên `tie` hoặc chọn bản ngắn gọn hơn đều có thể hợp lý.

Position bias count/rate: **3/5 = 60%** (`position_bias_count=3`, `position_bias_rate=0.6`).
Verbosity win rate: **2/2 = 100%**; decisive cases: **2**. Cả hai decisive cases đều là A thắng và A dài hơn
(`a_wins_a_longer=2`, `b_wins_b_longer=0`).

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
| 1 | 1 | 1 | Có | Đúng số ngày nghỉ kết hôn và có lương. |
| 5 | 0 | 0 | Có | Sai người phê duyệt: phải là Tổng Giám đốc. |
| 12 | 1 | 1 | Có | Đúng điều kiện nhân viên chính thức từ 6 tháng và mức 1 tháng lương. |
| 21 | 1 | 1 | Có | Đúng cả số ngày phép lẫn khoảng lương Senior. |
| 23 | 1 | 1 | Có | Đúng phải hoàn trả 25 triệu khi chưa đủ cam kết 1 năm. |
| 29 | 0 | 0 | Có | Thiếu Kế toán trưởng và tính phí phạt chưa đúng. |
| 33 | 1 | 1 | Có | Đúng số ngày phép và tổng phụ cấp. |
| 41 | 0 | 0 | Có | Dùng chính sách v2023; v2024 quy định 15 ngày phép. |
| 46 | 1 | 1 | Có | Đúng không có phép năm khi thử việc và phải xin nghỉ không lương. |
| 50 | 0 | 0 | Có | VPN cá nhân bị cấm theo reference. |

Cohen’s κ: **1.000** (`calibration.cohen_kappa`). Judge trùng cả 10/10 nhãn human: `p_o=1.000`,
`p_e=0.6×0.6 + 0.4×0.4 = 0.520`, nên `κ=(1.000-0.520)/(1-0.520)=1.000`.

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
- Judge và generation cùng là `gpt-4o-mini`, có thể ưu ái văn phong của chính model đó (self-preference) khi so A (pipeline)
  với B; muốn kiểm tra cần thêm một judge khác họ model.
- Prompt nhị phân của helper khắt khe với "thiếu ý thiết yếu"; ranh giới ý thiết yếu/phụ (ca 1, 12) là chủ quan, người và
  judge có thể khác nhau hợp lý.
- Cách dùng đề xuất: judge làm bộ lọc sơ bộ cho CI (luôn swap-and-average, `tie` khi bất đồng), các ca lệch hoặc `tie` gửi
  người review; định kỳ thêm nhãn người để đo lại κ trên mẫu lớn hơn (≥50).
- Nếu κ thật ≤ 0.6: đọc các ca lệch, xem lệch do ranh giới "ý thiết yếu" hay do judge sai sự thật, rồi mới quyết định chỉnh
  prompt; không chỉnh prompt dựa trên chính 10 nhãn này rồi báo κ trên cùng bộ đó như kết quả độc lập.
