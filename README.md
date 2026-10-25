# paper-graph

Đọc bài báo bằng mắt trước, bằng chữ sau.

Mỗi bài báo thành một sơ đồ nhiều tầng: tầng đầu chỉ 5–7 ô (vấn đề, ý then
chốt, phương pháp, kết quả, giới hạn), bấm một ô thì mở ra tầng dưới (các bước
của phương pháp, tuyên bố nối với bảng hay hình làm bằng chứng, các khái niệm).
Nhãn bằng tiếng Việt, kèm thuật ngữ gốc. Mỗi ô **neo về đúng câu trong bài**:
bấm vào là thấy đoạn gốc và bản dịch, và ô nào không neo được thì không được
vẽ như sự thật.

## Ghép từ đâu

| Lấy từ | Phần dùng lại |
| --- | --- |
| [pdf-translator](../pdf-translator) (VietPaper) | trích đoạn kèm toạ độ (PP-DocLayoutV3), OCR cho bản scan, bảng thuật ngữ Anh–Việt, bản dịch từng đoạn, cắt hình và bảng của bài |
| [archctl](../archctl) | sơ đồ là một file kiểm được; bộ kiểm báo khai báo không có thật trong nguồn; layout xác định và giữ chỗ cũ; giao diện SVG tự chứa, tự cập nhật; người khoá, máy đề xuất |
| skill `paper-anatomy` | thẻ neo §mục · trang · trích nguyên văn, và script kiểm neo |

Phần mới thật sự: bước dựng đồ thị từ các đoạn của bài, định dạng file sơ đồ,
bộ kiểm neo cho node và cạnh, và trình xem nhiều tầng.

## Dùng

```bash
# 1. PDF → các đoạn kèm toạ độ (chạy bằng Python của VietPaper vì cần PyMuPDF và model bố cục)
../pdf-translator/.venv/bin/python -m paper_graph extract bai.pdf            # → bai.blocks.json
../pdf-translator/.venv/bin/python -m paper_graph extract scan.pdf --ocr     # bản scan

# 2. Kiểm sơ đồ: dạng file, mọi neo có thật ở đúng trang, mỗi tầng tối đa 9 ô
python3 -m paper_graph check bai.graph.json
python3 -m paper_graph check bai.graph.json --pdf bai.pdf --json --strict

# 3. Chắc blocks.json đúng là trích từ PDF này, không bị sửa tay (`--pdf` ở trên chỉ so mã băm)
../pdf-translator/.venv/bin/python -m paper_graph verify-blocks bai.pdf bai.blocks.json

# Đọc bài theo trang, mỗi đoạn kèm id, để chép câu trích; tìm một cụm ở trang nào
python3 -m paper_graph read bai.blocks.json --pages 1-5
python3 -m paper_graph read bai.blocks.json --find "N = 6 identical layers"     # tìm cả trong chữ của bảng
../pdf-translator/.venv/bin/python -m paper_graph figure bai.blocks.json p8-f1   # cắt hình ra bai.figures/p8-f1.png
../pdf-translator/.venv/bin/python -m paper_graph view bai.graph.json            # trình xem bai.html, chạy offline
../pdf-translator/.venv/bin/python -m paper_graph serve bai.graph.json           # trình xem có chế độ sửa, http://127.0.0.1:8742/
python3 -m paper_graph fmt bai.graph.json                                       # định dạng chung: mỗi ô một dòng
python3 -m paper_graph quiz bai.quiz.json                                       # câu hỏi hiểu bài → trang làm bài
python3 -m paper_graph build bai.blocks.json --allow-training                  # dựng sơ đồ bằng model miễn phí qua OpenRouter
python3 -m paper_graph build bai.blocks.json --local http://localhost:11434/v1  # dựng bằng model trên máy (Ollama), bài riêng tư
```

`view` ghi một file HTML tự chứa: tầng đầu, bấm ô để xem giải thích và câu trích nguyên văn (kèm ảnh đoạn gốc),
ô có ▸ mở ra tầng dưới. Thẻ của ô hiện các hình, bảng liên quan, kèm lý do gắn: trường `figure` của ô, câu trích nằm ở
chú thích, ô nhắc "Bảng 2", hình của ô bằng chứng nối vào, hay hình ở tầng dưới. Bấm hình để phóng to; nút "Hình và
bảng" liệt kê mọi hình của bài kèm các ô dùng nó. Nút "Tự đoán trước" bật chế độ học: mở một ô có tầng dưới thì trang hỏi
bạn nghĩ tầng dưới có gì trước, rồi đặt dự đoán cạnh các ô thật để bạn tự tick ý đã đoán trúng (lưu trong trình duyệt,
theo bài). Tự viết ra trước khi xem giúp hiểu và nhớ hơn chỉ xem sơ đồ dựng sẵn. Chạy bằng `python3` thường cũng được, chỉ là không có ảnh (cắt ảnh
cần PyMuPDF). Sơ đồ phải qua `check` 0 lỗi mới xuất được.

`serve` mở cùng trình xem trên máy chủ cục bộ (chỉ 127.0.0.1) và cho sửa: sửa nhãn, thuật ngữ, giải thích trong thẻ
(ô thành `accepted`; sửa đổi phải qua `check` và không được thêm số không có trong bài), khoá hay mở khoá ô, kéo ô tới
chỗ khác (bàn phím: Alt + mũi tên), "Dàn lại tầng này". Nội dung ghi vào `bai.graph.json`; toạ độ ghi vào
`bai.layout.json` cạnh đó, nên dựng lại sơ đồ không mất chỗ các ô đã kéo (ô còn id thì còn chỗ), và `view` cũng
dùng toạ độ này. Sơ đồ trên đĩa đổi trong lúc trang đang mở (ví dụ vừa dựng lại) thì trang báo tải lại, không ghi đè.

Dựng sơ đồ không cần Claude Code: `build` gửi chữ bài và chỉ dẫn (lấy từ skill dung-so-do) tới một model qua
OpenRouter, chạy `check`, gửi lỗi lại cho model sửa. Mặc định (`--mode tiers`) dựng từng tầng một: lượt đầu xin tầng
đầu, mỗi ô tầng đầu trừ ô vấn đề có một lượt riêng xin tầng dưới của nó, ô con model đánh dấu cần mở thì mở tiếp (tới
độ sâu 3), mỗi phần được kiểm và sửa
riêng tối đa `--rounds` lượt (mặc định 3), phần còn lỗi thì bỏ để phần đã đạt không bị kéo theo (ở nhánh, chương trình bỏ câu trích hỏng của ô còn câu trích tốt, rồi bỏ đúng ô còn lỗi hay số không có trong đoạn được neo, PG220; khung còn lỗi thì xin lại khung từ đầu một lần, vẫn lỗi thì thành nháp); cuối cùng một lượt
soát thêm ô cho tuyên bố thiếu bằng chứng (PG305) và bảng không ô nào nói tới (PG309), rồi đối chiếu từng
câu tuyên bố có số hay có phạm vi của tóm tắt và kết luận (chương trình chọn câu, tối đa 6) với bảng, thêm ô "Chỗ lệch:"
khi bài tự nói khác bảng. Các nhánh, và các câu tuyên bố của cùng một mục, chạy cùng lúc (`--workers`, mặc định 4;
mỗi lượt thấy sơ đồ lúc nó bắt đầu, chương trình đổi id trùng giữa hai nhánh rồi kiểm lại phần gộp). Chương trình tự đặt `parent`
của mỗi phần và bỏ ô trùng id, nên một lượt không ghi được ra ngoài nhánh của nó. Trần số lượt gọi cả lần chạy
`--max-calls` (mặc định 32, kể cả thử lại; còn 8 lượt trước trần thì thôi mở tầng thứ ba để còn lượt soát, đối chiếu; một bài thường cần 20–30 lượt; model miễn phí của OpenRouter cho 50 lượt mỗi
ngày khi tổng tín dụng đã nạp dưới 9 USD, 1.000 lượt khi từ 9 USD trở lên). `--mode one-shot` là cách cũ (cả sơ đồ trong một câu trả lời), giữ để so. Trần tiền `--max-usd` (mặc định
0,5 USD) tính cho cả lần chạy. Model mặc định là `dots-studio/dots-3-note-preview:free` (so 5 model free ngày 22/10,
docs/bench.md); nó lỗi mãi thì lệnh tự chuyển sang model free dự phòng (`--fallback`, `--no-fallback`). Đạt (0 lỗi, không PG220) thì ghi `bai.graph.json`, chưa đạt thì `bai.graph.draft.json`; câu trả lời
không đọc được thành sơ đồ (bị cắt, không phải JSON) vẫn ghi ra `bai.graph.raw.txt`. Trước mỗi lượt lệnh in mức tiền
ước tối đa (tính cả token suy luận, tối đa 8.000; chữ tiếng Việt khoảng 1,7 ký tự mỗi token): model đắt như Opus cần
nâng `--max-usd`, khoảng 1 USD mỗi lượt với một bài 20 trang. Khoá lấy từ biến
`OPENROUTER_API_KEY` hay file `~/.config/paper-graph/openrouter.key` (quyền 600); không có cờ nhận khoá. Request đặt
`data_collection: deny` (nhà cung cấp không lưu, không huấn luyện), nhưng chữ bài vẫn rời máy: bài riêng tư thì dựng
bằng skill hay model trên máy (dưới đây). Đã có `bai.graph.json` thì phải `--force`, và ô đã khoá phải giữ nguyên. Model miễn phí (`…:free`) chỉ chạy khi cho
nhà cung cấp huấn luyện trên chữ gửi đi: bật "Free model training" trong cài đặt OpenRouter và thêm `--allow-training`
(chỉ nhận model `:free`); chỉ dùng cho bài đã công khai.

Model trên máy (`--local URL`): cùng cách dựng theo tầng, gửi tới máy chủ model chạy trên chính máy này qua API kiểu
OpenAI, ví dụ Ollama (`http://localhost:11434/v1`) hay LM Studio (`http://localhost:1234/v1`). Lệnh chỉ nhận
`localhost`, `127.0.0.1`, `[::1]`, không qua proxy, không theo redirect, không đọc khoá OpenRouter; không có `--model` thì
dùng model duy nhất máy chủ đang có. Mặc định một lượt mỗi lúc (một GPU xếp hàng các request), mỗi lượt chờ tối đa 30
phút. Bài 20 trang cần ngữ cảnh 30–60 nghìn token, mà Ollama mặc định chỉ 4.096 và lặng lẽ cắt phần đầu: đặt
`OLLAMA_CONTEXT_LENGTH=65536` trước `ollama serve` (LM Studio: Context Length khi nạp model). Chữ bài đi trong tin nhắn
system (Ollama quá ngữ cảnh thì bỏ nguyên tin nhắn cũ nhất trừ tin nhắn system). Lệnh dừng khi thấy chữ bị cắt: số token
máy chủ đọc chạm độ dài ngữ cảnh nó báo (Ollama `/api/ps`, LM Studio `/api/v0/models`), số token đứng yên trong khi chữ
gửi đi đổi, hay quá 5 ký tự mỗi token; khi đã biết ngữ cảnh, lượt chắc không vừa bị từ chối trước khi gửi. Đối chiếu
tài liệu ngày 23/10: Ollama nhận `response_format: json_object`, luôn trả `usage.prompt_tokens`, `/api/ps` có
`context_length`; LM Studio báo `loaded_context_length` ở API v0 (từ 0.3.6) và báo lỗi thay vì cắt khi quá ngữ cảnh.
Chưa chạy với Ollama hay LM Studio thật, chỉ với máy chủ giả cùng định dạng (test `Local`). Máy chủ không báo ngữ cảnh thì chỗ cắt nhỏ (dưới khoảng một phần
tư) có thể lọt. Máy dùng chung với người khác thì cổng loopback không riêng tư.

Đo người đọc có hiểu hơn khi đọc qua sơ đồ không: bộ câu hỏi `bai.quiz.json` (mỗi câu neo về câu trích có thật),
lệnh `quiz` xuất trang làm bài tự chấm; quy trình đo đổi chéo ở [docs/do-hieu-bai.md](docs/do-hieu-bai.md).

Dựng sơ đồ: trong repo này, nhờ Claude Code "dựng sơ đồ cho bài X". Skill
[dung-so-do](.claude/skills/dung-so-do/SKILL.md) đọc bài bằng `read`, viết `bai.graph.json`, chạy `check` và sửa tới khi
đạt. Mỗi con số trong ô phải có trong đoạn được neo (PG220); ô bạn đã khoá (`locked`) không bị dựng lại ghi đè
(`check --base`, PG401).

```
sơ đồ «Attention Is All You Need» · 21 ô, 3 tầng, sâu 2 · neo: 25/25 có thật

kết quả: 0 lỗi, 0 cảnh báo
```

Câu trích bịa, chép sai trang, hay quá ngắn đều bị bắt, kèm gợi ý chỗ đúng:

```
✗ LỖI PG201  ô idea · neo 1
  câu trích không có ở tr.2 «based solely on attention mechanisms, dispensing with recurrence and convolutions entirely»
  → có ở tr.1 (đoạn p1-b12)
```

## Trong VietPaper

VietPaper dùng paper-graph như thư viện: `../pdf-translator/.venv/bin/pip install -e ../paper-graph` (`pyproject.toml`
không có dependency nào). Tab 🗺 Sơ đồ của VietPaper dựng, xem, sửa sơ đồ của bài đang đọc; bấm ô thì hai bản gốc và dịch
cuộn tới đúng đoạn, thẻ có bản dịch của câu trích (README của VietPaper, mục "Sơ đồ bài báo"). Phần paper-graph cung cấp:

- `extract.extract(pdf, app=<module VietPaper>, given={trang: (khối, có OCR)})`: dùng đúng các khối VietPaper đã trích
  (cả khối OCR bằng VLM), nên đoạn `p{n}-b{k}` là đoạn số k-1 của trang n-1 trong VietPaper; không huỷ phiên model bố cục.
- `view.page(data, edit, assets="/pg/")`: trang nhúng nạp `viewer.js`, `viewer.css` từ app chứa nó, không script nội tuyến,
  không thẻ CSP riêng (đặt trong `<iframe srcdoc>` thì thừa kế CSP của app). Dữ liệu có `embed: true` thì trình xem gửi
  `postMessage({pg: "anchor", page, block, go})` lên trang chứa khi chọn ô hay bấm "Xem trong bài"; `edit.api` đổi route
  gửi sửa đổi; neo có `vi` (`vi_whole`) thì thẻ hiện bản dịch.

Lõi (`check`) chỉ dùng thư viện chuẩn của Python 3.11. Định dạng hai file và toàn bộ mã lỗi ở
[docs/format.md](docs/format.md); bộ đo và đáp án tay ở [docs/bench.md](docs/bench.md).

```bash
../pdf-translator/.venv/bin/python bench/prepare.py                      # trích bảy bài của bộ đo
../pdf-translator/.venv/bin/python -m unittest discover -s tests -t .    # 112 test
```

## Trạng thái

Mốc 4 (gắn vào VietPaper). Xem [PLAN.md](PLAN.md) §0.

## Giấy phép

GNU AGPL-3.0, xem [LICENSE](LICENSE). Báo lỗi bảo mật: [SECURITY.md](SECURITY.md).
