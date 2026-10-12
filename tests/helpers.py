"""Dữ liệu giả cho test: một bài 3 trang, vài đoạn, một hình, và một sơ đồ hợp lệ trên đó."""
import copy

SHA = "a" * 64

BLOCKS = {
    "version": 1,
    "source": {"file": "toy.pdf", "sha256": SHA, "pages": 3, "extractor": "test"},
    "pages": [{"page": 1, "width": 612, "height": 792, "text": True},
              {"page": 2, "width": 612, "height": 792, "text": True},
              {"page": 3, "width": 612, "height": 792, "text": False}],
    "blocks": [
        {"id": "p1-b1", "page": 1, "bbox": [72, 72, 540, 100], "label": "doc_title", "text": "A Toy Paper on Widgets"},
        {"id": "p1-b2", "page": 1, "bbox": [72, 120, 540, 300], "label": "abstract",
         "text": "Recurrent widgets process tokens one at a time, which precludes paral-\nlelization within a sequence. "
                 "We propose the flat widget, which processes all tokens at once."},
        {"id": "p1-b3", "page": 1, "bbox": [72, 310, 540, 360], "label": "figure_title",
         "text": "Figure 0: The flat widget processes all tokens at once."},
        {"id": "p2-b1", "page": 2, "bbox": [72, 72, 300, 400], "label": "text",
         "text": "The flat widget uses a single ﬁxed projection for every token, and the end of this"},
        {"id": "p2-b2", "page": 2, "bbox": [310, 72, 540, 400], "label": "text",
         "text": "sentence continues in the next column with a measured speedup of four times."},
        {"id": "p2-b3", "page": 2, "bbox": [72, 420, 540, 440], "label": "figure_title",
         "text": "Figure 1: Throughput of the flat widget compared with recurrent widgets."},
        {"id": "p2-b4", "page": 2, "bbox": [72, 710, 540, 740], "label": "text",
         "text": "The flat widget reaches 28.4 BLEU (p < 0.05) with a loss change of −3.2 points over 100,000 steps."},
        {"id": "p2-b5", "page": 2, "bbox": [72, 742, 540, 760], "label": "text",
         "text": "It is impossible to train with a rate of 1e-5 or with 2-3 layers at 80.5% recall."},
    ],
    "figures": [{"id": "p2-f1", "page": 2, "bbox": [72, 450, 540, 700], "kind": "chart", "caption": "p2-b3"}],
}

GRAPH = {
    "version": 1,
    "paper": {"title": "A Toy Paper on Widgets", "sha256": SHA, "blocks": "toy.blocks.json"},
    "nodes": [
        {"id": "problem", "parent": None, "kind": "problem", "label": "Xử lý tuần tự",
         "anchors": [{"page": 1, "quote": "which precludes parallelization within a sequence"}]},
        {"id": "idea", "parent": None, "kind": "idea", "label": "Xử lý cùng lúc",
         "anchors": [{"page": 1, "quote": "processes all tokens at once", "block": "p1-b2"}]},
        {"id": "result", "parent": None, "kind": "result", "label": "Nhanh hơn bốn lần",
         "anchors": [{"page": 2, "quote": "with a measured speedup of four times"}], "figure": "p2-f1"},
        {"id": "r.claim", "parent": "result", "kind": "claim", "label": "Nhanh hơn",
         "anchors": [{"page": 2, "quote": "a measured speedup of four times"}]},
        {"id": "r.fig", "parent": "result", "kind": "evidence", "label": "Hình 1",
         "anchors": [{"page": 2, "quote": "Throughput of the flat widget compared"}], "figure": "p2-f1"},
    ],
    "edges": [
        {"from": "problem", "to": "idea", "kind": "flow", "label": "giải bằng"},
        {"from": "idea", "to": "result", "kind": "flow"},
        {"from": "r.fig", "to": "r.claim", "kind": "supports", "strength": "strong"},
    ],
    "groups": [],
}


def blocks():
    return copy.deepcopy(BLOCKS)


def graph():
    return copy.deepcopy(GRAPH)


def node(g, nid):
    return next(n for n in g["nodes"] if n["id"] == nid)
