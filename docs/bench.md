# Bộ đo

Ba bài, ghim theo SHA-256 của PDF trong [bench/papers.json](../bench/papers.json). PDF nằm ở `../pdf-translator/data/`
và không vào git; chữ trích ra (`*.blocks.json`) cũng không.

```bash
../pdf-translator/.venv/bin/python bench/prepare.py          # trích lại blocks của cả ba bài (~1 phút)
../pdf-translator/.venv/bin/python -m unittest discover -s tests -t .
```

| Bài | Vì sao chọn | Ý bắt buộc | Ý tuỳ chọn |
| --- | --- | --- | --- |
| Attention Is All You Need | kiến trúc, có hình kiến trúc rõ | 10 | 7 |
| BERT | quy trình hai bước, nhiều tuyên bố có bảng | 10 | 6 |
| DataSentinel | bài bảo mật: mô hình đe dọa, trò chơi minimax, tấn công thích nghi | 13 | 4 |

## Hai thứ trong mỗi thư mục bài

- `<tên>.graph.json`: sơ đồ dựng tay (hiện chỉ bài Attention). Nó phải qua `check` sạch, và là nền cho các kiểu phá
  trong `tests/test_bench.py`: câu trích bịa, sai trang, quá ngắn, bỏ neo, cạnh treo, cạnh khác tầng, hình không có,
  tầng quá 9 ô, SHA của bài khác, đối chiếu với blocks của bài khác.
- `<tên>.gold.json`: đáp án tay, những ý một sơ đồ tốt phải có. Không phải một sơ đồ: nó không quy định nhãn, cách
  chia ô hay cạnh nào, chỉ quy định **ý nào** phải có mặt và ở khoảng tầng nào.

## Dạng đáp án

```json
{"version": 1,
 "paper": {"name": "attention", "title": "…", "sha256": "bdfa…"},
 "items": [
  {"id": "scaled_dot", "must": true, "tier": "under:method", "kinds": ["step", "concept"],
   "what": "Scaled dot-product attention: …",
   "terms": ["scaled dot-product", "dot-product attention"],
   "anchors": [{"page": 4, "quote": "We call our particular attention \"Scaled Dot-Product Attention\""}]}],
 "relations": [{"from": "problem", "to": "idea", "what": "…"},
               {"from": "table2", "to": "result", "what": "…", "ancestor_ok": true}]}
```

| Trường | Nghĩa |
| --- | --- |
| `must` | ý bắt buộc; độ phủ chỉ tính trên các ý này |
| `tier` | `top`: phải ở tầng đầu. `under:<id ý>`: phải nằm trong cây con của ô khớp với ý đó, ở tầng nào cũng được. `any`: tầng nào cũng được |
| `kinds` | loại ô chấp nhận được |
| `terms` | thuật ngữ gốc; ô có nhãn, `term` hay `explain` chứa một trong số này cũng tính là khớp |
| `anchors` | nơi bài nói ý này; được kiểm như neo của sơ đồ (test `GoldFiles`) |
| `relations` | quan hệ phải thấy được: có cạnh giữa hai ô khớp, hay (khi `ancestor_ok`) ô này nằm trong cây con của ô kia |

## Cách chấm (làm ở Mốc 2)

Một ô **khớp** một ý khi loại ô nằm trong `kinds`, và một trong hai điều sau đúng:

1. một neo của ô rơi vào cùng đoạn (`block`) với một neo của ý;
2. nhãn, `term` hay `explain` của ô chứa một trong `terms` của ý (không phân biệt hoa thường).

Rồi tính:

| Số đo | Ngưỡng của Mốc 2 |
| --- | --- |
| neo hợp lệ (`check`) | 100% |
| độ phủ: ý bắt buộc có ô khớp | ≥ 80% |
| đúng tầng: ý bắt buộc có ô khớp ở đúng `tier` | báo cáo, chưa đặt ngưỡng |
| quan hệ thấy được | báo cáo, chưa đặt ngưỡng |

Đáp án là của một người chọn. Hai người chọn "ý nào là then chốt" thường không trùng hết, nên đọc các con số này theo
hướng tăng giảm giữa các lần dựng, đừng đọc chính xác tới từng điểm.
