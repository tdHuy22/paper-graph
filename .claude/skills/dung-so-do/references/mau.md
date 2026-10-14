# Mẫu cho các chỗ khó viết

Một sơ đồ nhỏ cho một bài **tự đặt** (nén bộ đệm khoá–giá trị cho LLM), chỉ để thấy cách viết; câu trích và số liệu
là giả, đừng chép vào sơ đồ thật. Test `tests/test_build_support.py` (`SkillPatterns`) chạy phần cấu trúc của
`check` trên khối JSON dưới đây, nên nó luôn khớp định dạng thật.

Mẫu có (test `SkillPatterns` còn chạy `check` đầy đủ với blocks dựng từ chính các câu trích, nên mọi con số trong mẫu
đều có trong câu neo của ô, như luật PG220 đòi):

- tầng `result` có tuyên bố được bảng ủng hộ (`supports`), tuyên bố bị chính bảng của bài bác (`contradicts`), và chỗ
  chữ với bảng lệch số ("Chỗ lệch:");
- tầng `limit` chia hai nhóm: điều tác giả tự nhận, và điều do bạn suy ra (`basis: inference`, vẫn neo vào câu làm
  tiền đề);
- `term` của ô tuyên bố, bằng chứng ghi nguồn ngắn (Abstract, Table 2), không phải thuật ngữ.

```json
{"version": 1,
 "paper": {"title": "LiteKV: Compressing the Key-Value Cache", "sha256": "0000000000000000000000000000000000000000000000000000000000000000",
           "blocks": "litekv.blocks.json"},
 "nodes": [
  {"id": "problem", "parent": null, "kind": "problem", "label": "Bộ đệm KV chiếm gần hết bộ nhớ GPU",
   "term": "KV cache", "explain": "Câu càng dài, bộ đệm khoá–giá trị càng lớn, nên số yêu cầu chạy cùng lúc bị giới hạn.",
   "anchors": [{"page": 1, "quote": "the key-value cache dominates GPU memory for long contexts"}],
   "basis": "paper", "status": "draft"},
  {"id": "idea", "parent": null, "kind": "idea", "label": "Giữ đủ chính xác cho token quan trọng, nén mạnh phần còn lại",
   "term": "mixed-precision KV cache", "explain": "Token được chú ý nhiều giữ 8 bit, token ít được chú ý nén xuống 2 bit.",
   "anchors": [{"page": 2, "quote": "we keep frequently attended tokens at 8 bits and the rest at 2 bits"}],
   "basis": "paper", "status": "draft"},
  {"id": "method", "parent": null, "kind": "method", "label": "Đếm điểm chú ý, chọn số bit theo từng token",
   "term": "attention-guided quantization", "explain": "Sau mỗi bước sinh, cộng điểm chú ý của từng token rồi xếp hạng.",
   "anchors": [{"page": 3, "quote": "accumulated attention scores decide the bit width of each token"}],
   "basis": "paper", "status": "draft"},
  {"id": "result", "parent": null, "kind": "result", "label": "Bộ đệm nhỏ hơn 4 lần, chất lượng gần như giữ nguyên",
   "term": "memory · quality", "explain": "Bảng 2 và Bảng 3 so với bộ đệm gốc; có một chỗ chữ và bảng lệch số.",
   "anchors": [{"page": 1, "quote": "reduces the cache by 4x with negligible quality loss"}],
   "basis": "paper", "status": "draft"},
  {"id": "limit", "parent": null, "kind": "limit", "label": "Chỉ thử trên câu dưới 8K token",
   "term": "context length · batch size", "explain": "Tác giả nhận chưa thử câu dài hơn; vài giới hạn khác do người dựng suy ra.",
   "anchors": [{"page": 9, "quote": "we leave contexts beyond 8K tokens to future work"}],
   "basis": "paper", "status": "draft"},

  {"id": "r.c_all", "parent": "result", "kind": "claim", "label": "Tóm tắt: nhanh hơn trên mọi tải",
   "term": "claim · Abstract", "explain": "Tóm tắt nói nhanh hơn trên mọi tải, không kèm điều kiện.",
   "anchors": [{"page": 1, "quote": "LiteKV is faster across all workloads we evaluate"}],
   "basis": "paper", "status": "draft"},
  {"id": "r.c_mem", "parent": "result", "kind": "claim", "label": "Bộ đệm nhỏ hơn 4 lần",
   "term": "claim · Section 5", "explain": "Đo trên mọi mô hình bài thử, cùng độ dài câu.",
   "anchors": [{"page": 6, "quote": "the cache is 4x smaller on every model we test"}],
   "basis": "paper", "status": "draft"},
  {"id": "r.t2", "parent": "result", "kind": "evidence", "label": "Bảng 2: tải ngắn chậm hơn bản gốc",
   "term": "Table 2", "explain": "Ở tải câu ngắn, LiteKV chậm hơn bản gốc (1,8 so với 1,6 ms mỗi token) vì tốn thêm bước nén. Chấm mạnh: chính bảng của bài cho thấy ngược với câu tóm tắt.",
   "anchors": [{"page": 6, "quote": "short prompts see a small slowdown of 1.8 versus 1.6 ms"}],
   "figure": "p6-f1", "basis": "paper", "status": "draft"},
  {"id": "r.t3", "parent": "result", "kind": "evidence", "label": "Bảng 3: bộ nhớ trước và sau khi nén",
   "term": "Table 3", "explain": "Chỗ lệch: chữ ở mục 5 nói nhỏ hơn 4 lần, nhưng Bảng 3 cho 12,0 GB xuống 3,4 GB. Ghi cả hai số, không tự tính tỉ lệ. Chấm vừa: một lần đo, không báo độ dao động.",
   "anchors": [{"page": 6, "quote": "the cache is 4x smaller on every model we test"},
               {"page": 7, "quote": "memory drops from 12.0 GB to 3.4 GB"}],
   "figure": "p7-f1", "basis": "paper", "status": "draft"},

  {"id": "l.long", "parent": "limit", "kind": "limit", "label": "Chưa thử câu trên 8K token",
   "term": "context length", "explain": "Tác giả tự nhận.",
   "anchors": [{"page": 9, "quote": "we leave contexts beyond 8K tokens to future work"}],
   "basis": "paper", "status": "draft"},
  {"id": "l.batch", "parent": "limit", "kind": "limit", "label": "Chỉ đo với một yêu cầu mỗi lần",
   "term": "batch size", "explain": "Tác giả tự nhận chỉ đo batch 1.",
   "anchors": [{"page": 9, "quote": "all latency numbers use a batch size of one"}],
   "basis": "paper", "status": "draft"},
  {"id": "l.drift", "parent": "limit", "kind": "limit", "label": "Điểm chú ý cũ có thể không còn đúng",
   "term": "attention score drift", "explain": "Bài xếp hạng token theo điểm chú ý cộng dồn từ đầu (câu được neo); suy ra: khi chủ đề đổi giữa câu, token từng quan trọng vẫn giữ bit cao. Bài không thử trường hợp này.",
   "anchors": [{"page": 3, "quote": "accumulated attention scores decide the bit width of each token"}],
   "basis": "inference", "status": "draft"}
 ],
 "edges": [
  {"from": "problem", "to": "idea", "kind": "flow", "label": "giải bằng"},
  {"from": "idea", "to": "method", "kind": "flow"},
  {"from": "method", "to": "result", "kind": "flow"},
  {"from": "result", "to": "limit", "kind": "relates", "label": "nhưng"},
  {"from": "r.t2", "to": "r.c_all", "kind": "contradicts", "strength": "strong"},
  {"from": "r.t3", "to": "r.c_mem", "kind": "supports", "strength": "moderate"}
 ],
 "groups": [
  {"id": "g.self", "parent": "limit", "label": "Tác giả tự nhận", "members": ["l.long", "l.batch"]},
  {"id": "g.inf", "parent": "limit", "label": "Người dựng suy ra", "members": ["l.drift"]}
 ]}
```

Ghi chú:

- Cạnh `contradicts` đi từ ô bằng chứng tới ô tuyên bố, như `supports`. Ô tuyên bố bị bác giữ đúng lời bản rộng
  ("Tóm tắt: …") để người đọc thấy bài đã nói gì.
- Bài tự rào ngay trong câu (vd. "tốt nhất trên cả bốn tập (riêng tập X chỉ trên phần chia Y)"): nhãn ghi bản có rào,
  nối `supports`. Chỉ dùng `contradicts` khi bản không rào xuất hiện ở chỗ khác (tóm tắt, kết luận) mà bảng bác nó.
- Một nhóm có thể chỉ có một ô (`g.inf`): nó vẫn cho người đọc thấy ô đó thuộc loại nào.
- Ô suy luận vừa dựa vào sự kiện tác giả nêu vừa có phần bạn suy ra: `basis: inference`, neo vào câu nêu sự kiện,
  `explain` tách rõ phần nào bài nói, phần nào bạn suy ra.
