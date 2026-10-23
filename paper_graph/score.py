"""Chấm một sơ đồ theo đáp án tay của bộ đo (luật ở docs/bench.md).

Một ô **khớp** một ý khi loại ô nằm trong `kinds` của ý, và hoặc một neo của ô rơi vào cùng đoạn với một neo của ý,
hoặc nhãn/thuật ngữ/giải thích của ô chứa một trong `terms` của ý. Từ đó:
    độ phủ      ý bắt buộc có ít nhất một ô khớp
    đúng tầng   ý bắt buộc có ô khớp nằm đúng `tier` (top: tầng đầu; under:X: trong cây con của ô đại diện ý X)
    ô đại diện  của ý tầng đầu: ô khớp, ô tầng đầu cùng loại ý có ô khớp trong cây con, và mọi ô tầng đầu khác cùng loại
                với ô đó. Ý vẫn ở tầng đầu khi câu neo của đáp án rơi vào ô con (ô tầng đầu neo câu khác), và ý tách
                thành nhiều ô tầng đầu cùng loại (kết quả "tốc độ" và "độ chính xác") là một ý. Ô khớp nằm dưới ô tầng
                đầu khác loại (tuyên bố kết quả dưới ô phương pháp) vẫn là sai tầng. Quan hệ tính trên ô khớp và ô tầng đầu chứa chúng (không lấy mọi ô cùng loại), giữa hai ô khác
                nhau
    quan hệ     hai ô khớp hai đầu nối nhau trong cùng tầng, trực tiếp hay qua một ô ở giữa (vấn đề → ý → cách làm),
                hay, khi `ancestor_ok`, ô này nằm trong cây con của ô kia
    soi         điểm soi (`probes`) đạt: cạnh đúng loại và mức giữa hai phía, hay một ô nêu đủ số và từ của chỗ bài
                tự lệch; đo thứ độ phủ không đo (thấy chỗ bài tự lệch, chấm mức bằng chứng đúng)
"""
import re
from dataclasses import dataclass, field

from . import model as m
from . import numbers as nums
from .blocks import Blocks
from .check import MIN_QUOTE_CHARS, MIN_QUOTE_WORDS
from .gold import Gold, Probe, Side
from .text import squash, word_count


@dataclass
class ItemResult:
    id: str
    must: bool
    matched: list[str]
    tier_ok: bool
    how: str  # "đoạn", "thuật ngữ", hay "" khi không khớp


@dataclass
class Score:
    items: list[ItemResult]
    relations: list[tuple[str, str, bool]]
    extra: list[str] = field(default_factory=list)  # ô tầng đầu không khớp ý nào (có thể là ý hay ngoài đáp án)
    probes: list[tuple[str, bool, str]] = field(default_factory=list)  # (id, đạt, giải thích)

    def _must(self) -> list[ItemResult]:
        return [i for i in self.items if i.must]

    @property
    def coverage(self) -> float:
        must = self._must()
        return sum(bool(i.matched) for i in must) / len(must) if must else 1.0

    @property
    def tier(self) -> float:
        must = self._must()
        return sum(i.tier_ok for i in must) / len(must) if must else 1.0

    @property
    def relation_rate(self) -> float:
        return sum(ok for *_, ok in self.relations) / len(self.relations) if self.relations else 1.0

    @property
    def probe_rate(self) -> float | None:
        return sum(ok for _, ok, _ in self.probes) / len(self.probes) if self.probes else None

    def summary(self) -> dict:
        must = self._must()
        return {"coverage": round(self.coverage, 3), "covered": sum(bool(i.matched) for i in must), "must": len(must),
                "tier": round(self.tier, 3), "relations": round(self.relation_rate, 3),
                "optional_covered": sum(bool(i.matched) for i in self.items if not i.must),
                "optional": sum(not i.must for i in self.items),
                "probes_ok": sum(ok for _, ok, _ in self.probes), "probes": len(self.probes)}


def _blocks_of(anchors: list[m.Anchor], blocks: Blocks) -> set[str]:
    out: set[str] = set()
    for a in anchors:
        # neo quá ngắn khớp ở đâu cũng được (PG202): không cho nó "khớp đoạn" với đáp án
        if word_count(a.quote) < MIN_QUOTE_WORDS or len(squash(a.quote)) < MIN_QUOTE_CHARS:
            continue
        if a.page in blocks.pages:
            for h in blocks.find_all(squash(a.quote), a.page):
                out.update(h.blocks)
    return out


def _has_term(text: str, term: str) -> bool:
    t = term.lower().strip()
    return bool(t) and re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", text) is not None


def score(graph: m.Graph, gold: Gold, blocks: Blocks) -> Score:
    nodes = graph.nodes
    node_blocks = {n.id: _blocks_of(n.anchors, blocks) for n in nodes.values()}
    node_text = {n.id: f"{n.label}\n{n.term}\n{n.explain}".lower() for n in nodes.values()}

    def ancestors(nid: str) -> set[str]:
        seen, cur = set(), nodes[nid].parent
        while cur is not None and cur in nodes and cur not in seen:
            seen.add(cur)
            cur = nodes[cur].parent
        return seen

    matches: dict[str, dict[str, str]] = {}  # ý → {ô: cách khớp}
    for it in gold.items.values():
        gold_blocks = _blocks_of(it.anchors, blocks)
        found: dict[str, str] = {}
        for n in nodes.values():
            if n.kind not in it.kinds:
                continue
            if node_blocks[n.id] & gold_blocks:
                found[n.id] = "đoạn"
            elif any(_has_term(node_text[n.id], t) for t in it.terms):
                found[n.id] = "thuật ngữ"
        matches[it.id] = found

    def top_of(nid: str) -> str:
        seen, cur = {nid}, nid
        while nodes[cur].parent in nodes and nodes[cur].parent not in seen:
            cur = nodes[cur].parent
            seen.add(cur)
        return cur

    owners: dict[str, set[str]] = {}  # ý → ô đại diện, cho đúng tầng
    linked_owners: dict[str, set[str]] = {}  # ý → ô khớp và ô tầng đầu chứa chúng, cho quan hệ
    for it in gold.items.values():
        owners[it.id] = set(matches[it.id])
        linked_owners[it.id] = set(matches[it.id])
        if it.tier == "top":
            tops = {t for t in map(top_of, matches[it.id]) if nodes[t].parent is None and nodes[t].kind in it.kinds}
            kinds = {nodes[t].kind for t in tops}
            owners[it.id] |= tops | {n.id for n in nodes.values() if n.parent is None and n.kind in kinds}
            linked_owners[it.id] |= tops

    results = []
    for it in gold.items.values():
        found = matches[it.id]
        if it.tier == "top":
            tier_ok = any(nodes[x].parent is None for x in owners[it.id])
        elif it.tier.startswith("under:"):
            tier_ok = any(ancestors(x) & owners.get(it.tier[6:], set()) for x in found)
        else:
            tier_ok = bool(found)
        how = "đoạn" if "đoạn" in found.values() else ("thuật ngữ" if found else "")
        results.append(ItemResult(it.id, it.must, sorted(found), tier_ok, how))

    near: dict[str, set[str]] = {}  # hàng xóm không hướng
    for e in graph.edges:
        near.setdefault(e.src, set()).add(e.dst)
        near.setdefault(e.dst, set()).add(e.src)

    def linked(x: str, y: str) -> bool:
        nx = near.get(x, set())
        return y in nx or any(y in near.get(z, set()) for z in nx)

    rels = []
    for r in gold.relations:
        # Hai ý cùng loại (ý tưởng, phương pháp) có thể chung một ô đại diện: một ô không tính là nối với chính nó
        a, b = linked_owners[r.src], linked_owners[r.dst]
        ok = any(x != y and linked(x, y) for x in a for y in b)
        if not ok and r.ancestor_ok:
            ok = any(y in ancestors(x) or x in ancestors(y) for x in a for y in b)
        rels.append((r.src, r.dst, ok))

    matched_nodes = {x for found in matches.values() for x in found}
    extra = [n.id for n in nodes.values() if n.parent is None and n.id not in matched_nodes]
    probes = [_probe(p, graph, node_blocks, node_text, blocks) for p in gold.probes]
    return Score(results, rels, extra, probes)


def _on_side(side: Side, node_blocks: dict[str, set[str]], graph: m.Graph, blocks: Blocks) -> set[str]:
    want = _blocks_of(side.anchors, blocks)
    return {n.id for n in graph.nodes.values() if node_blocks[n.id] & want or (n.figure and n.figure in side.figures)}


def _probe(p: Probe, graph: m.Graph, node_blocks, node_text, blocks: Blocks) -> tuple[str, bool, str]:
    if p.type == "edge":
        src = _on_side(p.src, node_blocks, graph, blocks)
        dst = _on_side(p.dst, node_blocks, graph, blocks) if p.dst else None
        if not src:
            return p.id, False, "không ô nào khớp phía from"
        if dst is not None and not dst:
            return p.id, False, "không ô nào khớp phía to"
        edges = [e for e in graph.edges if e.src in src and (dst is None or e.dst in dst)]
        typed = [e for e in edges if p.kind is None or e.kind == p.kind]
        if not typed:
            have = ", ".join(sorted({e.kind for e in edges})) or "không có cạnh"
            return p.id, False, f"không có cạnh {p.kind or ''} giữa hai phía ({have})".replace("  ", " ")
        good = [e for e in typed if not p.strengths or e.strength in p.strengths]
        if not good:
            got = ", ".join(sorted({str(e.strength) for e in typed}))
            return p.id, False, f"mức {got}, mong {' hay '.join(p.strengths)}"
        e = good[0]
        return p.id, True, f"{e.src} → {e.dst} ({e.kind}{', ' + e.strength if e.strength else ''})"
    at = _on_side(p.at, node_blocks, graph, blocks)
    if not at:
        return p.id, False, "không ô nào neo vào chỗ đó"
    for nid in sorted(at):
        vals = nums.values_of(node_text[nid])
        if all(any(nums.values_of(x) & vals for x in g) for g in p.numbers) and \
                all(any(_has_term(node_text[nid], w) for w in g) for g in p.words):
            return p.id, True, f"ô {nid}"
    return p.id, False, f"{len(at)} ô neo vào đó nhưng không ô nào nêu đủ số, từ"


def render(sc: Score, title: str) -> str:
    s = sc.summary()
    lines = [f"chấm «{title}» theo đáp án: phủ {s['covered']}/{s['must']} ý bắt buộc ({s['coverage']:.0%}), "
             f"đúng tầng {s['tier']:.0%}, quan hệ {s['relations']:.0%}, ý tuỳ chọn {s['optional_covered']}/{s['optional']}"
             + (f", soi {s['probes_ok']}/{s['probes']}" if s["probes"] else ""),
             ""]
    for i in sc.items:
        mark = ("✓" if i.tier_ok else "≈") if i.matched else ("✗" if i.must else "·")
        tag = "bắt buộc" if i.must else "tuỳ chọn"
        detail = f"{', '.join(i.matched)} (khớp theo {i.how})" if i.matched else "không ô nào khớp"
        note = "" if i.tier_ok or not i.matched else "  ← sai tầng"
        lines.append(f"{mark} {i.id:<14} {tag:<9} {detail}{note}")
    if sc.relations:
        lines.append("")
        lines += [f"{'✓' if ok else '✗'} quan hệ {a} → {b}" for a, b, ok in sc.relations]
    if sc.probes:
        lines.append("")
        lines += [f"{'✓' if ok else '✗'} soi {pid}: {why}" for pid, ok, why in sc.probes]
    if sc.extra:
        lines += ["", "ô tầng đầu không khớp ý nào trong đáp án: " + ", ".join(sc.extra)]
    return "\n".join(lines)
