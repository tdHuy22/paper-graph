# Đo hiểu bài: đọc chữ so với đọc qua sơ đồ

Câu hỏi cần trả lời: người đọc hiểu bài tốt hơn, nhanh hơn khi đọc qua sơ đồ của paper-graph so với chỉ đọc chữ không?
Bộ đo của `bench/` chấm sơ đồ so với đáp án; nó không nói người đọc có hiểu hơn không. Phép đo này cần người thật.

## Công cụ

```bash
python3 -m paper_graph quiz bench/papers/rag/rag.quiz.json -o rag.quiz.html   # kiểm câu hỏi, xuất trang làm bài
python3 -m paper_graph view papers/rag/rag.graph.json -o rag.html            # sơ đồ cho nhóm đọc qua sơ đồ
```

- `<tên>.quiz.json`: 3–12 câu trắc nghiệm, mỗi câu 3–5 phương án, một đáp án, giải thích, và câu trích nguyên văn
  chứng minh đáp án (bộ kiểm đối chiếu với blocks.json như neo của sơ đồ). Loại câu: `big` (bức tranh lớn),
  `mechanism` (cơ chế), `evidence` (bằng chứng), `limit` (giới hạn), `detail` (chi tiết).
- Trang làm bài: hỏi người đọc đã đọc bằng cách nào, đo thời gian từ lúc bấm "Bắt đầu", có phương án "Không biết"
  (để đoán bừa không làm nhiễu điểm), chấm ngay, hiện đáp án kèm câu trích, và cho một dòng kết quả JSON để chép lại.
- Đáp án nằm trong trang (đây là bài tự kiểm): người đọc phải tự giác không xem mã trang.
- Có sẵn: `bench/papers/attention/attention.quiz.json`, `bench/papers/rag/rag.quiz.json` (6 câu mỗi bài). Sơ đồ: Attention
  có sẵn `bench/papers/attention/attention.graph.json`; RAG thì dựng trước (skill dung-so-do hay `build`) vào
  `papers/rag/`, duyệt và khoá ô rồi mới dùng để đo.
- Bộ kiểm cảnh báo PG231 khi đáp án đúng là phương án dài nhất ở quá nửa số câu: viết phương án nhiễu dài và cụ thể
  ngang đáp án.

## Thiết kế

Đổi chéo trong từng người (within-subject crossover), để mỗi người là đối chứng của chính mình:

| Nhóm | Bài 1 (Attention) | Bài 2 (RAG) |
|---|---|---|
| A | đọc chữ | đọc qua sơ đồ |
| B | đọc qua sơ đồ | đọc chữ |

- Chia người vào A, B xen kẽ theo thứ tự đến (A, B, A, B…), không tự chọn.
- Mỗi bài: 15 phút đọc (bấm giờ), rồi làm bài ngay, không mở lại tài liệu.
- "Đọc chữ": bản gốc hay bản dịch VietPaper, tuỳ người. "Đọc qua sơ đồ": trang `view` của bài, được bấm mở câu trích
  và ảnh đoạn gốc (đó là cách dùng thật), không mở PDF riêng.
- Sau 7 ngày, làm lại cùng bộ câu hỏi không đọc lại (đo nhớ lâu); nếu được, dùng thêm vài câu mới cùng loại.
- Người đã đọc kỹ bài nào từ trước thì bỏ bài đó.

## Đo gì, đọc kết quả thế nào

- Số câu đúng (phương án "Không biết" tính là sai), thời gian làm bài, và số "Không biết".
- So từng người: điểm khi đọc qua sơ đồ trừ điểm khi đọc chữ. Với ít người (dưới 20), báo trung vị và số người hơn,
  kém, bằng; đừng kết luận từ trung bình của 5–6 người. Thứ tự bài có thể ảnh hưởng (bài 2 dễ hơn hay người đã quen),
  nên so riêng nhóm A và B trước khi gộp.
- Tách theo loại câu: sơ đồ có thể giúp `big` và `mechanism` mà không giúp `evidence` (con số chi tiết), hay ngược lại.
- Chế độ "Tự đoán trước" của trình xem là một điều kiện thứ ba đáng đo về sau (tự đoán trước rồi mở so với chỉ xem).

## Giới hạn

- 6 câu mỗi bài là ít; một câu khó hay dễ bất thường làm lệch điểm. Thêm câu trước khi đo trên nhiều người.
- Câu hỏi do người dựng công cụ soạn, có thể vô tình hợp với cách sơ đồ trình bày; nên nhờ người khác soạn thêm.
- Đây không phải nghiên cứu có kiểm soát: không giấu được người đọc đang ở điều kiện nào.
