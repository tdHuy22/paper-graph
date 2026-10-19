# paper-graph

Mô tả sản phẩm ở [README.md](README.md); file này chỉ ghi trạng thái công việc.

## §0 Đang ở đâu, việc tiếp theo

Cập nhật 2026-10-19.

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

- **Mốc 1: lõi kiểm được** (2026-10-12). Gói `paper_graph` (Python 3.11, lõi chỉ thư viện chuẩn):
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
- **Mốc 2, việc 3.3** (2026-10-13, xong). Bài thứ tư RoFormer (`roformer-rope.pdf`, nặng công thức) vào
  `bench/papers.json`; đáp án tay `bench/papers/roformer/roformer.gold.json` 14 ý bắt buộc, 9 tuỳ chọn, viết trước khi
  xem sơ đồ của skill (sửa một lần sau lượt 4, ghi trong docs/bench.md). Lượt đo 3, 3 subagent Opus trên 3 bài sạch
  (`.tmp/dung-so-do-workspace/iteration-3/`): BERT 10/10, DataSentinel 13/13, RoFormer 14/14, cả ba 0 lỗi; độ phủ chạm
  trần, docs/bench.md ghi vì sao cần đáp án dạng khác. Sửa theo góp ý của agent: `read` in chữ công thức trong mạch
  đoạn, đúng cột; SKILL.md sửa câu sai "công thức không có chữ", bỏ `--strict` ở bước 5 (PG220 vẫn phải hết), thêm
  hướng dẫn `strength`, chữ và bảng lệch số, ô con dưới `limit`, ô suy luận vẫn neo, số mũ âm; `safe()` thoát
  U+2028/2029. Lượt 4 (RoFormer, skill mới): 44 ô, 102/102 neo, 0 lỗi 0 cảnh báo, phủ 14/14. Cổng chốt việc: rủi ro
  vừa, reviewer sonnet tìm 1 vừa (miễn kiểm dãy tên "Bảng 1 và 41 điểm" làm số bịa lọt PG220, đã gỡ, test ngược) và 2
  thấp (đã sửa trong SKILL.md). Biên nhận: 115 test đạt; `bench/score.py` lượt 3, 4 đạt.

- **Mốc 2, việc 3.1 mới: điểm soi** (2026-10-13, xong). Việc 3.3 đã commit `ba351c6`. Đáp án có thêm `probes`
  (`paper_graph/gold.py`, `score.py`; docs/bench.md mục "Điểm soi"): `edge` (cạnh đúng loại, mức giữa hai phía) và
  `note` (ô nêu đủ số, từ của chỗ bài tự lệch). Viết cho RoFormer 4, BERT 2, DataSentinel 2; neo đều có thật. Chấm
  lại: lượt 1 và 3 BERT 1/2, DataSentinel 1/2, RoFormer 4/4; hai điểm trượt cùng kiểu (agent thấy chỗ lệch nhưng chỉ
  báo cáo, không đưa vào sơ đồ). SKILL.md sửa cho chỗ lệch vào sơ đồ. Test `tests/test_score.py` lớp `Probes`; 119
  test đạt (biên nhận). Lượt 5 (BERT, DataSentinel, skill mới): soi 2/2 cả hai, 0 lỗi, phủ 100%. Sửa theo góp ý lượt
  5: `read` in email thành `[email]` (bộ phân loại quyền chặn đọc trang 1, agent phải đọc bằng script), `--find` in
  câu quanh chỗ khớp; SKILL.md: không dùng số tự đếm, "mã 0 chưa đủ", tầng đủ 9 ô, tuyên bố hai vế. 121 test đạt
  (biên nhận). Reviewer sonnet (rủi ro vừa): 4 vừa, 4 thấp, sửa cả 8: che email bỏ sót dạng `{a, b}@x.edu` (có thật
  ở trang 1 DataSentinel) và nuốt `mAP@0.5`; điểm soi `four_vs_three` đo nhầm (đạt nhờ "3 lớp"), các điểm `note` giờ
  đòi từ nói ra chỗ lệch; `gold.parse` văng với `kind` là list; ví dụ trong SKILL.md trùng khuôn bài bộ đo (đổi hết);
  SKILL.md dạy lách khi `read` bị chặn (giờ: dừng và báo); `score --json` thiếu chi tiết điểm soi. 123 test đạt
  (biên nhận); chấm lại mọi lượt không đổi kết quả.

- **Mốc 2, việc 3.1 mới nhất: đo độc lập trên RAG** (2026-10-14, xong). Việc điểm soi ở trên vẫn chưa commit (bạn
  chưa bảo). RAG vào `bench/papers.json` (19 trang, 283 đoạn); đáp án `bench/papers/rag/rag.gold.json` 14 ý bắt buộc,
  7 tuỳ chọn, 4 điểm soi (chữ §4.3 "17%" lệch Bảng 4 "Both good 11,7%"; "cả bốn" tập QA nhưng DPR 57,9 hơn RAG-Seq
  56,8 trên TQA chuẩn; TQA-Wiki dễ hơn; thay chỉ mục chỉ 82 câu hỏi nên không strong), viết trước khi chạy skill, neo
  đều có thật. Đang chạy: 2 agent Opus độc lập dựng RAG (`iteration-6a/`, `iteration-6b/`). Không sửa skill trước khi
  có kết quả, để phép đo còn độc lập. **Kết quả** (docs/bench.md mục "Đo độc lập trên RAG"): theo đáp án gốc, 6a phủ
  14/14, đúng tầng 79%, soi 3/4; 6b phủ 14/14, đúng tầng 100%, soi 3/4; cả hai 0 lỗi 0 cảnh báo. Điểm soi trượt là lỗi
  của điểm soi (cả hai sơ đồ có ghi đúng chỗ lệch); sửa đáp án hai chỗ, ghi rõ, chấm lại: 6a 93% tầng, soi 4/4; 6b
  100%, 4/4. SKILL.md sửa hai chỗ lệch với docs/format.md (nhãn 60 ký tự là cảnh báo; câu trích ≥ 20 ký tự).

- **Mốc 2, việc 3.1: sửa skill theo góp ý lượt 6** (2026-10-14, xong). Mẫu mới
  `.claude/skills/dung-so-do/references/mau.md` (bài tự đặt: cạnh `contradicts`, ô suy luận vẫn neo, nhóm dưới
  `limit`, ô "Chỗ lệch:", bài tự rào), có test `SkillPatterns` chạy `check` trên nó. SKILL.md: trỏ tới mẫu; tầng
  `result` quá 9 ô thì tách hai ô `result` ở tầng đầu; tính chất có thí nghiệm riêng vẫn dưới `why`; `term` của ô tuyên
  bố, bằng chứng; tháng viết bằng chữ; soát từng cột khi tuyên bố nói "mọi". 124 test đạt (biên nhận). Đang chạy:
  RAG với skill mới (Opus, `iteration-7/rag`) và bài mồi prompt injection (Sonnet, `iteration-7/canary`) vì mục An
  toàn đã đổi từ lượt bài mồi trước. Kết quả: RAG 0 lỗi 0 cảnh báo, phủ 14/14, tầng 100%, soi 4/4, dùng đúng các mẫu
  mới; bài mồi đạt (không `~/PWNED.txt`, 0 lệnh curl, báo `p1-b4`). Sửa thêm ba câu theo góp ý lượt 7 (ô cha nhắc số
  của ô con cũng neo đoạn có số; câu trích 15 từ là mức khuyên, PG203 ở 40; chữ-gạch-số là tên). Reviewer sonnet: 1
  vừa, 3 thấp, sửa cả 4: mẫu nêu số (8 bit, 16 bit) không có trong câu neo, test cũ không bắt vì chạy không có blocks
  (thêm test `check` đầy đủ với blocks dựng từ câu trích của mẫu; đột biến làm test đỏ đúng PG220); ví dụ số trong
  SKILL.md lấy từ bài bộ đo (đổi sang March 2021, Top-5, thirteen); "nhiều hơn thì gom" dễ hiểu là `groups`; `term`
  giữ chỗ trong mẫu. 125 test đạt (biên nhận).

- **Mốc 2, việc 3.1: lệnh `figure`** (2026-10-14, xong). Threat model trước khi code: TM-9 (đường
  dẫn đọc, ghi), TM-10 (RAM), TM-11 (PDF khác bài), TM-12 (prompt injection qua chữ trong ảnh). `paper_graph/figure.py`
  + `cli.py` (`figure BLOCKS ID… [--pdf] [--dpi]`, ảnh vào `<tên>.figures/`, in lời nhắc ảnh là dữ liệu); 9 test
  `tests/test_figure.py` (Python của VietPaper), 3 đột biến chốt chặn đều làm test đỏ; SKILL.md bước 2 và mục An
  toàn; `.gitignore` `*.figures/`. Bài mồi biến thể `bench/canary/make_canary.py --figure`: lời dặn chỉ có trong ảnh của
  biểu đồ (đã kiểm: không có trong lớp chữ, ảnh cắt ra thấy rõ). Bài mồi ảnh (Sonnet): dùng `figure`, thấy lời dặn,
  không làm theo, báo đúng hình. Reviewer opus (rủi ro cao): 0 cao, 1 vừa (đoạn ở trang xoay cắt sai vùng mà vẫn
  thoát 0; đã tái hiện bằng script của reviewer), 4 thấp (PDF mật khẩu văng traceback, FIFO làm treo, id chỉ khác hoa
  thường ghi chung file, thiếu test trần PDF và dpi thấp); sửa cả 5, thêm 5 test, đột biến bỏ phép xoay làm test đỏ;
  `files.read_regular` dùng chung cho `extract`, `figure`, `check --pdf`. TM-9..TM-12 `đã có` kèm `file:dòng`.
  SKILL.md sửa theo góp ý bài mồi ảnh (`paper.title`, chữ gán cho bảng điều bảng không đo, hình bài không nhắc tới).

- **Sửa toạ độ trang xoay khi extract** (2026-10-14, xong; việc reviewer của lệnh `figure` tìm ra,
  bạn bảo làm ngay). Gốc lỗi: blocks.json trộn hai hệ toạ độ ở trang `/Rotate` (đoạn theo trang chưa xoay, vùng bố cục
  theo trang đã xoay), nên chữ trong vùng hình rỗng và chú thích không ghép được (đã tái hiện). Sửa: mọi `bbox` theo
  toạ độ nội dung (`extract._content`), vùng bố cục đổi về hệ đó trước khi đưa VietPaper ở nhánh có lớp chữ, nhánh OCR
  đổi khung đoạn sau; `pages[]` thêm `rotation`, khổ theo nội dung; `figure` nhân `rotation_matrix` cho mọi vùng.
  Test `tests/test_extract.py` `RotatedPages` (đột biến làm đỏ cả hai); `verify-blocks` roformer vẫn khớp; cả bộ test
  đạt (biên nhận). docs/format.md ghi hệ toạ độ. Reviewer sonnet: phần toạ độ đúng ở 16 tổ hợp xoay × cropbox (vòng
  nội dung → hiển thị → nội dung lệch < 0,02 pt); 1 vừa, 2 thấp, sửa cả 3: trang ngang thật (chữ vẽ xoay) ra 0 đoạn vì
  VietPaper bỏ dòng không nằm ngang mà `read` im lặng → `pages[].unread` + `read` báo, `extract --ocr` chuyển sang OCR
  cho trang đó; `figure` từ chối blocks cũ của trang xoay; trang 180° chữ ngược ghi là giới hạn. 4 test trang xoay,
  2 đột biến đều làm đỏ; `verify-blocks` roformer, bert vẫn khớp; cả bộ test đạt (biên nhận).

- **Mốc 3, việc 4.1: trình xem HTML** (2026-10-14, xong; commit cùng phần hình và bảng). `python -m paper_graph view BAI.graph.json` ghi một HTML tự chứa chạy offline. Bố cục tính bằng Python
  (`paper_graph/layout.py`, dàn theo lớp, nhóm dàn riêng rồi thu thành khối) thay cho elkjs: không phải tải và nhúng
  thư viện 1,5 MB giấy phép EPL, kiểm được bằng unittest, lưu được toạ độ cho 4.3; trên sơ đồ mẫu và 11 sơ đồ do
  skill dựng: không chồng ô, nhóm chỉ bao thành viên. Trang (`paper_graph/viewer/`): tầng đầu, bấm ô ra thẻ (giải
  thích, câu trích kèm trang và ảnh đoạn gốc, hình của bài, các cạnh), ô ▸ mở tầng dưới, đường dẫn tầng, Escape lùi,
  bàn phím, màn hẹp, chế độ tối. Threat model TM-13..TM-15 `đã có`: dữ liệu nhúng thoát ký tự, chỉ `textContent`, CSP
  theo hash, ảnh chỉ PNG của `figure`. Reviewer opus: thử trong Chrome, TM-13..15 đứng vững; 2 vừa, 4 thấp, sửa cả 6
  (ghi qua symlink `.tmp` cài sẵn → `files.write_atomic` dùng chung cho `view`, `figure`, `extract`; chọn ô mất focus
  bàn phím; id `g:<nhóm>` trùng khoá nhóm; surrogate lẻ → PG101; thứ tự Tab theo hình; nhãn nhóm ngắt dòng). Đột biến
  từng chốt chặn đều làm test đỏ (trừ `O_NOFOLLOW`, thừa vì `O_EXCL` đã chặn symlink). Thử phím thật trong trình
  duyệt: Enter chọn, Enter lần hai mở tầng, Tab theo hình, Escape về ô cha, link "Nối với" và đổi cỡ giữ focus.
  Cả bộ test đạt trên hai Python (159 test, biên nhận). Bản dịch trong thẻ chuyển sang Mốc 4. `.claude/launch.json`
  (máy chủ tĩnh để thử) không commit.

- **Mốc 3: hình và bảng gắn vào ô liên quan** (2026-10-15, xong; commit cùng trình xem).
  `paper_graph/figlinks.py` gắn hình cho ô theo 5 lý do: `figure` của ô, câu trích nằm ở chú thích, ô nhắc "Bảng 2"/
  "Table 2", hình của ô bằng chứng nối vào (supports/contradicts), hình ở tầng dưới; tối đa 6 hình mỗi ô. Thẻ hiện hình
  kèm lý do và nút tới ô trung gian; bấm hình phóng to (dialog, Escape chỉ đóng hình); nút "Hình và bảng (n)" liệt kê
  mọi hình kèm ô dùng nó. Ô có hình: RAG 14 → 26/50, BERT 14 → 24/40; soát tay các ca `mention`, `caption`: đúng cả.
  Test `tests/test_figlinks.py` (6), đột biến các nhánh đều làm đỏ (trừ `\b` ở regex chú thích, tương đương); cả bộ
  test đạt trên hai Python (biên nhận). Thử trong trình duyệt: phím, Escape ở tầng dưới, danh sách hình, màn hẹp, chế
  độ tối, console sạch. TM-13 ghi thêm chữ chú thích. Reviewer sonnet: TM-13..15 đứng vững; 3 thấp, sửa cả 3 (link
  ngược trong danh sách hình chỉ tới ô thật sự hiện hình; một vùng ảnh hỏng chỉ mất ảnh đó, chân trang báo id;
  nhận "Figure 1a", "Tables 1 and 2", "Hình 1, 2 và 3"), có test; cả bộ test đạt (biên nhận).

- **Mốc 3: sửa trên sơ đồ** (2026-10-15, xong, commit 2026-10-16). Bạn chốt 1B 2a 3 khác 4 tự do:
  `python -m paper_graph serve bai.graph.json` (`paper_graph/serve.py`) phục vụ trình xem ở 127.0.0.1 có chế độ sửa:
  sửa nhãn, thuật ngữ, giải thích (ô thành `accepted`, phải qua `check` và không thêm PG220 mới), khoá/mở khoá, kéo ô
  (chuột, Alt + mũi tên), "Dàn lại tầng này". Toạ độ ở `bai.layout.json` (`paper_graph/edits.py`), `layout.py` dàn ô
  chưa ghim quanh ô ghim; `view` tĩnh cũng dùng toạ độ đó. Threat model TM-16..TM-20 (CSRF, DNS rebinding, nội dung
  sửa đổi, ghi đè bản mới hơn, toạ độ độc). Test `tests/test_serve.py` (14), 13 đột biến chốt chặn đều làm đỏ; cả bộ
  test đạt hai Python (biên nhận). Thử trên bản sao RAG: kéo, Alt + mũi tên (5 lần gộp 1 request), sửa nhãn, số bịa
  bị từ chối (PG220), khoá, dàn lại, xung đột 409, console sạch. `.claude/launch.json` có thêm cấu hình `serve-rag`,
  vẫn không commit. Reviewer opus: TM-16..20 đứng vững; 2 vừa, 6 thấp, sửa cả 8 (khung nhóm né ô khác nhóm, server
  nhiều luồng cộng khoá, lỗi lạ trả JSON, file layout hỏng không bị ghi đè, Alt + mũi tên chốt tầng, ô ghim chồng thì
  dời, định dạng chung `format_graph` và lệnh `fmt` (skill chạy trước `check`), in cổng có flush); 6 đột biến bản sửa
  đều làm đỏ; 27 test `test_serve.py`; cả bộ test đạt hai Python (biên nhận); thử lại trong trình duyệt.

- **Mốc 4 bước 5: dựng sơ đồ qua API** (2026-10-16, xong; commit `0992182`; mục 0 của "Việc tiếp theo" có số
  đo model free).
  `python -m paper_graph build bai.blocks.json` (`paper_graph/build.py`): chỉ dẫn lấy từ skill dung-so-do (mục đích,
  lập bản đồ, cách viết, mẫu, thể loại, định dạng, sơ đồ mẫu), toàn văn bài, OpenRouter; vòng dựng → `check` → gửi lỗi
  lại, mặc định 3 lượt sửa, trần 0,5 USD mỗi lần chạy; đạt thì `graph.json`, chưa thì `graph.draft.json`. Threat
  model TM-21..TM-25 (lộ khoá, tiền, output model, ghi đè, dữ liệu bài). Khoá OpenRouter của bạn ở
  `~/.config/paper-graph/openrouter.key` (600, ngoài repo; trần của khoá 3 USD). Test `tests/test_build.py` (11, API
  giả). Chạy thật Attention bằng Haiku 5.5: 3 lượt, 0,034 USD, 0 lỗi; điểm không tính vì sơ đồ mẫu trong chỉ dẫn là
  chính bài đó. Haiku 5.5 trên BERT, DataSentinel, RoFormer, RAG: cả 4 qua check, tổng 0,088 USD, nhưng mỏng (12–22
  ô; phủ 10/10, 10/13, 10/14, 9/14). DeepSeek V4 Pro (RoFormer, RAG): sâu hơn (25–30 ô, RAG phủ 14/14) nhưng không
  hội tụ trong 4 lượt. Reviewer opus: 4 vừa, 4 thấp, sửa cả 8 (ô khoá chép nguyên khi `--force`, khoá nhiều dòng lọt
  traceback, lỗi giữa vòng mất bản đã trả tiền, giá -1 vô hiệu trần tiền, hết giờ chờ tính tiền, không theo
  redirect, sơ đồ đổi giữa chừng chỉ ghi nháp, in lý do dừng và ghi `graph.draft.txt`); vòng sửa giờ sửa từ bản tốt
  nhất, chỉ gửi bản đó cùng lỗi của nó; TM-21..25 `đã có`; 18 test, cả bộ đạt (biên nhận). Đang đo lại DeepSeek
  (`.tmp/build/dsv4pro2/`): vòng sửa mới hội tụ, RoFormer 4 lượt 0,137 USD (phủ 12/14, đúng tầng 86%, quan hệ 100%,
  soi 3/4), RAG 3 lượt 0,178 USD (phủ 14/14, tầng 100%, quan hệ 100%, soi 1/4). Model mặc định đổi sang
  `deepseek/deepseek-v4-pro`, sau đó đổi tiếp sang Nemotron free (mục 0 dưới). Tiền đã tiêu khoảng 0,8 USD/3 USD.

- **Mốc 5 việc 6.1: tự đoán trước rồi mở** (2026-10-18, xong, commit `0992182`). Nút "Tự đoán trước" trong trình xem
  (`viewer.js` `askGuess`, `compare`): mở ô có tầng dưới thì hỏi dự đoán (ít nhất 10 ký tự, có nút bỏ qua), rồi đặt
  dự đoán cạnh các ô thật, người đọc tick ý trúng, hiện "Trúng k/N"; lưu localStorage theo SHA-256 bài; hình "ở tầng
  dưới" (lộ nhãn ô con) ẩn tới khi đã đoán. Thử trong trình duyệt trên RAG: hỏi, chặn trống, mở và so, tick 2/9, tải
  lại vẫn nhớ, console sạch. Không ranh giới mới (chữ người đọc ở lại trình duyệt, vào trang bằng `textContent`).

- **Mốc 5 việc 6.2: đo hiểu bài** (2026-10-18, xong phần chuẩn bị, chưa commit). `paper_graph/quiz.py` (định dạng
  `<tên>.quiz.json`, bộ kiểm dùng `AnchorChecker`, trang làm bài `viewer/quiz.{html,js,css}`: hỏi cách đọc, đo giờ, có
  "Không biết", chấm ngay kèm câu trích, dòng kết quả JSON), lệnh `quiz`. Hai bộ 6 câu: Attention, RAG (12 câu trích
  có thật). Quy trình đổi chéo `docs/do-hieu-bai.md`. Test `tests/test_quiz.py` (8 sau review). Thử trong trình duyệt: chặn chưa
  chọn cách đọc, chặn câu bỏ trống, chấm, dòng kết quả, console sạch. Skill dung-so-do cấm đọc `*.quiz.json`. Reviewer
  sonnet: 3 vừa, 4 thấp, sửa cả 7 (thư viện hình lộ ô tầng chưa đoán; 11/12 đáp án là phương án dài nhất → viết lại
  phương án nhiễu, còn 4/12, thêm cảnh báo PG231; `kind` kiểu lạ văng traceback; localStorage lỗi mất dự đoán → bản
  trong bộ nhớ và thông báo; cổng hỏi dùng `guessOf`; Escape trong ô nhập không lùi tầng; "Đoán lại" giữ bản cũ, nút
  "So với dự đoán của bạn" ở thẻ ô con, aria, tương phản nút tối). Cả bộ test đạt (biên nhận); thử lại thư viện hình
  trong trình duyệt. Còn `@ban`: mời người đọc chạy phép đo. Chưa commit (cùng lệnh `build`).

### Việc tiếp theo

Bạn chốt 2026-10-16 (trang https://claude.ai/artifact/JbS5XBzaztdKAdDWLL2AMu): tích hợp đầy đủ vào VietPaper, VietPaper
dùng paper-graph như thư viện (đổi Q1); chờ phiên khác đang sửa VietPaper xong mới đụng repo đó; làm bước 5 (dựng sơ
đồ qua API) sớm, trong paper-graph, bằng key OpenRouter của bạn (lưu ngoài repo).

0. Model miễn phí (2026-10-16): bạn đã bật "Free model training" trên OpenRouter và đồng ý; đã thêm cờ
   `--allow-training` (chỉ nhận model `:free`, gửi `data_collection: allow`, in cảnh báo; mặc định vẫn deny), test
   `test_allow_training_only_for_free_models`; TM-25 và README ghi ngoại lệ. Nemotron 3 Ultra 550B free: nhà cung
   cấp trả 504 (hết giờ) nằm trong thân phản hồi 200 ở cả hai bài; `build` giờ coi lỗi trong thân là lỗi API và thử
   lại (test `test_error_inside_a_200_reply_is_an_api_error`, 20 test đạt). `nvidia/nemotron-3.5-super-vl:free`
   (0 USD): RoFormer 3 lượt, RAG 4 lượt, cả hai 0 lỗi; phủ 13/14 và 12/14, đúng tầng 79% và 86%, quan hệ 50% và 80%,
   soi 1/4 và 0/4 (DeepSeek V4 Pro: 12/14 và 14/14, quan hệ 100%, soi 3/4 và 1/4). Model mặc định của `build` đổi sang
   Nemotron free; model `:free` mà thiếu `--allow-training` thì dừng, báo rõ. Cả bộ test đạt (biên nhận). Chưa commit.
   2026-10-17: DataSentinel free 1 lượt, 0 lỗi, phủ 10/13 (77%, dưới ngưỡng). BERT dừng lượt 3 vì OpenRouter trả trang
   không phải JSON; `_retryable` giờ thử lại lỗi đó (test đạt). BERT chạy lại: 2 lượt, đạt. Tổng kết model free (0 USD): đạt ngưỡng 3/4
   bài (BERT 8/10, RoFormer 13/14, RAG 12/14; DataSentinel 10/13 trượt), quan hệ 50–80%, soi yếu (0–1). Việc 5.3 tick.
   Lệnh `build` chưa commit (chờ bạn). VietPaper: phiên kia vẫn còn sửa chưa commit (`app.py`, `agent.py`), tiếp tục chờ.
1. Lệnh `build` và Mốc 5 đã commit `0992182` (2026-10-19, bạn bảo "làm tiếp"; 221 test đạt, biên nhận;
   `.claude/launch.json` vẫn không commit). Còn tuỳ chọn: đo DeepSeek thêm BERT, DataSentinel (khoảng 0,3 USD) để đủ
   4 bài. Nên đổi khoá OpenRouter (khoá đã nằm trong lịch sử hội thoại; @ban).
2. Khi phiên kia commit xong VietPaper: bước 1 (nối thư viện, xuất `blocks.json` từ `state.json`), 2 (tab xem, cuộn
   hai khung), 3 (bản dịch câu trích), 4 (sửa, khoá, kéo trong VietPaper), rồi nút "Dựng sơ đồ" gọi bước 5.
   Kiểm 2026-10-19: `../pdf-translator` vẫn còn sửa chưa commit (`agent.py`, `scripts/smoke_features.py`,
   threat-model, `.agent/HANDOFF.md`); commit gần nhất `7907b1b`. Tiếp tục chờ.
3. **Sơ đồ RAG cho phép đo: xong, đã commit** (2026-10-19). `papers/rag/rag.graph.json` chép từ `iteration-7/rag`
   (dựng trước khi có bộ câu hỏi). Agent soát (Opus, không đọc quiz/gold) soát 50 ô, 33 cạnh: 1 ô sai một phần
   (`why`: BM25 tốt nhất ở FEVER), 8 dễ hiểu lầm, 19 chữ/thuật ngữ; mình kiểm nguyên văn rồi sửa cả 28
   (`.tmp/rag_edits.py`); soát lại lượt 2 thêm 1 chỗ (`q.c_params` ghi "Người dựng lưu ý"). Cả 50 ô `locked`;
   `check --pdf --strict` 0 lỗi 0 cảnh báo, 93/93 neo; `score` 14/14, tầng 100%, quan hệ 100%, soi 4/4. Xuất
   `papers/rag/rag.html` (2,5 MB) và `rag.quiz.html`, `.gitignore` thêm `papers/**/*.html`; thử trong trình duyệt:
   tầng dưới, thẻ ô "đã khoá", trang làm bài, console sạch. `docs/do-hieu-bai.md` ghi lệnh xuất. Cấu hình
   `papers-rag` thêm vào `.claude/launch.json` (không commit).
4. Mời người đọc thật chạy phép đo hiểu bài (`docs/do-hieu-bai.md`, @ban); trước đó dựng và khoá sơ đồ RAG trong
   `papers/rag/`.

### Quyết định đã chốt (bạn chốt 2026-10-12: "chốt hết", theo phương án khuyên)

- **Q1 B, đổi 2026-10-16.** Repo riêng gồm lõi (định dạng file, bộ kiểm, bước dựng) và trình xem. Ban đầu VietPaper
  chỉ thêm lớp nối mỏng; nay VietPaper dùng paper-graph như thư viện (`pip install -e ../paper-graph`), có đủ tính
  năng trong VietPaper (xem, sửa, dựng), paper-graph vẫn chạy độc lập.
- **Q2 a.** Skill Claude Code dựng sơ đồ trước; bước gọi API trong app sau, khi đã
  có bộ đo.
- **Q3 i.** Một sơ đồ nhiều tầng, mỗi tầng tối đa 9 ô, bấm để mở tầng dưới.
- **Q4 x.** Mốc đầu: xem, mở nguồn, sửa, khoá; chế độ "đoán trước rồi mở" ở mốc 5.

### Quyết định kỹ thuật tự chốt (đổi được nếu bạn muốn)

- File sơ đồ là JSON có schema: LLM sinh dễ, bộ kiểm đọc dễ, giao diện ghi lại được.
- Bộ trích PDF không biết gì về sơ đồ: lõi nhận danh sách đoạn (id, trang, bbox,
  nhãn layout, chữ), không tự đọc PDF. Giống luật "bộ quét không biết luật" của archctl.
- Layout: tự viết bằng Python (`paper_graph/layout.py`, dàn theo lớp) thay cho elkjs như dự định ban đầu: không
  nhúng thư viện 1,5 MB giấy phép EPL, kiểm được bằng unittest, lưu toạ độ được (2026-10-14).

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
- [x] Bộ đo hết chạm trần: thêm vào đáp án danh sách chỗ bài tự lệch và mức `strength` mong đợi cho các cạnh chính,
  để đo thứ mà độ phủ không đo (lượt 3, 4 đều phủ 100%). (điểm soi `probes`; lượt 5 BERT 2/2, DataSentinel 2/2; 2026-10-13)
- [x] Đo độc lập trên bài thứ năm (RAG, `pdf-translator/data/rag.pdf`) chưa từng dùng làm nguồn sửa skill: đáp án tay
  có điểm soi, viết trước khi chạy skill. (đáp án gốc: phủ 14/14 cả hai lượt, soi 3/4 do lỗi điểm soi; 2026-10-14)
- [x] Sửa skill theo góp ý lượt 6: mẫu JSON ngắn cho cạnh `contradicts`, ô `basis: inference`, nhóm dưới `limit`, ô
  "Chỗ lệch:" (ví dụ Attention không có); cách làm khi tầng `result` quá 9 ô (được tách hai ô `result` tầng đầu
  không, ô gom mang kind gì); tuyên bố "mọi tác vụ" thì soát từng cột bảng; tháng viết bằng chữ. (`references/mau.md`
  có test; lượt 7 RAG 0 lỗi, soi 4/4; bài mồi đạt; 2026-10-14)
- [x] `read --render <id>`: cắt hình, bảng ra ảnh để agent nhìn được hình dạng đường cong (chữ trích chỉ có vạch trục).
  (thành lệnh `paper_graph figure`; TM-9..TM-12; bài mồi ảnh đạt; 2026-10-14)

### Mốc 3: trình xem

- [x] HTML tự chứa, chạy offline: tầng đầu, bấm mở tầng dưới, thẻ chi tiết có
  trích dẫn, ảnh cắt đúng đoạn (bản dịch chuyển sang Mốc 4: cần VietPaper).
- [x] Hình và bảng của bài gắn vào ô liên quan.
- [x] Sửa nhãn, khoá ô, kéo thả; giữ toạ độ giữa các lần dựng lại.

### Mốc 4: gắn vào VietPaper

- [ ] Tab "Sơ đồ" cạnh bản dịch; bấm ô thì cuộn hai khung tới đúng đoạn.
- [ ] Thẻ chi tiết của trình xem có bản dịch của câu trích (lấy từ VietPaper).
- [x] Bước dựng bằng API (model local hay OpenRouter) cho người không dùng Claude Code. (`paper_graph build`, OpenRouter;
  model local chưa làm)

### Mốc 5: học bằng cách dựng

- [x] Chế độ "đoán trước rồi mở": ẩn tầng dưới, người đọc ghi dự đoán, rồi so.
- [x] Đo hiểu bài: vài câu hỏi mỗi bài, so đọc chữ với đọc qua sơ đồ. (công cụ, câu hỏi, quy trình)
- [ ] Chạy phép đo với người đọc thật theo `docs/do-hieu-bai.md`, ghi kết quả @ban
