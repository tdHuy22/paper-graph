# paper-graph

Đọc bài báo bằng mắt trước, bằng chữ sau.

Mỗi bài báo thành một sơ đồ nhiều tầng: tầng đầu chỉ 5–9 ô (vấn đề, ý then
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
```

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

Lõi (`check`) chỉ dùng thư viện chuẩn của Python 3.11. Định dạng hai file và toàn bộ mã lỗi ở
[docs/format.md](docs/format.md); bộ đo và đáp án tay ở [docs/bench.md](docs/bench.md).

```bash
../pdf-translator/.venv/bin/python bench/prepare.py                      # trích ba bài của bộ đo
../pdf-translator/.venv/bin/python -m unittest discover -s tests -t .    # 81 test
```

## Trạng thái

Mốc 1 (lõi kiểm được). Xem [PLAN.md](PLAN.md) §0.
