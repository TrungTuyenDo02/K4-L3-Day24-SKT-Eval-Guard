# Đánh giá LLM Judge Phase B

Nhóm: SKT

Người phụ trách code và tích hợp: Đỗ Trung Tuyến — 2A202602427. Thực nghiệm Phase B: Vũ Đình Thư — 2A202602652.

Nguồn số liệu: artifacts/judge_results.json; answers A từ artifacts/answers_50q.json. Thời điểm: 2026-10-12 18:27:10 ICT. Answers A trong artifact hiện tại được sinh bằng gpt-4o-mini-2024-07-18; judge là gpt-4o-mini. Đây không phải bản Gemini/fallback được mô tả trong một số ghi chú cũ.

Lưu ý provenance: commit 150cff2 có 50 answers fallback; HEAD hiện tại là bb86e4b với answers Gemini/LLM được ghi lần cuối ở e51a24e. Working tree hiện có một bộ answers mới khác nữa. Pairwise và calibration dưới đây lấy đúng answers/artifact trong working tree hiện tại; chúng không phải đánh giá trên bộ fallback của commit 150cff2.

## Cách Task 5–8 được implement

- Task 5 pairwise_judge: đưa question, reference và hai answers vào prompt; ưu tiên accuracy, completeness, conciseness; temperature=0, JSON response; kiểm tra winner/reasoning/scores.
- Task 6 swap_and_average: chạy lại khi đảo vị trí A/B, quy kết quả pass 2 về answer gốc; nếu hai lượt bất đồng thì final_winner=tie.
- Task 7 cohen_kappa: tính Cohen’s κ trên nhãn judge nhị phân và human, kiểm tra đầu vào và trường hợp κ không xác định.
- Task 8 bias_report: tính position inconsistency; tính verbosity chỉ trên các cặp decisive, không tính tie.
- Binary helper chỉ nhận question, answer và reference; không đưa human_label/human_note vào prompt. Winner A/B của pairwise không phải nhãn đúng/sai 1/0.

## Năm cặp pairwise

B là câu trả lời cố định trong fixture; A là answer pipeline hiện tại. Bảng kết quả lấy từ pairwise_results, scores pass 2 đã quy về A/B gốc.

| ID | A — pipeline | B — fixture | Pass 1 | Pass 2 | Kết quả | Scores A/B pass 1 → pass 2 | Nhận xét |
|---:|---|---|---|---|---|---|---|
| 1 | 3 ngày làm việc khi kết hôn | 3 ngày làm việc có lương | B | B | B | 0.75/1.00 → 0.80/1.00 | B bổ sung điều kiện nghỉ có lương. |
| 5 | Cần Tổng Giám đốc (CEO) | Cần Giám đốc phòng ban | A | A | A | 1.00/0.00 → 1.00/0.00 | A khớp reference; B sai người phê duyệt. |
| 12 | Thưởng Tết tối thiểu 1 tháng lương cho nhân viên chính thức đủ 6 tháng | Tối thiểu 1 tháng lương | A | tie | tie | 1.00/0.50 → 1.00/1.00 | Hai lượt không nhất quán; nội dung gần nhau, khác mức độ nêu điều kiện. |
| 21 | Answer dài: 18 ngày theo phép tính 12+6; không tìm thấy lương | 18 ngày theo 15+3; lương Senior 20–35 triệu | B | B | B | 0.60/1.00 → 0.50/1.00 | B có breakdown đúng theo v2024 và trả lời phần lương; A dùng sai breakdown, thiếu dữ kiện lương. |
| 41 | 15 ngày phép năm | 12 ngày phép năm | A | A | A | 1.00/0.00 → 1.00/0.00 | A chọn đúng chính sách v2024 hiện hành. |

Position inconsistency: 1/5 = 20%, chỉ cặp 12. Điều này cho biết judge đổi kết quả giữa hai lượt đảo vị trí trên một cặp; mẫu 5 cặp chưa đủ để kết luận có position bias ổn định.

Verbosity win rate: 3/4 = 75% các cặp decisive chọn answer dài hơn; hai lần answer A dài hơn thắng, một lần answer B dài hơn thắng. Ở cặp 21, answer A dài hơn nhưng B thắng vì đúng breakdown và có thông tin lương. Đây là tín hiệu cần đọc nội dung, không chứng minh judge ưu tiên độ dài.

## Calibration nhị phân với nhãn người

Calibration dùng đúng model_answer gốc trong fixtures/human_labels_10q.json, không dùng answer A mới từ pipeline. Prompt helper chỉ nhận question, answer và reference; không nhận human_label/human_note.

| ID | model_answer gốc | Nhãn human | Nhãn judge | Khớp |
|---:|---|---:|---:|---|
| 1 | Nhân viên được nghỉ 3 ngày làm việc có lương khi kết hôn. | 1 | 1 | Có |
| 5 | Cần Giám đốc phòng ban phê duyệt. | 0 | 0 | Có |
| 12 | Nhân viên được thưởng Tết tối thiểu 1 tháng lương. | 1 | 1 | Có |
| 21 | Được nghỉ 18 ngày phép (15 cơ bản + 3 thâm niên). Lương Senior từ 20 đến 35 triệu. | 1 | 1 | Có |
| 23 | Hoàn trả 25 triệu vì chưa đủ 1 năm cam kết | 1 | 1 | Có |
| 29 | Trưởng phòng phê duyệt; phạt 2% tháng trên 8 triệu | 0 | 0 | Có |
| 33 | Phép 19 ngày; phụ cấp 1.500.000 VNĐ/tháng | 1 | 1 | Có |
| 41 | Nhân viên được nghỉ 12 ngày phép năm. | 0 | 0 | Có |
| 46 | Nhân viên thử việc không được nghỉ phép năm và phải xin nghỉ không lương nếu cần. | 1 | 1 | Có |
| 50 | Được, miễn là đảm bảo kết nối an toàn. | 0 | 0 | Có |

Artifact có 10 nhãn judge, trùng 10/10 nhãn human; Cohen’s κ = 1.000. Bộ nhãn gồm 6 positive và 4 negative. Đây là kết quả trên mẫu kiểm thử nhỏ, không chứng minh judge hoàn hảo.

Một số reasoning của helper nêu thêm ý không có trong model_answer: câu 1 nói answer có “không trừ vào phép năm” dù answer chỉ nêu số ngày và có lương; câu 12 nói answer nêu điều kiện ≥6 tháng dù model_answer chỉ ghi mức thưởng. Nhãn tổng thể vẫn trùng human, nhưng reasoning cần được kiểm tra riêng nếu dùng để giải thích quyết định.

## Giới hạn và cách dùng

- Chỉ có 5 cặp pairwise và 10 nhãn binary; một cặp bất nhất làm tỷ lệ position thay đổi 20 điểm phần trăm.
- Cặp 12 kết thúc tie sau khi đổi vị trí; nên giữ swap-and-average và chuyển tie cho người review.
- Pairwise judge nên hỗ trợ sàng lọc, không thay thế người đánh giá ở câu version conflict, câu nhiều ý, hoặc khi reasoning không bám answer.
- Tăng bộ calibration lên ít nhất 50 nhãn người và giữ một tập held-out nếu chỉnh prompt; không báo κ trên chính dữ liệu đã dùng để tối ưu prompt.
