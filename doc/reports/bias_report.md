# Đánh giá LLM Judge Phase B

Nhóm: SKT

Người phụ trách: Đỗ Trung Tuyến — 2A202602427 (code Tasks 5–8, thiết kế prompt, phân tích nguồn và nhãn người); kết quả chạy
và diễn giải số liệu do thành viên chạy Phase B bổ sung.

> **Trạng thái tại commit này:** Phase B **chưa chạy**. Runner cần `artifacts/answers_50q.json` (nguồn của answer A) nên phải
> chờ setup. Mục ghi "CHỜ KẾT QUẢ" phải điền từ `artifacts/judge_results.json`; không điền winner/nhãn/κ ước lượng.

Nguồn: `artifacts/judge_results.json`; run timestamp: CHỜ KẾT QUẢ (lấy `metadata.created_at`).
Models generation/judge: dự kiến generation `gpt-4o-mini`; judge `gpt-4o-mini` cho cả pairwise (`config.JUDGE_MODEL`) và
binary helper. Ghi lại đúng theo `metadata.models` sau khi chạy.

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

A (answer pipeline), winner hai lượt, scores, reasoning: CHỜ KẾT QUẢ — điền 5 rows từ `pairwise_results`
(id, winner_pass1, winner_pass2 đã quy về A/B gốc, final_winner, position_consistent, scores hai lượt, tóm tắt reasoning).
Khi đọc kết quả, cặp 5 và 41 là phép thử rõ nhất: B sai theo reference, nên nếu A đúng mà judge vẫn chọn B hoặc tie thì cần
đọc reasoning. Cặp 1, 12, 21 có B đúng, nên `tie` hoặc chọn bản ngắn gọn hơn đều có thể hợp lý.

Position bias count/rate: CHỜ KẾT QUẢ (`bias_report.position_bias_count`/`position_bias_rate`).
Verbosity win rate: CHỜ KẾT QUẢ; decisive cases: CHỜ KẾT QUẢ.

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

Nhãn judge, reasoning, agree: CHỜ KẾT QUẢ — điền 10 rows theo đúng thứ tự `binary_judgments`.
Cohen’s κ: CHỜ KẾT QUẢ (`calibration.cohen_kappa`).

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
