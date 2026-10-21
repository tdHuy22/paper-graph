# Đo hiểu bài: đọc chữ so với đọc qua sơ đồ

Câu hỏi cần trả lời: người đọc hiểu bài tốt hơn, nhanh hơn khi đọc qua sơ đồ của paper-graph so với chỉ đọc chữ không?
Bộ đo của `bench/` chấm sơ đồ so với đáp án; nó không nói người đọc có hiểu hơn không. Phép đo này cần người thật.

## Công cụ

```bash
python3 -m paper_graph quiz bench/papers/rag/rag.quiz.json --blocks papers/rag/rag.blocks.json -o papers/rag/rag.quiz.html
python3 -m paper_graph view papers/rag/rag.graph.json --pdf ../pdf-translator/data/rag.pdf -o papers/rag/rag.html
```

- `<tên>.quiz.json`: 3–12 câu trắc nghiệm, mỗi câu 3–5 phương án, một đáp án, giải thích, và câu trích nguyên văn
  chứng minh đáp án (bộ kiểm đối chiếu với blocks.json như neo của sơ đồ). Loại câu: `big` (bức tranh lớn),
  `mechanism` (cơ chế), `evidence` (bằng chứng), `limit` (giới hạn), `detail` (chi tiết).
- Trang làm bài: hỏi người đọc đã đọc bằng cách nào, đo thời gian từ lúc bấm "Bắt đầu", có phương án "Không biết"
  (để đoán bừa không làm nhiễu điểm), chấm ngay, hiện đáp án kèm câu trích, và cho một dòng kết quả JSON để chép lại.
- Đáp án nằm trong trang (đây là bài tự kiểm): người đọc phải tự giác không xem mã trang.
- Có sẵn: `bench/papers/attention/attention.quiz.json`, `bench/papers/rag/rag.quiz.json` (12 câu mỗi bài: q1–q6 do người dựng công
  cụ soạn; q7–q12 do một agent soạn chỉ từ chữ bài, không được đọc sơ đồ hay đáp án bộ đo, 2026-10-19). Sơ đồ: Attention
  có sẵn `bench/papers/attention/attention.graph.json`; RAG ở `papers/rag/rag.graph.json`: skill dung-so-do
  dựng (lượt đo 7, trước khi có bộ câu hỏi), một agent không đọc câu hỏi soát 50 ô với nguyên văn, sửa 28 ô, cả 50 ô
  đã khoá (2026-10-19). Hai trang HTML nhúng chữ và ảnh của bài nên không đưa vào git; tạo lại bằng hai lệnh trên
  (`rag.blocks.json` lấy từ `bench/prepare.py`).
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

- 12 câu mỗi bài (mức tối đa của định dạng) vẫn ít; một câu khó hay dễ bất thường làm lệch điểm. Có thể tách điểm
  q1–q6 và q7–q12 để xem hai nhóm câu có cho cùng chiều không. Hai nhóm còn khác nhau về độ dài và độ khó (q7–q12 dài
  và cụ thể hơn), nên chênh giữa hai nhóm không chỉ do cách soạn.
- q1–q6 do người dựng công cụ soạn, có thể vô tình hợp với cách sơ đồ trình bày; q7–q12 soạn không nhìn sơ đồ nhưng
  vẫn do model soạn. Nên nhờ người khác soạn thêm.
- Đây không phải nghiên cứu có kiểm soát: không giấu được người đọc đang ở điều kiện nào.

## Phép đo thay bằng model (2026-10-19)

Chạy khi chưa có người đọc, để xem model có làm người đọc thay được không. Kết luận: không, vì model đã thuộc bài.

- 6 agent Sonnet 5.5, context mới, mỗi agent một điều kiện cho một bài: không đọc gì (hiểu biết sẵn có), chỉ đọc chữ
  (đầu ra `read`), chỉ đọc `graph.json` (những gì trình xem hiện khi bấm ô). Câu hỏi bỏ đáp án, thêm "Không biết";
  hai điều kiện có tài liệu được dặn chỉ dựa vào tài liệu, không đủ thì chọn "Không biết". Câu trả lời và script chấm:
  `.tmp/do-hieu-bai/2026-10-19-model/` (không có trong git).

| Bài | Không đọc | Đọc chữ | Đọc sơ đồ |
|---|---|---|---|
| Attention | 12/12 | 12/12 | 9/12, 3 "Không biết" (q6, q10, q12) |
| RAG | 12/12 | 12/12 | 12/12 |

- Không đọc mà vẫn 12/12 ở cả hai bài: hai bài này nằm trong dữ liệu huấn luyện của model, nên điểm không nói gì về
  việc sơ đồ giúp hiểu. Muốn đo bằng model thì cần bài ra sau mốc dữ liệu của model, và điều kiện "không đọc" phải ra
  điểm thấp trước đã.
- Điều đo được là độ đủ thông tin: agent đọc sơ đồ trích id ô cho mỗi câu (mọi id đều có thật) và chọn "Không biết"
  khi sơ đồ không nói, dù nó biết đáp án. Sơ đồ RAG (50 ô) đủ cho cả 12 câu, q7 phải suy từ hai ô. Sơ đồ Attention
  (21 ô, dựng tay) thiếu 3 câu: thời gian huấn luyện bản lớn (q6, `evidence`), thí nghiệm đổi số đầu attention (q10,
  `evidence`), so mã vị trí hình sin với mã học được (q12, `limit`). Người đọc qua sơ đồ Attention chỉ trả lời được
  ba câu này nếu mở câu trích hay đã biết từ trước.
- Không sửa sơ đồ Attention theo ba câu này trước khi đo người thật: sơ đồ chỉnh theo đề thì phép đo hết công bằng.

### Lượt 2: hai bài ra sau mốc dữ liệu (2026-10-19)

Thêm hai bài nộp arXiv ngày 16/10/2026 vào bộ đo (`bench/papers.json`, PDF ở `bench/pdf/`): Prism Attention
(`prism`, 20 trang, bài phương pháp) và Ignored, Not Refused (`ignored`, 17 trang, bài đánh giá về prompt injection).
Đáp án `*.gold.json` và bộ 12 câu `*.quiz.json` do một agent Opus soạn chỉ từ đầu ra `read`; sơ đồ do skill dung-so-do
dựng (Opus, `.tmp/dung-so-do-workspace/iteration-8/`), không agent nào thấy kết quả của agent kia. Cùng cách đo như
lượt 1 (6 agent Sonnet; câu trả lời ở `.tmp/do-hieu-bai/2026-10-19-model-moi/`).

| Bài | Không đọc | Đọc chữ | Đọc sơ đồ |
|---|---|---|---|
| Prism | 0/12 (12 "Không biết") | 12/12 | 11/12, 1 "Không biết" (q6) |
| Ignored | 3/12 (9 "Không biết") | 12/12 | 11/12, 1 "Không biết" (q3) |

- Điều kiện "không đọc" giờ ra điểm thấp: model không biết hai bài này. Ba câu Ignored đoán được không cần đọc (q1 lộ từ
  tên bài, q2 và q6 suy được từ cách đặt câu hỏi), đúng như agent soạn đề tự báo trước.
- Đọc chữ vẫn 12/12: model đọc trọn 60–70 nghìn ký tự không mệt, không hết giờ, nên phép đo bằng model chỉ đo được sơ
  đồ có đủ thông tin hay không (đọc sơ đồ so với đọc chữ), không đo được sơ đồ có giúp người hiểu nhanh hơn không.
- Sơ đồ đủ cho 11/12 câu ở cả hai bài. Câu thiếu: Prism q6 (sơ đồ ghi cấu hình 10F11R57S của GLM-5.2 nhưng không nói
  lớp S làm gì, Bảng 9), Ignored q3 (sơ đồ liệt kê nhãn Genuine Refusal, Inert-Recognized mà không nói hai nhãn khác
  nhau ở đâu). Thêm ba câu agent chọn đúng dù một vế của đáp án không có trong sơ đồ (Prism q11; Ignored q4, q5, q10):
  sơ đồ đủ để loại phương án sai, chưa đủ để nói lại trọn ý.
- So với lượt 1: sơ đồ RAG (dựng bằng skill, đã soát tay) đủ 12/12, sơ đồ Attention (dựng tay, 21 ô) 9/12; hai sơ đồ
  skill dựng mới (48 ô mỗi bài, chưa soát tay) 11/12.
- Điểm sơ đồ theo đáp án (`score`): Ignored phủ 14/14, đúng tầng 100%, quan hệ 57%, soi 2/4. Prism lần chấm đầu phủ
  13/13, đúng tầng 46%, quan hệ 50%, soi 1/3: ý `method` của đáp án chỉ neo câu giới thiệu ở trang 2, nên ô "Phương
  pháp" neo vào §4 không khớp, kéo theo cả ba ý `under:method`. Reviewer (không đọc sơ đồ) xác nhận đáp án neo quá hẹp;
  thêm neo §4 (p4-b5), chấm lại: đúng tầng 77%, quan hệ 67%. Phần còn trượt: sơ đồ tách kết quả thành hai ô tầng đầu
  (độ chính xác, tốc độ; skill cho phép), đáp án chỉ có một ý `result`. Không sửa đáp án thêm theo sơ đồ. Điểm soi
  `speedup_bsz16` trượt dù sơ đồ có cả 3,36× và 1,15× (ở hai ô nối bằng cạnh `contradicts`): điểm soi `note` đòi cả hai
  số trong một ô.

### Lượt 3: bài Merging, skill sau lần sửa 20/10 (2026-10-21)

Bài chưa từng dùng để sửa skill (docs/bench.md mục "Merging"). Cùng cách đo như lượt 2.

| Bài | Không đọc | Đọc chữ | Đọc sơ đồ |
|---|---|---|---|
| Merging | 0/12 (12 "Không biết") | 12/12 | 12/12 |

- Lần đầu sơ đồ đủ thông tin cho cả 12 câu ở một bài model không biết (lượt 2: Prism, Ignored 11/12). Một bài, một lần
  dựng: chưa đủ để nói skill sửa ngày 20/10 tốt hơn, chỉ là không kém.

## Bộ đồ đã sẵn (2026-10-21)

- Thư mục gửi người đọc: `papers/do-hieu-bai/goi/` (không vào git, vì nhúng chữ và ảnh của bài; tạo lại bằng hai lệnh ở mục
  "Công cụ" cho cả Attention và RAG, rồi chép hai PDF): `attention.pdf`, `attention.html`, `attention.quiz.html`,
  `rag.pdf`, `rag.html`, `rag.quiz.html`, `HUONG-DAN.md` (bản chép của `docs/huong-dan-nguoi-doc.md`). Khoảng 7 MB, nén
  lại gửi được qua email hay Drive. Mọi trang chạy offline, không tải gì từ ngoài.
- Chia nhóm xen kẽ theo thứ tự nhận lời (A, B, A, B…), báo người đọc nhóm của họ.
- Gom kết quả: mỗi dòng người đọc gửi, thêm `"nguoi"` (mã, vd. P1, không ghi tên thật) và `"nhom"`, ghi vào một file
  `.jsonl`, mỗi dòng một JSON; lần làm lại sau 7 ngày thêm `"lan": 2`. Không đưa file này vào git nếu có thông tin cá
  nhân.
- Chấm: `python3 bench/hieu_bai.py ket-qua.jsonl`. Script chấm lại từ `tra_loi` (không tin điểm tự báo), in từng người
  (điểm, số "Không biết", thời gian, hiệu sơ đồ − chữ), trung vị và số người hơn/kém/bằng theo nhóm A, B và gộp, và
  điểm theo loại câu. Test: `tests/test_hieu_bai.py`.
