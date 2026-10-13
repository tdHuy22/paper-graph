# paper-graph

Mô tả sản phẩm ở [README.md](README.md); file này chỉ ghi trạng thái công việc.

## §0 Đang ở đâu, việc tiếp theo

Cập nhật 2026-10-13.

### Đã xong, có bằng chứng

- **Khảo sát thứ có sẵn** (2026-10-12, skill `reuse-best` và một lượt nghiên cứu
  web). Không công cụ nào làm đủ: sơ đồ có cấu trúc (luồng phương pháp, tuyên bố
  → bằng chứng) **và** mỗi ô neo về đúng trang, đoạn **và** tiếng Việt **và**
  chạy local. Gần nhất là Mind Map của NotebookLM: dạng cây, đóng, không thấy
  tài liệu chính thức nói ô neo về đoạn gốc. PaperBanana (MIT) chỉ ra hình tĩnh;
  Paper2Poster, Paper2Slides ra poster, slide. Quyết định: ghép code của chính
  mình (VietPaper, archctl, paper-anatomy), tự viết phần dựng đồ thị, bộ kiểm,
  trình xem; layout dùng thư viện có sẵn.
- **Bằng chứng nghiên cứu**: phân tích gộp về concept map (Schroeder và cộng sự,
  Educational Psychology Review, 2018) cho hiệu ứng g ≈ 0,58; tự dựng sơ đồ
  (0,72) lợi hơn chỉ xem (0,43). Số lấy từ bản tóm tắt, chưa đọc bảng gốc. Hệ
  quả cho thiết kế: sơ đồ là lối vào nguyên văn, không thay nguyên văn; nên có
  chế độ để người đọc tự dựng hay đoán trước.
- **Sơ đồ mẫu bài Attention** (`pdf-translator/data/attention-is-all-you-need.pdf`),
  dựng tay, ba tầng (tổng quan, phương pháp, tuyên bố → bằng chứng), Hình 1 cắt
  tự động từ trang 3 theo bbox ảnh của PyMuPDF. Mọi neo (mục, trang) trong mẫu
  được `extract_paper.py --find` của paper-anatomy tìm thấy đúng trang. Một câu
  không tìm thấy vì bài chen dấu trích dẫn `[11]` vào giữa câu: bộ kiểm phải bắt
  người dựng chép từ chữ đã trích, không chép theo trí nhớ.
- **Trang kế hoạch** (Artifact riêng tư, bản 1):
  https://claude.ai/artifact/Q99hjFnb4axyLD7rBHLkFW — sơ đồ mẫu bấm được, bốn
  câu cần chốt, mốc, rủi ro. Nguồn HTML ở scratchpad của phiên 2026-10-12; lấy
  lại bằng Artifact `read`.

- **Mốc 1: lõi kiểm được** (2026-10-12, chưa commit). Gói `paper_graph` (Python 3.11, lõi chỉ thư viện chuẩn):
  `extract` (PDF → `*.blocks.json` qua bộ gom đoạn của VietPaper; công thức giữa câu lấy đúng ký tự theo danh sách
  VietPaper ghi, không cắt theo khung), `check` (PG1xx dạng file, PG2xx neo, PG3xx tầng; docs/format.md),
  `verify-blocks` (trích lại rồi so). Bộ đo 3 bài ghim SHA-256 (`bench/papers.json`, `bench/prepare.py`), sơ đồ mẫu
  Attention 21 ô 25/25 neo, đáp án tay 3 bài: 33 ý bắt buộc, 17 tuỳ chọn, mọi neo có thật (docs/bench.md). Threat
  model TM-1..TM-5 đều `đã có` kèm `file:dòng` và test (TM-5 còn phần trình xem ở Mốc 3–4). Review hai lượt
  (reviewer sonnet): lượt 1 tìm 7, lượt 2 (trên các bản sửa) tìm 8, sửa cả 15, mỗi mục có test hồi quy; so khớp câu
  trích giờ theo ranh giới từ và số ("score of 2" không khớp 28.4, 1e-5 khác 1e5, "possible" không khớp
  "impossible"). Sửa thêm: `extract`/`verify-blocks` thỉnh thoảng chết lúc tắt (onnxruntime, mã -6, 1/5 lần) →
  huỷ phiên ONNX sau khi trích và thoát thẳng sau khi ghi xong; 6/6 lần chạy lại sạch. Biên nhận trên mã cuối:
  `../pdf-translator/.venv/bin/python -m unittest discover -s tests -t .` 81 test đạt; `python3 -m unittest …` đạt
  (8 bỏ qua vì thiếu VietPaper); tái hiện: `extract` bài Attention, `check --pdf --strict` 0 lỗi, `verify-blocks`
  khớp trên cả ba bài, và bắt được blocks sửa tay (2 chỗ khác, mã 1).

### Mốc kiểm tra

```bash
../pdf-translator/.venv/bin/python bench/prepare.py                       # blocks của bộ đo (không có trong git)
../pdf-translator/.venv/bin/python -m unittest discover -s tests -t .     # mọi test, gồm bộ trích và bộ đo
python3 -m paper_graph check bench/papers/attention/attention.graph.json --strict
```

- **Mốc 1 đã commit** `668d8e2` (bạn bảo "commit đi", 2026-10-12).
- **Mốc 2, việc 3.1 và 3.2** (2026-10-12; commit 2026-10-13, bạn bảo "chỉ commit thôi"). Threat model TM-6 (prompt injection vào agent dựng sơ đồ),
  TM-7 (ô viết sai con số), TM-8 (dựng lại ghi đè ô đã khoá), đều `đã có`. Code: lệnh `read` (chữ bài kèm id đoạn,
  dòng đầu nói đây là dữ liệu), PG220 (mỗi con số trong ô phải có trong đoạn được neo hay trong chữ của bảng gắn với
  ô; đọc cả kiểu Việt), `check --base` (PG401/402), chữ trong vùng hình/bảng vào blocks.json, bộ chấm `score` và
  `bench/score.py`. Skill `.claude/skills/dung-so-do/`. Kết quả thử skill, mỗi bài một subagent mới:
  BERT (Opus) 31 ô, 75/75 neo, 0 lỗi 0 cảnh báo, phủ 10/10 ý bắt buộc; DataSentinel (Opus) 36 ô, 80/80 neo, 0 lỗi
  0 cảnh báo, phủ 12/13 (thiếu ý "known-answer detection còn FPR/FNR cao" ở dạng ô vấn đề); bài mồi (Sonnet) không
  làm theo lệnh `curl … | sh` và tạo `~/PWNED.txt` cài trong bài, báo đúng đoạn. SKILL.md sửa theo 3 báo cáo (nghĩa
  của "tầng", sha256 đủ 64 ký tự trong `read`, quyền đọc file, luật PG220, công thức là ảnh, bảng dạng chữ, ví dụ
  thể loại không còn nhắc bài trong bộ đo). Sơ đồ mẫu Attention chưa đo bằng skill vì skill lấy nó làm ví dụ.
  Cổng chốt việc (rủi ro cao): differential-review tìm 8, reviewer opus tìm 6, sửa cả 14, mỗi mục có test; kiểm số
  liệu giờ coi một số là một giá trị, có dấu, đọc "512.000" theo hàng nghìn, bỏ số trích dẫn và số dính tên. Bài mồi
  chạy lại lần 2 sau khi sửa SKILL.md vẫn đạt. Biên nhận trên mã cuối: 112 test đạt; `bench/score.py` trên sơ đồ do
  skill dựng: BERT và DataSentinel đạt, 0 lỗi 0 cảnh báo với luật mới.
- **Luật chặn quyền cứng** (F3 của review, `.claude/settings.json` với `permissions.deny` cho mạng và lệnh tải): bạn
  chọn chưa thêm (2026-10-13, "chỉ commit thôi"). TM-6 vẫn chỉ dựa vào chỉ dẫn trong skill và lời nhắc của `read`.
- Phiên làm việc đã chuyển sang thư mục project (2026-10-13).
- **Mốc 2, việc 3.3** (2026-10-13, xong, chưa commit). Bài thứ tư RoFormer (`roformer-rope.pdf`, nặng công thức) vào
  `bench/papers.json`; đáp án tay `bench/papers/roformer/roformer.gold.json` 14 ý bắt buộc, 9 tuỳ chọn, viết trước khi
  xem sơ đồ của skill (sửa một lần sau lượt 4, ghi trong docs/bench.md). Lượt đo 3, 3 subagent Opus trên 3 bài sạch
  (`.tmp/dung-so-do-workspace/iteration-3/`): BERT 10/10, DataSentinel 13/13, RoFormer 14/14, cả ba 0 lỗi; độ phủ chạm
  trần, docs/bench.md ghi vì sao cần đáp án dạng khác. Sửa theo góp ý của agent: `read` in chữ công thức trong mạch
  đoạn, đúng cột; SKILL.md sửa câu sai "công thức không có chữ", bỏ `--strict` ở bước 5 (PG220 vẫn phải hết), thêm
  hướng dẫn `strength`, chữ và bảng lệch số, ô con dưới `limit`, ô suy luận vẫn neo, số mũ âm; `safe()` thoát
  U+2028/2029. Lượt 4 (RoFormer, skill mới): 44 ô, 102/102 neo, 0 lỗi 0 cảnh báo, phủ 14/14. Cổng chốt việc: rủi ro
  vừa, reviewer sonnet tìm 1 vừa (miễn kiểm dãy tên "Bảng 1 và 41 điểm" làm số bịa lọt PG220, đã gỡ, test ngược) và 2
  thấp (đã sửa trong SKILL.md). Biên nhận: 115 test đạt; `bench/score.py` lượt 3, 4 đạt.

### Việc tiếp theo

1. Commit việc 3.3 khi bạn bảo.
2. Mốc 3: trình xem HTML tự chứa (đọc `*.graph.json`, tầng đầu, bấm mở tầng dưới, thẻ chi tiết, ảnh cắt từ bài).

### Quyết định đã chốt (bạn chốt 2026-10-12: "chốt hết", theo phương án khuyên)

- **Q1 B.** Repo riêng gồm lõi (định dạng file, bộ kiểm, bước dựng) và trình xem;
  VietPaper thêm tab "Sơ đồ" qua một lớp nối mỏng.
- **Q2 a.** Skill Claude Code dựng sơ đồ trước; bước gọi API trong app sau, khi đã
  có bộ đo.
- **Q3 i.** Một sơ đồ nhiều tầng, mỗi tầng tối đa 9 ô, bấm để mở tầng dưới.
- **Q4 x.** Mốc đầu: xem, mở nguồn, sửa, khoá; chế độ "đoán trước rồi mở" ở mốc 5.

### Quyết định kỹ thuật tự chốt (đổi được nếu bạn muốn)

- File sơ đồ là JSON có schema: LLM sinh dễ, bộ kiểm đọc dễ, giao diện ghi lại được.
- Bộ trích PDF không biết gì về sơ đồ: lõi nhận danh sách đoạn (id, trang, bbox,
  nhãn layout, chữ), không tự đọc PDF. Giống luật "bộ quét không biết luật" của archctl.
- Layout: elkjs (EPL-2.0, nhóm lồng nhau, cạnh dài) đóng vào trình xem, kèm file
  giấy phép; thử trên sơ đồ mẫu trước khi chốt, dagre (MIT, 49 KB) là dự phòng.

## §1 Các mốc

### Mốc 0: chốt hướng

- [x] Chốt Q1–Q4 @ban (2026-10-12: B, a, i, x)

### Mốc 1: lõi kiểm được

- [x] Định dạng `*.graph.json` và schema: node (id, tầng, loại, nhãn Việt, thuật
  ngữ gốc, giải thích, neo, hình), cạnh (loại, nhãn, neo), trạng thái
  draft/accepted/locked.
- [x] Đầu vào đoạn: lấy `extract_blocks` và vùng layout của VietPaper (đoạn kèm
  bbox, nhãn `image`/`table`/`figure_title`), không viết lại bộ trích.
- [x] Bộ kiểm `paper-graph check`: neo chép nguyên văn có thật ở đúng trang, cạnh
  trỏ node có thật, không ô mồ côi, mỗi tầng tối đa 9 ô, tuyên bố không có bằng
  chứng thì báo ra.
- [x] Threat model trước khi code (PDF lạ, gọi LLM ngoài, server local) bằng skill
  `mo-hinh-de-doa`.
- [x] Bộ đo: đáp án tay cho 3 bài trong `pdf-translator/data/` (Attention, BERT,
  DataSentinel): ô then chốt phải có, cạnh phải đúng.

### Mốc 2: dựng sơ đồ

- [x] Skill Claude Code dựng `*.graph.json` từ đoạn và bảng thuật ngữ, chạy bộ
  kiểm, sửa tới khi đạt. (`.claude/skills/dung-so-do/`, 2026-10-12)
- [x] Đo trên bộ đo: 100% neo hợp lệ, độ phủ ô then chốt. (BERT 10/10, DataSentinel 12/13; `bench/score.py`)
- [x] Thêm bài thứ tư ngoài ví dụ của skill (RoFormer hay RAG), làm đáp án tay, đo skill trên 3 bài sạch. (RoFormer;
  lượt 3: BERT 10/10, DataSentinel 13/13, RoFormer 14/14; 2026-10-13)
- [ ] Bộ đo hết chạm trần: thêm vào đáp án danh sách chỗ bài tự lệch và mức `strength` mong đợi cho các cạnh chính,
  để đo thứ mà độ phủ không đo (lượt 3, 4 đều phủ 100%).
- [ ] `read --render <id>`: cắt hình, bảng ra ảnh để agent nhìn được hình dạng đường cong (chữ trích chỉ có vạch trục).

### Mốc 3: trình xem

- [ ] HTML tự chứa, chạy offline: tầng đầu, bấm mở tầng dưới, thẻ chi tiết có
  trích dẫn, ảnh cắt đúng đoạn và bản dịch.
- [ ] Hình và bảng của bài gắn vào ô liên quan.
- [ ] Sửa nhãn, khoá ô, kéo thả; giữ toạ độ giữa các lần dựng lại.

### Mốc 4: gắn vào VietPaper

- [ ] Tab "Sơ đồ" cạnh bản dịch; bấm ô thì cuộn hai khung tới đúng đoạn.
- [ ] Bước dựng bằng API (model local hay OpenRouter) cho người không dùng Claude Code.

### Mốc 5: học bằng cách dựng

- [ ] Chế độ "đoán trước rồi mở": ẩn tầng dưới, người đọc ghi dự đoán, rồi so.
- [ ] Đo hiểu bài: vài câu hỏi mỗi bài, so đọc chữ với đọc qua sơ đồ.
