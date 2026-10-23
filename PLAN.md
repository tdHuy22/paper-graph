# paper-graph

Mô tả sản phẩm ở [README.md](README.md); file này chỉ ghi trạng thái công việc.

## §0 Đang ở đâu, việc tiếp theo

Cập nhật 2026-10-23.

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
python3 -m paper_graph check bench/papers/attention/attention.graph.json        # 0 lỗi; 1 cảnh báo PG309 đã biết (Bảng 3)
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
   `.claude/launch.json` vẫn không commit). Không đo thêm model trả phí (bạn chốt
   2026-10-19). Nên đổi khoá OpenRouter (khoá đã nằm trong lịch sử hội thoại; @ban).
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
4. **Bộ câu hỏi lên 12 câu mỗi bài: xong, đã commit** (2026-10-19). q7–q12 của Attention và RAG do agent Opus soạn
   chỉ từ đầu ra `read` (cấm đọc `*.graph.json`, `*.gold.json`, `papers/`), bù hai loại còn thiếu: mỗi bài 2 `limit`,
   1 `detail`, 1 `evidence`, 2 `mechanism`. Mình đối chiếu cả 12 đáp án với nguyên văn: đúng. Cổng chốt việc (rủi ro
   vừa, reviewer sonnet): 0 sai, 4 dễ tranh cãi, 5 nhỏ; sửa cả 9 trừ hai mục chỉ ghi để biết (RAG q7 gần q2, RAG q8 giữ
   ý): viết lại Attention q11 (hướng cho chuỗi dài, bỏ vế "bình phương" không có neo), RAG q9 (số đoạn k thay câu đã lộ
   ở q1, q5), RAG q10 có chủ ngữ, RAG q11 thêm phương án nhiễu về giám sát, nhiễu dè dặt ở hai câu q12, rút đáp án dài.
   Đáp án là phương án dài nhất: Attention 2/12, RAG 3/12. `quiz` 0 lỗi cả hai bài, 221 test đạt (biên nhận); trang
   `papers/rag/rag.quiz.html` xuất lại. `docs/do-hieu-bai.md` ghi nguồn gốc và khác biệt của hai nhóm câu.
5. **Opus 5.5 qua `build` (2026-10-19, bạn bảo chạy RAG, `--max-usd 1.5 --rounds 2`): lượt 1 hỏng, mất 0,902 USD.**
   Câu trả lời bị cắt (`length`), không ghi file nào; tiền thật vượt "ước tối đa" 0,796. Đo bằng lời gọi nhỏ (tổng
   khoảng 0,04 USD): Opus 5.5 trên OpenRouter bắt buộc suy luận và token suy luận ăn vào `max_tokens`; chữ tiếng Việt 1,74
   ký tự/token (code giả định 3). Sửa `build.py` (commit `be3beaa`): ngân sách suy luận riêng 8.000 token (chỉ gửi khi model
   nhận `reasoning`, không vượt `max_completion_tokens`), ước theo 1,5 ký tự/token rồi hiệu chỉnh theo token thật, giá
   ghi cache, thiếu `usage.cost` thì cộng mức ước trên, câu trả lời không đọc được ghi `bai.graph.raw.txt`, lỗi API ở
   lượt sau không làm mất câu trả lời đã trả tiền. Reviewer sonnet: 3 vừa, 4 thấp, sửa cả 7; 7 test mới, 9 đột biến đều
   đỏ; cả bộ test đạt (biên nhận). TM-22 cập nhật, threat model TM-21..25 giờ tham chiếu theo tên hàm. Đã commit
   `be3beaa`. **Chạy lại** (bạn bảo, `--max-usd 1.25`): lại hỏng, 1,062 USD (ước tối đa 1,190 nên trần tiền giữ đúng),
   nhưng Opus dùng 27.705 token suy luận dù gửi `reasoning.max_tokens: 8000`: **Opus 5.5 trên OpenRouter không tuân
   ngân sách suy luận** (lời gọi thử trước chỉ chứng minh tham số được nhận, không chứng minh được tuân). Câu trả lời
   dở được giữ ở `.tmp/build/opus55/rag/rag.graph.raw.txt`; cứu được 38 ô (`rag.partial.graph.json`, không cạnh):
   0 lỗi, 72/72 neo có thật, 0 PG220, phủ 14/14, đúng tầng 93%, soi 1/4 (quan hệ 40% vì mất hết cạnh). So trên RAG:
   Haiku 5.5 13 ô phủ 9/14 (0,014 USD); Nemotron free 22 ô 12/14 (0 USD); DeepSeek V4 Pro 33 ô 14/14 soi 1/4 (0,178
   USD); Opus 5.5 38 ô dở 14/14 soi 1/4 (1,96 USD hai lần, không ra sơ đồ); skill trong Claude Code 50 ô 14/14 soi 4/4.
   Khoá còn 0,20 USD/3. Bạn chốt: không dùng model trả phí trên OpenRouter nữa, chỉ dùng Opus trong Claude Code (mục
   "Quyết định đã chốt").
6. Mời người đọc thật chạy phép đo hiểu bài (`docs/do-hieu-bai.md`, @ban): đủ đồ cho cả hai bài (sơ đồ đã khoá, 12
   câu mỗi bài).
7. **Phép đo thay bằng model (2026-10-19, bạn bảo "làm 6.1 và bạn tự chấm"): không thay được người đọc.** 6 agent
   Sonnet mới, mỗi agent một điều kiện: không đọc / chỉ đọc chữ (`read`) / chỉ đọc `graph.json`, trên Attention và RAG,
   câu hỏi bỏ đáp án, có "Không biết", dặn chỉ dựa vào tài liệu. Kết quả: không đọc 12/12 cả hai bài, đọc chữ 12/12 cả
   hai, đọc sơ đồ RAG 12/12, Attention 9/12 (q6, q10, q12 chọn "Không biết": sơ đồ không có thời gian huấn luyện bản
   lớn, thí nghiệm đổi số đầu, so mã vị trí sin với mã học). Mọi id ô được trích đều có thật. Model đã thuộc cả hai
   bài nên phép đo này không đo được hiểu bài; chỉ cho biết độ đủ thông tin của sơ đồ: RAG đủ cho 12/12 câu, Attention
   thiếu 3 câu `evidence`/`limit`. Đừng thêm ô vào sơ đồ Attention theo ba câu này trước khi đo người thật (sơ đồ sẽ
   bị chỉnh theo đề). Chi tiết: `docs/do-hieu-bai.md` mục "Phép đo thay bằng model"; câu trả lời và script chấm ở
   `.tmp/do-hieu-bai/2026-10-19-model/`. Đã commit `7e6c427` (bạn bảo "commit đi"). Việc 6.1 vẫn mở (@ban).
8. **Xong: thêm hai bài ra sau mốc dữ liệu vào bộ đo, đo lại bằng model** (2026-10-19, bạn duyệt tải). Prism
   Attention (arXiv 2610.22985, CC BY 4.0) và Ignored, Not Refused (arXiv 2610.23254, CC BY-NC-SA 4.0), nộp 16/10/2026;
   PDF ở `bench/pdf/` (không vào git), `bench/papers.json` ghim sha256 và `source`. Gold + quiz do agent Opus soạn chỉ
   từ `read`; sơ đồ do skill dựng (`.tmp/dung-so-do-workspace/iteration-8/`, 48 ô mỗi bài, `check` 0 lỗi 0 cảnh báo).
   Đo (6 agent Sonnet): không đọc Prism 0/12, Ignored 3/12; đọc chữ 12/12 cả hai; đọc sơ đồ 11/12 cả hai. Model hết
   thuộc bài, nhưng đọc chữ vẫn trọn điểm nên phép đo bằng model chỉ đo độ đủ thông tin của sơ đồ, không đo được sơ đồ
   giúp người hiểu nhanh hơn. `score`: Prism phủ 13/13, tầng 77% (sau khi sửa neo `method` của gold), quan hệ 67%, soi
   1/3; Ignored 14/14, tầng 100%, quan hệ 57%, soi 2/4. Cổng chốt việc (rủi ro vừa, reviewer sonnet): 0 đáp án sai,
   1 vừa (neo `method` quá hẹp, đã sửa), 3 thấp (test quiz thiếu hai bài, docs "năm bài" và nguồn PDF, lời giải thích
   lệch nhẹ), sửa cả 4. 228 test đạt (biên nhận). Chi tiết: `docs/do-hieu-bai.md` "Lượt 2". Đã commit (bạn bảo "commit đi", 2026-10-20).
   Phát hiện phụ: `read --find` không tìm trong chữ của vùng bảng. (Đã sửa ở mục 9.)
9. **Cải tiến pipeline, đợt 1** (2026-10-20, bạn bảo "vẫn chưa cải thiện pipeline xong"; đã commit, bạn bảo "commit đợt 1").
   - `read --find` tìm cả trong chữ của vùng bảng, biểu đồ, in rõ là không làm câu trích được (`reader._figure_hits`).
   - Luật mới PG309 (cảnh báo): bảng, biểu đồ có chú thích đánh số, nằm trước tài liệu tham khảo, mà không ô nào nói
     tới (`check._unlinked_figures`, dùng `figlinks.link`). Trên các sơ đồ cũ: Attention báo Bảng 3 (đúng chỗ thiếu q10
     của lượt đo), RAG Hình 3, Prism Hình 6, RoFormer lượt 4 Bảng 3, DataSentinel Hình 3–5; Ignored không báo. Sơ đồ mẫu
     Attention giữ nguyên tới khi đo người thật (test `KNOWN`).
   - SKILL.md theo góp ý của hai agent dựng lượt 8: mỗi RQ một ô `result`; một ô bằng chứng nối nhiều tuyên bố cùng
     tầng; tầng đầy thì nhắc tên bảng phụ trong `explain`; PG220 so cả đoạn được neo; liệt kê tên thay số đếm; số trong
     tên cột bảng không tính; `fmt` viết lại file; PG309. Thêm một câu rút từ lượt đo (tên bài tự đặt phải nói nghĩa):
     từ nay Prism và Ignored đã dùng để sửa skill, đo skill mới cần bài mới.
   - Test: 3 test mới (PG309 hai ca, `find` trong bảng); 231 test đạt trên hai Python (biên nhận; một lần chạy trước đó
     chết lúc tắt mã -6, lỗi onnxruntime đã biết, chạy lại đạt).
   - Còn trong danh sách cải tiến: `build` dựng theo từng tầng (lớn, cần kế hoạch); chặn cứng lệnh mạng cho agent dựng
     (`permissions.deny`, cần bạn duyệt vì đổi cấu hình).
10. **Kế hoạch `build` dựng theo từng tầng: bạn chốt cả 4 câu theo khuyến nghị** (2026-10-20, "chốt theo khuyến nghị
    cả 4 câu … làm đi"; trang đã ghi quyết định). Trang:
    https://claude.ai/artifact/VzGQsV8T99U1fMmi1hahP1 — ba phương án (A khung rồi mở từng ô, khuyên; B một lượt sửa
    bằng bản vá; C theo từng mục), bốn câu chốt: phương án; lượt mở gửi toàn văn hay chỉ trang liên quan (khuyên toàn
    văn); giữ cách cũ sau một cờ để so (khuyên giữ); đo 3 bài RAG, DataSentinel, Prism bằng Nemotron free (khoảng 45
    lượt, sát hạn mức 50 lượt mỗi ngày của model free khi tổng nạp dưới 9 USD). Dùng lại: không có công cụ sẵn; kỹ
    thuật dàn khung rồi mở rộng (Skeleton-of-Thought 2023, OmniThink 2025), tự viết trong `build.py`. Đọc bình luận
    trên trang bằng ArtifactComments trước khi làm.
11. **`build --mode tiers`: xong code, đo xong, chưa thắng cách cũ** (2026-10-20). Code: `_Caller` dùng
    chung (ước tiền, thử lại, trần tiền, trần `--max-calls` kể cả thử lại), `run_tiers` (khung → mở từng ô tới sâu 3 →
    lượt soát PG305/PG309), `--mode one-shot` giữ cách cũ; mặc định đang là tiers. Threat model TM-26..28 `đã có`.
    Reviewer sonnet: 4 vừa, 5 thấp, sửa cả 9 (id không băm được làm sập; id sai mẫu lọt; dừng giữa lượt sửa khung mất
    khung; dựng lại với ô khoá ở tầng dưới; …), 16 test lớp `Tiers`, đột biến các chốt chặn đều đỏ; 247 test đạt hai
    Python (biên nhận). Đo (Nemotron free, khoảng 40 lượt, 0 USD; docs/bench.md mục cuối): tiers phủ RAG 14/14,
    DataSentinel 13/13, Prism 11/13; một lượt 12/14, 11/13, 13/13; đủ thông tin Prism 5/12 so với 6/12 (skill 11/12).
    Tiêu chí đặt trước chưa đạt (thua ở Prism). Phát hiện: sơ đồ không dày hơn (21–24 ô) vì model chỉ đánh dấu 2–3 ô
    cần mở, không phải vì câu trả lời quá dài. Trang kế hoạch ghi kết quả. Còn treo (@ban): thử tiếp bản chương trình
    tự mở mọi ô tầng đầu (trừ vấn đề), hay dừng và để one-shot làm mặc định; đã commit (bạn bảo "commit đợt này").
12. **Đang dở: tiers v2, chương trình tự mở mọi ô tầng đầu trừ ô vấn đề** (2026-10-20, bạn bảo; code chưa commit).
    Code: `run_tiers` chọn ô mở ở tầng đầu (`kind != problem`), `expand` của model chỉ còn cho tầng sâu hơn; 2 test mới,
    đột biến làm đỏ; 248 test đạt hai Python (biên nhận). Tài khoản OpenRouter đã nạp 10 USD nên model free được 1.000
    lượt/ngày (bạn nói 2026-10-20). Đo (`.tmp/build/2026-10-21-tiers2/`, Nemotron free, `--max-calls 16`): RAG 35 ô, phủ
    12/14, tầng 79%, quan hệ 80%, soi 0/4 (chạm trần 16 lượt); DataSentinel 35 ô, phủ 12/13, tầng 92%, quan hệ 60%, soi 0/2
    (dừng vì OpenRouter 504); Prism lần 3 (21/10) chạy được: 37 ô, phủ 13/13, tầng 100%, quan hệ 100%, soi 0/3, đủ thông tin 8/12 (v1 5, một lượt 6, skill 11); hai lần trước hỏng ở lượt khung (504). Nhận xét sơ bộ: sơ đồ dày
    hơn (35 ô so với 24 của tiers v1, 20–21 của one-shot) nhưng độ phủ không tăng (v1: 14/14, 13/13). Mốc so: one-shot
    ngày 20/10 ở `.tmp/build/2026-10-20/oneshot/`, tiers v1 ở `.tmp/build/2026-10-20/tiers/`, bảng ở docs/bench.md mục
    cuối. Tiếp: chạy lại Prism lúc nhà cung cấp bớt tải (`python3 -m paper_graph build .tmp/build/2026-10-21-tiers2/prism/prism.blocks.json --allow-training --mode tiers --max-calls 16`), chấm (`score`, rồi agent Sonnet chỉ đọc sơ đồ làm 12 câu của `prism.quiz.json` như mục
    11, câu hỏi ở `.tmp/do-hieu-bai/2026-10-20-build/prism.questions.md`), ghi bảng v2 vào docs/bench.md, hỏi bạn chọn
    mặc định (one-shot, tiers v1 hay v2) rồi commit.
13. **Lượt đối chiếu chỗ bài tự lệch: xong, tác dụng nhỏ** (2026-10-21, bạn bảo "tiếp tục cải thiện"; chưa commit).
    Code: `build.py` `AUDIT_TASK`, `_add` (dùng chung cho lượt soát và đối chiếu, có 1 lượt sửa cho phần thêm còn lỗi),
    `_checked`; `run_tiers` chạy đối chiếu cuối cùng khi sơ đồ 0 lỗi. Test `Audit` (ô chỗ lệch có thật được giữ, ô bịa số
    được gửi lại sửa rồi bỏ). Đo riêng trên 3 sơ đồ v2: 1 ô đúng (Prism, 3,4× chỉ ở batch 16), soi vẫn 0/4, 0/2, 0/3
    (điểm soi Prism đòi thêm số 1,15×); docs/bench.md mục cuối. Còn treo (@ban): chọn mặc định của `build` (v2 hay
    one-shot), commit v2 + đối chiếu.
14. **Lần đo chốt: đạt tiêu chí, đã commit** (2026-10-21, bạn bảo "làm cho đạt tiêu chí rồi mới commit"). Đổi:
    `MAX_CALLS`/`--max-calls` mặc định 24, `_add` 2 lượt sửa, lời dặn đối chiếu nêu cả số ở điều kiện kia. Một lần chạy
    mỗi bài (`.tmp/build/2026-10-21-final/`): phủ RAG 14/14, DataSentinel 12/13, Prism 13/13 so với one-shot 12/14, 11/13,
    13/13; soi ngang (0/4, 1/2, 0/3). Tiêu chí đặt trước đạt; giới hạn và chi phí (15–18 lượt mỗi bài) ở docs/bench.md mục
    cuối. 249 test đạt (biên nhận). Tiers giữ làm mặc định. Còn mở: điểm soi model free vẫn thấp (phần thêm của lượt đối
    chiếu thường còn lỗi neo).
15. **Xong: bài mới thứ ba cho bộ đo skill** (2026-10-21, bạn duyệt tải). Merging (arXiv 2610.22999, 13 trang,
    `bench/pdf/merging-diversity.pdf`, ghim sha256 và `source` trong `bench/papers.json`; `prepare.py`: 237 đoạn). Đang
    chạy hai agent Opus: soạn gold + quiz chỉ từ `read` (ghi `.tmp/stage/merging/`), dựng sơ đồ bằng skill sau sửa 20/10
    (`.tmp/dung-so-do-workspace/iteration-9/merging/`). Xong: gold (13 must, 7 tuỳ chọn, 4 probes) và quiz 12 câu chép vào
    `bench/papers/merging/`, `test_quiz` kiểm thêm bài này, 249 test đạt (biên nhận). Sơ đồ skill: 50 ô, check 0 lỗi 2
    cảnh báo có lý do; `score` phủ 13/13, đúng tầng 69% (sơ đồ tách hai ô result, gold có một), quan hệ 86%, soi 3/4.
    Đo hiểu bài: không đọc 0/12, đọc chữ 12/12, đọc sơ đồ 12/12 (docs/do-hieu-bai.md "Lượt 3"). Đã commit `d537633` (bạn bảo
    "commit đi"). Góp ý của agent dựng cho skill: tên mô hình có dấu cách ("Qwen 2.5") dính
    PG220; PG303 + PG305 cho ô "chỗ lệch" không cạnh; hình nhiều mảnh nên gắn id nào.
16. **Bỏ việc chặn cứng lệnh mạng** (2026-10-21, bạn chốt: Claude Code thì không cần, `build` qua API cũng không vì
    model không có công cụ). Ghi lý do ở `.agent/threat-model.md` cuối file (TM-6 chấp nhận rủi ro còn lại). Mốc 6 xong.
    Đã commit cùng mục 17. Việc tiếp: 5.1, 5.2 chờ phiên VietPaper commit xong; 6.1 cần bạn mời người
    đọc thật.
17. **6.1: bộ đồ đo người đọc thật đã sẵn, chờ bạn mời người** (2026-10-21, bạn bảo "làm 6.1"; đã commit, thư mục gửi đi không vào git). Thư mục
    gửi đi `papers/do-hieu-bai/goi/` (PDF, sơ đồ, trang câu hỏi của Attention và RAG, `HUONG-DAN.md`; không vào git,
    khoảng 7 MB), hướng dẫn người đọc `docs/huong-dan-nguoi-doc.md`, cách gom và chấm ở docs/do-hieu-bai.md "Bộ đồ đã
    sẵn". Script chấm `bench/hieu_bai.py` (chấm lại từ câu trả lời, trung vị và hơn/kém/bằng theo nhóm, theo loại câu),
    3 test; 252 test đạt (biên nhận). Trang câu hỏi mở được trong trình duyệt, console sạch. Tiếp (@ban): mời người đọc,
    chia nhóm A, B xen kẽ, gom dòng kết quả vào một file `.jsonl`, rồi nhờ mình chạy `python3 bench/hieu_bai.py`.
18. **Mô phỏng người đọc bằng model** (2026-10-21, bạn bảo "tự AI đọc luôn rồi đánh giá luôn"; đã commit). Agent đọc
    ghi chú tối đa 250 chữ, agent mới trả lời chỉ từ ghi chú; Prism, Ignored, Merging. Đọc sơ đồ 25/36, đọc chữ 21/36
    (+2, −1, +3), hơn chủ yếu ở câu cơ chế. Một lần mỗi ô, nên chưa chắc. Chi tiết docs/do-hieu-bai.md mục cuối. 6.1
    (người thật) vẫn mở.
19. **6.1 làm bằng người đọc AI** (2026-10-22, bạn chốt "6.1 sử dụng AI đánh giá", Sonnet medium; đã commit). Đổi
    chéo 6 người đọc × 3 bài (Prism, Ignored, Merging), ghi chú tối đa 250 chữ, agent khác trả lời chỉ từ ghi chú. Đọc
    sơ đồ 66/108, đọc chữ 61/108; trung vị theo người +0,5 câu mỗi bài, 5 hơn 1 kém; hơn chủ yếu ở câu cơ chế và chi
    tiết. Mức hơn nhỏ hơn biến động giữa người đọc. Chi tiết docs/do-hieu-bai.md mục cuối. 6.1 tick.
20. **Xong: hoàn thiện đường API (`build`)** (2026-10-22, bạn bảo "làm cho hoàn chỉnh và tốt nhất, phải dùng được
    API"; chưa commit, cùng kết quả 6.1 ở mục 19). Xong: PG220 nhận tên mô hình có dấu cách lặp trong bài (`numbers.
    name_pairs`, test); SKILL.md: ô chỗ lệch để PG303/PG305 có lý do, hình nhiều mảnh gắn id nào; model `:free` thử lại 4
    lần chờ 10–80 giây khi 504 (test); đối chiếu từng câu tuyên bố có số của tóm tắt và kết luận (`_claims`,
    `AUDIT_CLAIM`, tối đa 6 câu), `--max-calls` mặc định 32 (TM-27, README). Đang chạy nền: so 4 model free
    (`.tmp/build/2026-10-22-models/`, Inkling bị OpenRouter từ chối: chỉ cho ứng dụng agent) và đối chiếu từng câu trên 3
    sơ đồ 21/10 (`.tmp/build/2026-10-22-audit/`). Lưu ý: lượt so model, RAG chạy code trước khi có đối chiếu từng câu,
    DataSentinel và Prism chạy code mới. Kết quả so model (docs/bench.md "So model free"): Dots 3 phủ 14/14, 13/13, 13/13, tầng 100% cả ba; Nemotron
    3.5 RAG 12/14, 71%; Gemma 4, Nemotron Ultra, Inkling hỏng (429, 502, 403). Đã đặt `DEFAULT_MODEL` = dots-3, dự
    phòng Nemotron 3.5 rồi 3 Super 120B (`_Caller.fallbacks`, `--fallback`, `--no-fallback`, chỉ :free); lượt đối chiếu
    gắn neo câu tuyên bố tự động và bỏ riêng neo hỏng (`_drop_bad_anchors`); threat model ghi bổ sung. Bản phát triển ở
    `../paper-graph-dev` (đã chép vào repo). 252+ test đạt. Đang chạy: reviewer sonnet; đo lượt đối chiếu mới trên sơ đồ
    Dots 3 (`.tmp/build/2026-10-23-audit/`). Review sonnet: 3 vừa, 4 thấp, sửa cả 7 (neo chương trình
    che neo bịa; "BLEU 28.4" lặp thành tên; 429 hết hạn mức ngày thử lại 15 lượt; dự phòng dùng giới hạn của model chính;
    câu tuyên bố trong tin nhắn chỉ dẫn; `_claims` đếm số trích dẫn; thiếu test CLI), ghi ở threat model; 259 test đạt
    (biên nhận). Đối chiếu bằng code đã sửa trên sơ đồ Dots 3: RAG thêm 1 ô chỗ lệch đúng ("ba" so với "bốn" tập QA), điểm soi
    không đổi (1 trên 9); docs/bench.md mục cuối. Đã commit (bạn bảo "commit đi").

21. **Xong: Mốc 7, nâng cấp toàn diện** (2026-10-23, bạn bảo "lên kế hoạch cải thiện và nâng cấp toàn diện rồi
    làm đi"; xuất phát từ `4a6e44e`, 259 test đạt). Thứ tự: (1) `build` mở các nhánh song song, Dots 3 mất ~30 phút một
    bài vì mở tuần tự; (2) bộ chấm "đúng tầng" nhận ý tầng đầu tách thành nhiều ô cùng loại (Prism, Merging bị chấm
    thấp oan); (3) đo Dots 3 trên 5 bài có đáp án, mỗi bài 2 lần, chạy nền; (4) `build` gọi model chạy trên máy (Ollama,
    LM Studio; chỉ localhost) cho bài riêng tư, threat model trước; (5) kiểm VietPaper, làm Mốc 4 nếu phiên kia đã
    commit; (6) review, docs, hỏi commit. Soi bằng hai model free để sau cùng (tốn gấp đôi, chưa chắc có lợi).
    Tiến độ: (1) xong: `--workers` (mặc định 4), `_Caller` khoá `_mu`, giữ chỗ tiền `pending`, đếm lượt dưới khoá,
    một luồng chuyển dự phòng; `_rename`, `gather`, `add_many` (đối chiếu chạy theo đợt: tóm tắt rồi kết luận); test
    `Parallel`, `Rename`; RAG chạy thật 4 luồng qua hết các nhánh trong 14 phút (tuần tự 22/10: 35 phút). (2) xong: ô đại
    diện của ý tầng đầu (`score.py`); chấm lại 61 sơ đồ: 13 đổi, độ phủ không đổi, sơ đồ có ý sai tầng 19 → 6
    (docs/bench.md mục cuối). (4) xong phần code: `--local URL` (TM-29..TM-32 trong threat model), test `Local` với máy
    chủ HTTP thật trên 127.0.0.1, 7 đột biến chốt chặn đều làm đỏ; máy chưa có Ollama nên chưa thử model thật. (5) VietPaper
    còn 2 file sửa chưa commit của phiên kia (`.agent/threat-model.md`, `scripts/smoke_features.py`) và `HANDOFF.md`:
    không đụng. Mốc kiểm tra `check --strict` Attention trượt từ `2f3d14a` vì PG309 (Bảng 3, đã biết): bỏ `--strict`.
    276 test đạt (biên nhận). Bản chạy thử RAG 4 luồng xong: 19 phút (tuần tự 35), 0 lỗi, phủ 12/14 vì nhánh `result` và
    `limit` bị bỏ cả nhánh khi chỉ còn 1 PG220 (dao động của model, không do song song) → sửa: `_drop_pg220` + `salvage`
    trong `run_tiers` bỏ đúng ô còn PG220 nếu phần còn lại sạch (test `test_only_the_cell_with_a_made_up_number_is_dropped`,
    `test_branch_with_an_error_is_still_dropped_whole`; đột biến tắt làm đỏ; README ghi). Review opus lượt 1: 0 cao, 3 vừa,
    3 thấp, sửa cả 6 (Ctrl+C không dừng → 1 luồng chạy ở luồng chính, nhiều luồng `_Pool` daemon + `_Caller.cancel`, SIGINT
    thật dừng ở 2,5 giây; dừng oan vì tiền đang giữ chỗ → chờ trên `_cv`; LM Studio gửi lại `response_format` mỗi lượt →
    `json_mode`; quan hệ của một ô với chính nó → `x != y`, chấm lại: 19/61 sơ đồ đổi, 6 sơ đồ build tụt quan hệ đúng
    như vậy; 1 luồng đổi thứ tự đối chiếu; `--workers 0`), TM-32 thêm hỏi ngữ cảnh máy chủ và dấu hiệu token đứng yên
    (ngưỡng 8 → 5); chi tiết ở threat model. 9 đột biến chốt chặn, 8 làm đỏ (1 còn lại có chốt dự phòng). Bộ test đầy
    đủ đạt (biên nhận, 69,6 giây). Review opus lượt 2: 1 vừa (hai lượt trả phí cùng hết giờ thì chờ nhau mãi → lượt thử
    lại trả chỗ rồi xin lại), 1 thấp (`/api/ps` lạ), 2 nghi ngờ (Ollama bỏ nguyên tin nhắn chữ bài khi quá ngữ cảnh → ở
    `--local` chữ bài vào tin nhắn system, kiểm trước khi gửi; "token đứng yên" báo nhầm → chỉ khi gần như bằng hẳn); sửa
    cả 4, test và đột biến đều đỏ khi bỏ chốt; bộ test đạt (biên nhận, 93,8 giây); tái hiện `--local` qua CLI đạt.
    (3) xong: đo Dots 3, 5 bài × 2 lần (`.tmp/build/2026-10-23-measure/`, docs/bench.md mục cuối): 10/10 lần 0 lỗi, ghi
    `graph.json`; phủ 131/134 (98%), soi 9/34 (lần 22/10: 1/9); Ignored, Merging phủ ngang skill Opus; 21 phút mỗi bài khi
    hai lần đo chạy cùng lúc (tuần tự 30); cứu nhánh dùng 3 lần; nhánh kết quả bị bỏ 3/10 lần (chỗ yếu tiếp theo).
    Chưa commit. Tiếp: hỏi commit Mốc 7. Treo: thử model thật với `--local` cần cài
    Ollama (@ban); TM-30 chấp nhận rủi ro cổng loopback trên máy dùng chung (@ban); Mốc 4 VietPaper chờ repo kia sạch.

### Quyết định đã chốt (bạn chốt 2026-10-12: "chốt hết", theo phương án khuyên)

- **Q1 B, đổi 2026-10-16.** Repo riêng gồm lõi (định dạng file, bộ kiểm, bước dựng) và trình xem. Ban đầu VietPaper
  chỉ thêm lớp nối mỏng; nay VietPaper dùng paper-graph như thư viện (`pip install -e ../paper-graph`), có đủ tính
  năng trong VietPaper (xem, sửa, dựng), paper-graph vẫn chạy độc lập.
- **Q2 a.** Skill Claude Code dựng sơ đồ trước; bước gọi API trong app sau, khi đã
  có bộ đo.
- **Q3 i.** Một sơ đồ nhiều tầng, mỗi tầng tối đa 9 ô, bấm để mở tầng dưới.
- **Q4 x.** Mốc đầu: xem, mở nguồn, sửa, khoá; chế độ "đoán trước rồi mở" ở mốc 5.

- **Không dùng model trả phí trên OpenRouter** (bạn chốt 2026-10-19, sau hai lượt Opus 5.5 hỏng, mất 1,96 USD). Dựng
  sơ đồ bằng skill dung-so-do với Opus trong Claude Code; `build` qua OpenRouter chỉ còn dùng model `:free` (mặc định
  Nemotron free). Không đo thêm DeepSeek, không sửa `build` cho model trả phí.

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
- [x] Chạy phép đo theo `docs/do-hieu-bai.md`, ghi kết quả: làm bằng người đọc AI theo bạn chốt 2026-10-22 (sơ đồ 66/108, chữ 61/108; bộ đồ cho người thật vẫn sẵn)

### Mốc 6: cải thiện pipeline (từ 2026-10-19)

- [x] Phép đo hiểu bài thay bằng model; thêm hai bài ra sau mốc dữ liệu (Prism, Ignored) vào bộ đo. (`7e6c427`, `4e70365`)
- [x] Luật PG309 cho bảng kết quả bị bỏ sót; `read --find` tìm cả chữ trong bảng; SKILL.md theo góp ý agent dựng. (`2f3d14a`)
- [x] `build --mode tiers`: dựng từng tầng, giữ one-shot để so. (`3da16cc`)
- [x] `build` theo tầng đạt tiêu chí so với one-shot trên RAG, DataSentinel, Prism (v2 tự mở ô tầng đầu, lượt đối chiếu; lần đo chốt 21/10)
- [x] ~~Chặn cứng lệnh mạng cho agent dựng sơ đồ (`permissions.deny`)~~: bỏ, bạn chốt 2026-10-21 không cần (chấp nhận rủi ro; `build` không có công cụ nên không liên quan)
- [x] Bài mới thứ ba cho bộ đo skill: Prism và Ignored đã dùng để sửa skill ngày 20/10, đo skill mới cần bài chưa dùng (Merging, 21/10)

### Mốc 7: nâng cấp toàn diện (từ 2026-10-23)

- [x] `build` mở các nhánh song song (`--workers`; khoá bộ đếm lượt, giữ chỗ tiền; id trùng giữa hai nhánh thì đổi id). (23/10)
- [x] Bộ chấm "đúng tầng" nhận ý tầng đầu tách thành nhiều ô cùng loại; quan hệ không tính một ô với chính nó. (23/10)
- [x] Đo Dots 3 trên 5 bài có đáp án, mỗi bài 2 lần: phủ 98%, soi 9/34, 0 lỗi cả 10 lần. (23/10)
- [x] `build --local` gọi model chạy trên máy (Ollama, LM Studio; chỉ localhost) cho bài riêng tư. (23/10; kiểm bằng máy chủ giả, chưa thử model thật)
- [ ] Thử `--local` với Ollama thật trên một bài (cần cài Ollama và một model). @ban
- [ ] Nhánh kết quả bị bỏ 3/10 lần vì còn lỗi neo sau 3 lượt sửa: xem lỗi nào lặp, sửa chỉ dẫn hay bước cứu.
- [ ] Soi bằng hai model free (đối chiếu chéo), làm sau cùng nếu còn đáng.
