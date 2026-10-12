"""`*.graph.json`: sơ đồ nhiều tầng của một bài báo. Hằng số và kiểm dạng; kiểm neo và kiểm tầng nằm ở check.py.

Một ô có `parent` là null thì thuộc tầng đầu; có `parent` là id của ô X thì thuộc tầng dưới của X (mở ra khi
bấm X). Cạnh và nhóm chỉ nối các ô cùng tầng. Mô tả đầy đủ ở docs/format.md.
"""
import re
from dataclasses import dataclass, field

VERSION = 1
ID = re.compile(r"[A-Za-z0-9_.:-]{1,64}")  # id còn đi vào DOM và URL ở trình xem (TM-5)

NODE_KINDS = {
    # tầng đầu: bức tranh lớn của bài
    "problem", "idea", "method", "why", "result", "limit", "context",
    # tầng dưới
    "step", "io", "concept", "claim", "evidence",
}
EDGE_KINDS = {"flow", "supports", "contradicts", "uses", "relates"}
STRENGTHS = {"strong", "moderate", "weak"}
STATUSES = {"draft", "accepted", "locked"}
BASES = {"paper", "inference"}

NODE_FIELDS = {"id", "parent", "kind", "label", "term", "explain", "anchors", "basis", "figure", "status"}
EDGE_FIELDS = {"from", "to", "kind", "label", "strength", "anchors"}
GROUP_FIELDS = {"id", "parent", "label", "members"}
ANCHOR_FIELDS = {"page", "quote", "block"}

MAX_LABEL = 120
MAX_EDGE_LABEL = 40
MAX_TERM = 160
MAX_EXPLAIN = 1500
MAX_QUOTE = 600


@dataclass
class Anchor:
    page: int
    quote: str
    block: str | None


@dataclass
class Node:
    id: str
    parent: str | None
    kind: str
    label: str
    term: str = ""
    explain: str = ""
    anchors: list[Anchor] = field(default_factory=list)
    basis: str = "paper"
    figure: str | None = None
    status: str = "draft"


@dataclass
class Edge:
    src: str
    dst: str
    kind: str
    label: str = ""
    strength: str | None = None
    anchors: list[Anchor] = field(default_factory=list)


@dataclass
class Group:
    id: str
    parent: str | None
    label: str
    members: list[str]


@dataclass
class Graph:
    title: str
    sha256: str
    blocks_file: str | None
    nodes: dict[str, Node]
    edges: list[Edge]
    groups: list[Group]
