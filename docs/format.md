# Định dạng file và luật kiểm

Hai file cho mỗi bài:

| File | Ai viết | Nội dung |
| --- | --- | --- |
| `<bài>.blocks.json` | `paper-graph extract` | các đoạn của bài, kèm trang, khung, nhãn bố cục, chữ; các vùng hình, bảng, công thức |
| `<bài>.graph.json` | model (skill Claude Code), người sửa | sơ đồ nhiều tầng, mỗi ô neo về câu trong bài |

`blocks.json` chứa toàn văn bài báo, nên không đưa vào git (`.gitignore`); tạo lại bằng `extract`.

## `blocks.json`

```json
{"version": 1,
 "source":  {"file": "attention.pdf", "sha256": "bdfa…", "pages": 15, "extractor": "vietpaper app.py sha256:2ddf…"},
 "pages":   [{"page": 1, "width": 612, "height": 792, "text": true, "layout": true, "label": "1"}],
 "blocks":  [{"id": "p1-b12", "page": 1, "bbox": [108, 290, 504, 470], "label": "abstract", "text": "…"}],
 "figures": [{"id": "p3-f1", "page": 3, "bbox": [195, 70, 417, 393], "kind": "image", "caption": "p3-b1"}]}
```

- `page` đếm từ 1 theo thứ tự trang trong file PDF, không theo số in trên trang (số in, nếu PDF có khai báo, nằm ở `label`).
- `bbox` theo điểm (pt) của trang PDF, gốc ở góc trên trái.
- `blocks[].label` lấy từ PP-DocLayoutV3: `text`, `abstract`, `paragraph_title`, `doc_title`, `figure_title`
  (chú thích hình hay bảng), `table` (một ô bảng), `algorithm`, `footnote`, `reference_content`…
- `blocks[].text`: chữ như in, bỏ đậm nghiêng; công thức giữa câu thay bằng đúng các ký tự của nó trên trang (`dk`
  cho d_k). Đoạn chỉ có số hay công thức (ô bảng toàn số) bị bỏ.
- `figures[].kind`: `image`, `chart`, `table`, `formula` (công thức đứng riêng dòng). `caption` là id của đoạn chú thích
  gần nhất nếu có.
- `pages[].text` false: trang scan chưa có chữ (chạy lại với `--ocr`). `layout` false: không nạp được model bố cục,
  đoạn gom theo khoảng cách và hình không được tách.
- id đoạn ổn định khi chạy lại cùng PDF với cùng VietPaper (`source.extractor` ghi băm của `app.py`). VietPaper đổi
  cách gom đoạn thì id có thể đổi; neo theo trang và câu trích nên vẫn đúng, chỉ `block` (không bắt buộc) có thể lệch.

## `graph.json`

```json
{"version": 1,
 "paper": {"title": "Attention Is All You Need", "sha256": "bdfa…", "blocks": "attention.blocks.json"},
 "nodes": [
  {"id": "idea", "parent": null, "kind": "idea",
   "label": "Chỉ dùng attention, bỏ hồi quy",
   "term": "Transformer · self-attention",
   "explain": "Mỗi từ nhìn thẳng vào mọi từ khác …",
   "anchors": [{"page": 1, "quote": "based solely on attention mechanisms, dispensing with recurrence"}],
   "figure": "p3-f1", "basis": "paper", "status": "accepted"}],
 "edges": [{"from": "problem", "to": "idea", "kind": "flow", "label": "giải bằng"}],
 "groups": [{"id": "g.enc", "parent": "method", "label": "Encoder · lặp 6 lần", "members": ["m.enc_attn", "m.enc_ffn"]}]}
```

### Tầng

`parent: null` là tầng đầu. `parent: "method"` là tầng dưới của ô `method`, mở ra khi bấm ô đó. Cạnh và nhóm chỉ
nối các ô cùng tầng. Mỗi tầng tối đa 9 ô; quá thì gom bớt vào một ô và đưa chi tiết xuống tầng dưới của ô ấy.

### Ô (`nodes`)

| Trường | Bắt buộc | Ý nghĩa |
| --- | --- | --- |
| `id` | có | `[A-Za-z0-9_.:-]`, 1–64 ký tự, không trùng với ô hay nhóm khác |
| `parent` | có (`null` được) | id ô cha |
| `kind` | có | tầng đầu: `problem`, `idea`, `method`, `why`, `result`, `limit`, `context`; tầng dưới: `step`, `io`, `concept`, `claim`, `evidence` (dùng ở tầng nào cũng được, đây chỉ là cách dùng thường gặp) |
| `label` | có | nhãn tiếng Việt ngắn; trên 60 ký tự bị cảnh báo |
| `term` | không | thuật ngữ gốc, cách nhau bằng ` · ` |
| `explain` | không | giải thích tiếng Việt, chữ thuần (không HTML, không Markdown) |
| `anchors` | có khi `basis` là `paper` | danh sách neo |
| `basis` | không | `paper` (mặc định): ô nói lại điều bài viết. `inference`: suy luận của người dựng |
| `figure` | không | id trong `figures` của blocks.json |
| `status` | không | `draft` (mặc định), `accepted`, `locked`. Ô `locked` không được dựng lại ghi đè (Mốc 2) |

### Neo (`anchors`)

`{"page": 3, "quote": "…", "block": "p3-b4"}`. `quote` chép **nguyên văn** từ chữ trong blocks.json, 4–15 từ, đủ
riêng để chỉ có ở đúng chỗ đó. `block` không bắt buộc; có thì phải đúng đoạn chứa câu trích.

So khớp bỏ qua hoa thường, dấu câu, khoảng trắng, xuống dòng, gạch nối cuối dòng, chữ ghép (ﬁ), dấu phụ. Nó **giữ**
những gì đổi nghĩa con số, vì neo là thứ chứng minh số liệu:

- `.` giữa hai chữ số (28.4 khác 284), `,` ngăn hàng nghìn (100,000 khác 100000);
- dấu âm trước chữ số, kể cả cách bởi khoảng trắng: −3.2, "a − 3" như "a −3", 1e-5 khác 1e5, 2-3 khác 23 (`-` và `−`
  coi như nhau);
- `< > ≤ ≥ = ≠ ≈ ± + % × ∞`;
- hai nhóm chữ số cách nhau bởi thứ bị bỏ thì vẫn là hai số ("[1, 2]" khác "12").

Câu trích phải **bắt đầu và kết thúc đúng ranh giới** từ và số của bài: "score of 2" không khớp "score of 28.4",
"possible to train" không khớp "impossible to train". Dấu so sánh, dấu của số dính với con số sau nó, `%` dính với con
số trước nó, nên câu trích không thể bỏ mất chúng ở hai đầu ("3.2 points" không khớp "−3.2 points").

Câu trích vắt qua chỗ ngắt đoạn hay ngắt cột vẫn khớp, nhưng phải nằm gọn trong một trang. Chép theo trí nhớ thường hỏng
ở dấu trích dẫn chen giữa câu (`residual connection [11] around`). Chưa phân biệt được chữ số mũ in nhỏ với chữ số
thường (`x²` và `x2`): khi trích từ PDF, chữ số mũ thường chỉ là chữ số cỡ nhỏ, không còn dấu hiệu nào.

Câu trích có ở nhiều chỗ trên trang (thân bài và chú thích hình) thì `block` đúng với chỗ nào cũng được.

### Cạnh (`edges`)

| `kind` | Dùng cho |
| --- | --- |
| `flow` | A rồi tới B, A dẫn tới B |
| `supports` / `contradicts` | bằng chứng (`evidence`) chống đỡ hay bác tuyên bố (`claim`); bắt buộc `strength`: `strong`, `moderate`, `weak` |
| `uses` | A dùng B (khái niệm, thành phần) |
| `relates` | quan hệ khác, nói rõ bằng `label` |

`label` tối đa 40 ký tự. `anchors` không bắt buộc; có thì được kiểm như neo của ô.

## Mã lỗi của `paper-graph check`

| Mã | Mức | Nghĩa |
| --- | --- | --- |
| PG101 | lỗi | thiếu trường, sai kiểu, chuỗi quá dài |
| PG102 | lỗi | giá trị không có trong tập cho phép (`kind`, `basis`, `status`, `strength`) |
| PG103 | lỗi | id sai dạng |
| PG104 | lỗi | id trùng |
| PG105 | lỗi | `parent` không có, hay chuỗi `parent` khép vòng |
| PG106 | lỗi | cạnh trỏ ô không có, hay tự nối vào chính nó |
| PG107 | lỗi | cạnh nối hai tầng |
| PG108 | lỗi | nhóm có thành viên không có, khác tầng, hay thuộc hai nhóm |
| PG109 | lỗi | `version` không hỗ trợ |
| PG110 | cảnh báo | trường lạ (thường là gõ nhầm tên trường) |
| PG111 | lỗi | quá trần: 2000 ô, 5000 cạnh, 500 nhóm, 10 neo mỗi ô hay cạnh; phần thừa bị bỏ qua |
| PG200 | lỗi | ô `basis: paper` không có neo |
| PG201 | lỗi | câu trích không có ở trang đã ghi; gợi ý trang có nó, hay đoạn gần giống nhất |
| PG202 | lỗi | câu trích dưới 4 từ hay dưới 20 ký tự sau chuẩn hoá |
| PG203 | cảnh báo | câu trích trên 40 từ |
| PG204 | lỗi | trang không có |
| PG205 | lỗi | `block` không có, hay không chứa câu trích |
| PG206 | lỗi | SHA-256 của sơ đồ khác của blocks.json hay của PDF đưa vào `--pdf`; neo và hình không được kiểm |
| PG207 | lỗi | `figure` không có trong blocks.json |
| PG208 | cảnh báo | ô suy luận không neo vào tiền đề nào |
| PG210 | cảnh báo | neo vào trang scan chưa có chữ: chưa kiểm được |
| PG211 | lỗi | không có blocks.json để kiểm neo |
| PG300 | lỗi | tầng có trên 9 ô |
| PG301 | lỗi | sơ đồ không có ô nào |
| PG302 | cảnh báo | tầng dưới chỉ có một ô |
| PG303 | cảnh báo | ô đứng lẻ, không cạnh hay nhóm nào |
| PG304 | cảnh báo | nhãn trên 60 ký tự |
| PG305 | cảnh báo | tuyên bố chưa có bằng chứng chống đỡ |
| PG306 | cảnh báo | cạnh `supports`/`contradicts` không đi từ `evidence` tới `claim` |
| PG307 | cảnh báo | bằng chứng không nối tới tuyên bố nào |
| PG308 | cảnh báo | ô nằm sâu hơn 3 tầng |

Neo đạt nghĩa là câu trích **có thật ở trang đã ghi của đúng bài**. Nó không chứng minh ô diễn giải đúng câu ấy:
phần đó cần người đọc, hay bước review ở Mốc 2.

Mã thoát: 0 đạt; 1 có lỗi (hay có cảnh báo khi `--strict`); 2 không đọc được input (file thiếu, hỏng, quá trần,
đường dẫn trong sơ đồ trỏ ra ngoài thư mục).

`--pdf` chỉ băm PDF rồi so với SHA-256 ghi trong sơ đồ và blocks.json. Nó **không** chứng minh blocks.json được trích
từ PDF đó: file blocks sửa tay mà giữ nguyên `source.sha256` vẫn qua. Muốn chắc thì trích lại và so:

```bash
../pdf-translator/.venv/bin/python -m paper_graph verify-blocks bai.pdf bai.blocks.json   # 0 khớp, 1 khác
```

Bản trích lại khác cũng có thể chỉ vì VietPaper đã đổi cách gom đoạn; lệnh báo cả điều đó (`source.extractor`).

## Giới hạn đầu vào

| | Trần | Ở đâu |
| --- | --- | --- |
| PDF | 150 MB, 400 trang (`--max-pages`) | `extract`, kiểm trước khi xử lý trang nào |
| JSON | 50 MB, lồng quá sâu bị từ chối | `check` |
| `paper.blocks` | tên tương đối trong thư mục của sơ đồ, đuôi `.blocks.json`, không đi qua symlink ra ngoài | `check` |

Lý do từng trần ở `.agent/threat-model.md`.
