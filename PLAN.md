# paper-graph

Mô tả sản phẩm ở [README.md](README.md); file này chỉ ghi trạng thái công việc.

## §0 Đang ở đâu, việc tiếp theo

Cập nhật 2026-10-12.

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

### Việc tiếp theo

1. Hỏi bạn: commit Mốc 1 chưa (repo mới `git init`, chưa có commit nào).
2. Mốc 2, việc 3.1: skill Claude Code dựng `*.graph.json` từ blocks. Trước khi viết: threat model cho prompt
   injection (chữ trong PDF ra lệnh cho agent đang dựng sơ đồ).
3. Mốc 2, việc 3.2: bộ chấm theo docs/bench.md (khớp ô với ý qua đoạn neo hay thuật ngữ, độ phủ ý bắt buộc ≥ 80%).

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

- [ ] Skill Claude Code dựng `*.graph.json` từ đoạn và bảng thuật ngữ, chạy bộ
  kiểm, sửa tới khi đạt.
- [ ] Đo trên bộ đo: 100% neo hợp lệ, độ phủ ô then chốt.

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
