"""Bố cục từng tầng của sơ đồ: Python tính sẵn toạ độ, trình xem chỉ vẽ (Mốc 3).

Mỗi tầng tối đa 9 ô, nên dàn theo lớp (Sugiyama rút gọn) là đủ, không cần thư viện bố cục: tính được bằng thư viện
chuẩn, kiểm được bằng unittest (không chồng ô, nhóm bao đúng ô), và toạ độ lưu lại được khi người dùng kéo thả (Mốc 3,
việc 4.3).

Các bước, cho một tầng (ô cùng `parent`, cạnh và nhóm của tầng đó):
1. lớp: mọi cạnh tính là có hướng `from → to` (cạnh vòng bị bỏ qua khi xếp lớp), lớp của ô = đường dài nhất từ ô
   không có cạnh vào; dàn từ trên xuống (vấn đề → ý → cách làm → kết quả; bằng chứng ở trên tuyên bố nó chống đỡ);
2. thứ tự trong lớp: theo trọng tâm của hàng xóm ở lớp trên rồi lớp dưới, vài lượt; ô cùng nhóm đứng liền nhau;
3. toạ độ: mỗi lớp một hàng, hàng căn giữa; kích thước ô theo số dòng nhãn sau khi ngắt;
4. cạnh: điểm đầu, điểm cuối ở mép ô (xuống: đáy → đỉnh; cùng lớp: cạnh bên; ngược lên: đỉnh → đáy);
5. nhóm: khung bao các ô thành viên, nhãn nhóm ngắt dòng theo bề ngang khung;
6. thứ tự đọc (`order`): theo hàng trên hình, trái sang phải; ô cùng nhóm liền nhau. Trình xem vẽ và cho Tab theo
   thứ tự này.
"""
from dataclasses import dataclass

from . import model as m

NODE_W = 210
CHAR_W = 7.2  # bề ngang trung bình một ký tự ở cỡ chữ 13px; ngắt dòng theo ước lượng này
LINE_H = 18
PAD_X = 12
PAD_Y = 10
MAX_LINES = 3
GAP_X = 40
GAP_Y = 64
MARGIN = 28
GROUP_PAD = 12
GROUP_LABEL_H = 20
GROUP_LINE_H = 15  # nhãn nhóm 12px, dòng thứ hai trở đi
SWEEPS = 4


@dataclass
class Box:
    x: float
    y: float
    w: float
    h: float
    lines: list[str]

    @property
    def cx(self) -> float:
        return self.x + self.w / 2


def wrap(text: str, width: int, max_lines: int = MAX_LINES) -> list[str]:
    """Ngắt theo từ, tối đa `max_lines` dòng; dòng cuối thừa thì cắt và thêm "…". Từ dài hơn một dòng thì bẻ."""
    words = text.split()
    lines: list[str] = []
    cur = ""
    for w in words:
        while len(w) > width:  # từ quá dài (id, URL): bẻ
            if cur:
                lines.append(cur)
                cur = ""
            lines.append(w[:width])
            w = w[width:]
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= width:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if not lines:
        lines = [""]
    if len(lines) > max_lines:
        last = lines[max_lines - 1]
        lines = lines[:max_lines - 1] + [(last[:width - 1].rstrip() + "…")]
    return lines


def node_size(label: str) -> tuple[float, float, list[str]]:
    per_line = max(8, int((NODE_W - 2 * PAD_X) / CHAR_W))
    lines = wrap(label, per_line)
    return NODE_W, 2 * PAD_Y + LINE_H * len(lines), lines


def _layers(ids: list[str], edges: list[tuple[str, str]]) -> dict[str, int]:
    """Lớp theo đường dài nhất, sau khi bỏ cạnh vòng tìm bằng DFS theo thứ tự ô trong file (ổn định)."""
    out: dict[str, list[str]] = {i: [] for i in ids}
    for a, b in edges:
        if a != b:
            out[a].append(b)
    state: dict[str, int] = {}  # 1 đang thăm, 2 xong
    keep: list[tuple[str, str]] = []
    for root in ids:
        if root in state:
            continue
        stack = [(root, iter(out[root]))]
        state[root] = 1
        while stack:
            v, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                state[v] = 2
                stack.pop()
                continue
            if state.get(nxt) == 1:
                continue  # cạnh vòng: bỏ khi xếp lớp
            keep.append((v, nxt))
            if nxt not in state:
                state[nxt] = 1
                stack.append((nxt, iter(out[nxt])))
    layer = {i: 0 for i in ids}
    changed = True
    rounds = 0
    while changed and rounds <= len(ids):  # DAG: tối đa len(ids) vòng
        changed = False
        rounds += 1
        for a, b in keep:
            if layer[b] < layer[a] + 1:
                layer[b] = layer[a] + 1
                changed = True
    return layer


def _place(items: list[str], sizes: dict[str, tuple[float, float]], links: list[tuple[str, str]],
           order_hint: dict[str, int], margin: float) -> tuple[dict[str, tuple[float, float]], float, float]:
    """Dàn các khối (ô hay nhóm đã thu gọn) theo lớp. Trả toạ độ góc trên trái của từng khối, bề ngang, bề cao."""
    layer = _layers(items, links)
    rows: dict[int, list[str]] = {}
    for i in items:
        rows.setdefault(layer[i], []).append(i)
    depth = max(rows) + 1 if rows else 0
    for k in range(depth):
        rows.setdefault(k, [])
    up: dict[str, list[str]] = {i: [] for i in items}
    down: dict[str, list[str]] = {i: [] for i in items}
    for a, b in links:
        if layer[a] < layer[b]:
            up[b].append(a)
            down[a].append(b)
        elif layer[b] < layer[a]:
            up[a].append(b)
            down[b].append(a)
    pos = {i: float(n) for k in rows for n, i in enumerate(rows[k])}

    def order(row: list[str], nb: dict[str, list[str]]) -> list[str]:
        def bary(i: str) -> float:
            ps = [pos[j] for j in nb[i] if j in pos]
            return sum(ps) / len(ps) if ps else pos[i]
        keyed = {i: bary(i) for i in row}
        return sorted(row, key=lambda i: (keyed[i], order_hint[i]))

    for _ in range(SWEEPS):
        for k in range(1, depth):
            rows[k] = order(rows[k], up)
            pos.update({i: float(n) for n, i in enumerate(rows[k])})
        for k in range(depth - 2, -1, -1):
            rows[k] = order(rows[k], down)
            pos.update({i: float(n) for n, i in enumerate(rows[k])})

    widths = {k: sum(sizes[i][0] for i in rows[k]) + GAP_X * max(0, len(rows[k]) - 1) for k in rows}
    full = max(widths.values(), default=0)
    at: dict[str, tuple[float, float]] = {}
    y = margin
    for k in range(depth):
        x = margin + (full - widths[k]) / 2
        row_h = max((sizes[i][1] for i in rows[k]), default=0)
        for i in rows[k]:
            w, h = sizes[i]
            at[i] = (x, y + (row_h - h) / 2)
            x += w + GAP_X
        y += row_h + GAP_Y
    height = y - (GAP_Y if depth else 0) + margin
    return at, full + 2 * margin, height


def layout_tier(nodes: list[m.Node], edges: list[m.Edge], groups: list[m.Group]) -> dict:
    """Bố cục một tầng. Mỗi nhóm được dàn riêng bên trong rồi thu thành một khối khi dàn cả tầng, nên khung nhóm chỉ
    bao đúng thành viên của nó."""
    ids = [n.id for n in nodes]
    if not ids:
        return {"nodes": {}, "order": [], "edges": [], "groups": [], "width": 2 * MARGIN, "height": 2 * MARGIN}
    index = {i: k for k, i in enumerate(ids)}
    by_id = {n.id: n for n in nodes}
    sizes = {i: node_size(by_id[i].label) for i in ids}
    group_of = {x: g.id for g in groups for x in g.members if x in index}
    pairs = [(e.src, e.dst) for e in edges if e.src in index and e.dst in index]

    # 1. dàn bên trong từng nhóm. Khoá khối có tiền tố và dấu cách ("n …", "g …"): id ô hay nhóm nào cũng không trùng
    # được khoá của khối khác
    inner: dict[str, dict[str, tuple[float, float]]] = {}
    head: dict[str, list[str]] = {}
    item_size: dict[str, tuple[float, float]] = {}
    hint: dict[str, int] = {}
    live_groups = [g for g in groups if any(x in index for x in g.members)]
    for g in live_groups:
        members = [x for x in ids if group_of.get(x) == g.id]
        links = [(a, b) for a, b in pairs if a in members and b in members]
        at, w, h = _place(members, {x: sizes[x][:2] for x in members}, links, index, 0)
        inner[g.id] = at
        w = max(w, NODE_W)
        head[g.id] = wrap(g.label, max(8, int(w / CHAR_W)))  # nhãn nhóm ngắt theo bề ngang các ô, không tràn khung
        item_size["g " + g.id] = (w + 2 * GROUP_PAD, h + 2 * GROUP_PAD + _head_h(head[g.id]))
        hint["g " + g.id] = min(index[x] for x in members)
    item_of = {i: ("g " + group_of[i] if i in group_of else "n " + i) for i in ids}
    for i in ids:
        if i not in group_of:
            item_size["n " + i] = sizes[i][:2]
            hint["n " + i] = index[i]
    items = list(dict.fromkeys(item_of[i] for i in ids))
    links = list(dict.fromkeys((item_of[a], item_of[b]) for a, b in pairs if item_of[a] != item_of[b]))

    # 2. dàn cả tầng theo khối, rồi đặt ô vào chỗ
    at, width, height = _place(items, item_size, links, hint, MARGIN)
    boxes: dict[str, Box] = {}
    out_groups = []
    for g in live_groups:
        gx, gy = at["g " + g.id]
        gw, gh = item_size["g " + g.id]
        for i, (x, y) in inner[g.id].items():
            w, h, lines = sizes[i]
            boxes[i] = Box(gx + GROUP_PAD + x, gy + GROUP_PAD + _head_h(head[g.id]) + y, w, h, lines)
        out_groups.append({"id": g.id, "label": g.label, "lines": head[g.id], "x": round(gx, 1), "y": round(gy, 1),
                           "w": round(gw, 1), "h": round(gh, 1)})
    for i in ids:
        if i not in group_of:
            w, h, lines = sizes[i]
            x, y = at["n " + i]
            boxes[i] = Box(x, y, w, h, lines)

    # thứ tự đọc (Tab, trình đọc màn hình): khối theo hàng trên hình rồi trái sang phải; trong nhóm cũng vậy
    def reading(xy: tuple[float, float], hgt: float) -> tuple[float, float]:
        return round(xy[1] + hgt / 2, 1), round(xy[0], 1)

    order: list[str] = []
    for item in sorted(items, key=lambda k: reading(at[k], item_size[k][1])):
        if item.startswith("g "):
            gid = item[2:]
            order += sorted(inner[gid], key=lambda i: reading(inner[gid][i], sizes[i][1]))
        else:
            order.append(item[2:])

    # 3. cạnh: hướng theo toạ độ thật
    out_edges = []
    for e in edges:
        if e.src not in boxes or e.dst not in boxes:
            continue
        a, b = boxes[e.src], boxes[e.dst]
        if b.y >= a.y + a.h:
            shape, p0, p1 = "down", (a.cx, a.y + a.h), (b.cx, b.y)
        elif b.y + b.h <= a.y:
            shape, p0, p1 = "up", (a.cx, a.y), (b.cx, b.y + b.h)
        elif a.x < b.x:
            shape, p0, p1 = "side", (a.x + a.w, a.y + a.h / 2), (b.x, b.y + b.h / 2)
        else:
            shape, p0, p1 = "side", (a.x, a.y + a.h / 2), (b.x + b.w, b.y + b.h / 2)
        out_edges.append({"from": e.src, "to": e.dst, "kind": e.kind, "label": e.label, "strength": e.strength,
                          "shape": shape, "points": [_r(p0), _r(p1)]})

    return {"nodes": {i: {"x": round(boxes[i].x, 1), "y": round(boxes[i].y, 1), "w": boxes[i].w, "h": boxes[i].h,
                          "lines": boxes[i].lines} for i in order},
            "order": order, "edges": out_edges, "groups": out_groups, "width": round(width, 1),
            "height": round(height, 1)}


def _head_h(lines: list[str]) -> float:
    """Phần đầu khung nhóm dành cho nhãn: dòng đầu cao GROUP_LABEL_H, mỗi dòng thêm GROUP_LINE_H."""
    return GROUP_LABEL_H + GROUP_LINE_H * (len(lines) - 1)


def _r(p: tuple[float, float]) -> list[float]:
    return [round(p[0], 1), round(p[1], 1)]


def layout_graph(graph: m.Graph) -> dict[str, dict]:
    """Bố cục mọi tầng: khoá "" cho tầng đầu, id ô cha cho tầng dưới của nó."""
    tiers: dict[str | None, list[m.Node]] = {}
    for n in graph.nodes.values():
        tiers.setdefault(n.parent, []).append(n)
    out = {}
    for parent, members in tiers.items():
        ids = {n.id for n in members}
        es = [e for e in graph.edges if e.src in ids and e.dst in ids]
        gs = [g for g in graph.groups if g.parent == parent]
        out["" if parent is None else parent] = layout_tier(members, es, gs)
    return out
