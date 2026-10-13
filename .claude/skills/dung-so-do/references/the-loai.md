# Thể loại bài và hình dạng sơ đồ

Tầng đầu luôn trả lời: bài giải quyết gì, bằng ý gì, làm thế nào, chứng minh tới đâu, dừng ở đâu. Thể loại đổi ô nào
cần có và ô nào nên mở tầng dưới.

| Thể loại | Tầng đầu thường có | Mở tầng dưới ở | Bằng chứng cần soi |
| --- | --- | --- | --- |
| Phương pháp mới, kiến trúc mô hình | problem, idea, method, why, result, limit | `method` (luồng dữ liệu, khối lặp), `result` (tuyên bố–bảng), `why` (ablation) | bảng so với baseline cùng điều kiện; ablation cho từng thành phần |
| Hệ thống (công cụ, hạ tầng, serving) | problem, context (ràng buộc, tải), method (thành phần), result, limit | `method` (thành phần và luồng gọi) | đo trên tải thật hay tải giả; so với hệ thống nào, cấu hình có công bằng không |
| Bảo mật: tấn công hay phòng thủ | problem, context (mô hình đe dọa), idea, method, result, limit | `method` (các bước, vòng lặp tấn công–phòng thủ), `result` (tấn công đã biết, tấn công thích nghi) | có thử tấn công thích nghi biết rõ cách phòng thủ không; giả định nào của mô hình đe dọa gánh cả bài |
| Lý thuyết (định lý, chứng minh) | problem, context (giả thiết, mô hình), idea (ý chứng minh), result (định lý chính), limit | `idea` (các bổ đề, bước chứng minh), `context` (giả thiết) | giả thiết có thực tế không; cận có chặt không |
| Thực nghiệm, đo đạc (benchmark, phân tích) | problem (câu hỏi), method (cách đo), result (phát hiện), why (giải thích), limit | `result` (mỗi phát hiện–bảng/hình) | cỡ mẫu, phương sai, nhiều seed hay một |
| Dữ liệu (dataset, benchmark mới) | problem, method (thu thập, gán nhãn), result (thống kê, baseline), limit | `method` (quy trình), `result` | độ đồng thuận gán nhãn; rò rỉ giữa tập huấn luyện và kiểm |
| Khảo sát | problem (phạm vi), context (cách chọn bài), idea (cách phân loại), result (xu hướng, khoảng trống), limit | `idea` (các nhánh phân loại) | khảo sát có hệ thống không, bỏ sót gì |

Ghi chú:

- `why` không bắt buộc ở tầng đầu; bài nào tự giải thích vì sao cách làm chạy được (bảng so độ phức tạp, ablation) thì
  đáng có. Không có thì đừng bịa.
- Bài bảo mật: ô `context` cho mô hình đe dọa thường quan trọng chỉ sau `idea`. Hỏi: kẻ tấn công được biết gì, không
  được biết gì, và nếu giả định đó sai thì cách phòng thủ còn đứng không.
- Bài ngắn (hội thảo 4 trang, bài hệ thống 2 trang) có khi chỉ cần tầng đầu và một tầng dưới cho `result`.
- Bài phương pháp có mục nền dài điểm lại các cách cũ (nhiều công thức của cách cũ): một ô `context` ở tầng đầu, mở
  2–4 ô cho các họ cách cũ, mỗi ô nói chúng khác cách mới ở đâu. Nền ngắn thì để trong `explain` của `problem`.
