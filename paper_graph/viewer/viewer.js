// Trình xem sơ đồ paper-graph. Dữ liệu nhúng trong #data (JSON, đã thoát < > & U+2028 U+2029); bố cục tính sẵn bằng
// Python (paper_graph/layout.py). Chữ của sơ đồ là dữ liệu không tin cậy (TM-5, TM-13): chỉ đưa vào trang bằng
// textContent, tên lớp CSS chỉ lấy từ danh sách cho phép; không ghi HTML thô, không chạy chuỗi thành mã.
(function () {
  "use strict";
  var SVG = "http://www.w3.org/2000/svg";
  var D = JSON.parse(document.getElementById("data").textContent);
  var KINDS = {
    problem: "Vấn đề", idea: "Ý then chốt", method: "Cách làm", why: "Vì sao chạy được", result: "Kết quả",
    limit: "Giới hạn", context: "Bối cảnh", step: "Bước", io: "Đầu vào, đầu ra", concept: "Khái niệm",
    claim: "Tuyên bố", evidence: "Bằng chứng"
  };
  var EDGES = { flow: "dẫn tới", supports: "chống đỡ", contradicts: "bác", uses: "dùng", relates: "liên quan" };
  var EDGES_IN = { flow: "đến từ", supports: "được chống đỡ bởi", contradicts: "bị bác bởi", uses: "được dùng bởi",
    relates: "liên quan" };
  var MIN_SCALE = 0.65;  // thu tầng rộng cho vừa khung, nhưng không nhỏ tới mức khó đọc chữ: hơn nữa thì cuộn
  var STRENGTH = { strong: "mạnh", moderate: "vừa", weak: "yếu" };
  var STATUS = { draft: "bản nháp", accepted: "đã duyệt", locked: "đã khoá" };
  var WHY = { own: "hình của ô này", caption: "câu trích nằm ở chú thích của hình", mention: "ô nhắc tới hình này",
    evidence: "từ bằng chứng", child: "ở tầng dưới" };
  var FIG_KINDS = { table: "bảng", chart: "biểu đồ", image: "hình", formula: "công thức" };
  var tier = "";
  var selected = null;
  var shown = new Map();  // id → <g> của các ô đang vẽ (Map: id như "__proto__" vẫn là khoá thường)

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = String(text);
    return e;
  }
  function sv(tag, attrs) {
    var e = document.createElementNS(SVG, tag);
    for (var k in attrs) if (Object.prototype.hasOwnProperty.call(attrs, k)) e.setAttribute(k, String(attrs[k]));
    return e;
  }
  function num(v) { return typeof v === "number" && isFinite(v) ? v : 0; }
  function kindOf(n) { return Object.prototype.hasOwnProperty.call(KINDS, n.kind) ? n.kind : "context"; }
  function edgeKind(k) { return Object.prototype.hasOwnProperty.call(EDGES, k) ? k : "relates"; }
  function strengthOf(s) { return Object.prototype.hasOwnProperty.call(STRENGTH, s) ? s : ""; }
  function node(id) { return Object.prototype.hasOwnProperty.call(D.nodes, id) ? D.nodes[id] : null; }
  function fig(id) { return D.figures && Object.prototype.hasOwnProperty.call(D.figures, id) ? D.figures[id] : null; }
  function figName(id) {
    var f = fig(id);
    if (!f) return id;
    var kind = Object.prototype.hasOwnProperty.call(FIG_KINDS, f.kind) ? FIG_KINDS[f.kind] : "hình";
    return (f.label || kind.charAt(0).toUpperCase() + kind.slice(1)) + ", trang " + num(f.page);
  }
  function image(key) {
    var v = D.images && Object.prototype.hasOwnProperty.call(D.images, key) ? D.images[key] : null;
    return typeof v === "string" && v.indexOf("data:image/png;base64,") === 0 ? v : null;  // TM-15
  }

  function markers(svg) {
    var defs = sv("defs", {});
    ["base", "supports", "contradicts"].forEach(function (k) {
      var m = sv("marker", { id: "arrow-" + k, viewBox: "0 0 10 10", refX: 9, refY: 5, markerWidth: 7,
        markerHeight: 7, orient: "auto-start-reverse" });
      m.setAttribute("class", k);
      m.appendChild(sv("path", { d: "M0,0 L10,5 L0,10 z" }));
      defs.appendChild(m);
    });
    svg.appendChild(defs);
  }

  function edgePath(e) {
    var a = e.points[0], b = e.points[1];
    var x0 = num(a[0]), y0 = num(a[1]), x1 = num(b[0]), y1 = num(b[1]);
    if (e.shape === "side") {
      var dx = (x1 - x0) / 2;
      return "M" + x0 + "," + y0 + " C" + (x0 + dx) + "," + y0 + " " + (x1 - dx) + "," + y1 + " " + x1 + "," + y1;
    }
    var dy = Math.max(24, Math.abs(y1 - y0) / 2) * (e.shape === "up" ? -1 : 1);
    return "M" + x0 + "," + y0 + " C" + x0 + "," + (y0 + dy) + " " + x1 + "," + (y1 - dy) + " " + x1 + "," + y1;
  }

  function focused() {
    var a = document.activeElement, hit = null;
    shown.forEach(function (g, id) { if (g === a) hit = id; });
    return hit;
  }
  function focusNode(id) { if (id !== null && shown.has(id)) shown.get(id).focus(); }
  function order(L) { return Array.isArray(L.order) ? L.order : Object.keys(L.nodes); }

  // vẽ lại cả tầng: chỉ khi đổi tầng hay đổi cỡ khung; chọn ô chỉ đổi lớp `sel` để focus bàn phím không mất
  function draw() {
    var L = D.tiers[tier];
    var svg = document.getElementById("svg");
    var keep = focused();
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    shown = new Map();
    var w = num(L.width), h = num(L.height);
    var room = document.getElementById("canvas").clientWidth || w;
    var scale = w > room ? Math.max(MIN_SCALE, room / w) : 1;
    svg.setAttribute("viewBox", "0 0 " + w + " " + h);
    svg.setAttribute("width", String(Math.round(w * scale)));
    svg.setAttribute("height", String(Math.round(h * scale)));
    markers(svg);
    L.groups.forEach(function (g) {
      var gg = sv("g", {});
      gg.setAttribute("class", "grp");
      gg.appendChild(sv("rect", { x: num(g.x), y: num(g.y), width: num(g.w), height: num(g.h), rx: 12 }));
      (Array.isArray(g.lines) ? g.lines : [g.label || ""]).forEach(function (line, i) {
        var t = sv("text", { x: num(g.x) + 12, y: num(g.y) + 15 + i * 15 });
        t.textContent = String(line);
        gg.appendChild(t);
      });
      svg.appendChild(gg);
    });
    L.edges.forEach(function (e) {
      var k = edgeKind(e.kind), s = strengthOf(e.strength);
      var ge = sv("g", {});
      ge.setAttribute("class", "edge " + k + (s ? " " + s : ""));
      var p = sv("path", { d: edgePath(e) });
      p.setAttribute("marker-end", "url(#arrow-" + (k === "supports" || k === "contradicts" ? k : "base") + ")");
      var title = sv("title", {});
      var na = node(e.from), nb = node(e.to);
      title.textContent = (na ? na.label : e.from) + " — " + EDGES[k] + (s ? " (" + STRENGTH[s] + ")" : "") + " → " +
        (nb ? nb.label : e.to);
      ge.appendChild(title);
      ge.appendChild(p);
      if (e.label) {
        var mx = (num(e.points[0][0]) + num(e.points[1][0])) / 2, my = (num(e.points[0][1]) + num(e.points[1][1])) / 2;
        var lt = sv("text", { x: mx + 6, y: my + 4 });
        lt.setAttribute("class", "halo");
        lt.textContent = String(e.label);
        ge.appendChild(lt);
        var lt2 = sv("text", { x: mx + 6, y: my + 4 });
        lt2.textContent = String(e.label);
        ge.appendChild(lt2);
      }
      svg.appendChild(ge);
    });
    order(L).forEach(function (id) {
      var b = Object.prototype.hasOwnProperty.call(L.nodes, id) ? L.nodes[id] : null, n = node(id);
      if (!b || !n || shown.has(id)) return;
      var g = sv("g", { tabindex: 0, role: "button" });
      g.setAttribute("class", "node k-" + kindOf(n) + (n.basis === "inference" ? " inference" : ""));
      g.setAttribute("aria-label", KINDS[kindOf(n)] + ": " + n.label + (n.children ? ". Có tầng dưới " + n.children + " ô" : ""));
      g.appendChild(sv("rect", { x: num(b.x) - 4, y: num(b.y) - 4, width: num(b.w) + 8, height: num(b.h) + 8, rx: 12,
        "class": "ring" }));
      g.appendChild(sv("rect", { x: num(b.x), y: num(b.y), width: num(b.w), height: num(b.h), rx: 9, "class": "box" }));
      (b.lines || []).forEach(function (line, i) {
        var t = sv("text", { x: num(b.x) + 12, y: num(b.y) + 10 + 13 + i * 18 });
        t.textContent = String(line);
        g.appendChild(t);
      });
      if (n.children) {
        var badge = sv("text", { x: num(b.x) + num(b.w) - 10, y: num(b.y) + num(b.h) - 7, "text-anchor": "end" });
        badge.setAttribute("class", "badge");
        badge.textContent = "▸ " + n.children;
        g.appendChild(badge);
      }
      g.addEventListener("click", function () { select(id); });
      g.addEventListener("dblclick", function () { if (n.children) open(id); });
      g.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); if (selected === id && n.children) open(id); else select(id); }
      });
      svg.appendChild(g);
      shown.set(id, g);
    });
    mark();
    crumbs();
    focusNode(keep);
  }

  function mark() {
    shown.forEach(function (g, id) {
      g.classList.toggle("sel", id === selected);
      if (id === selected) g.setAttribute("aria-current", "true"); else g.removeAttribute("aria-current");
    });
  }

  function crumbs() {
    var nav = document.getElementById("crumbs");
    while (nav.firstChild) nav.removeChild(nav.firstChild);
    var path = [];
    for (var cur = tier; cur; cur = (node(cur) || {}).parent || "") path.unshift(cur);
    path.unshift("");
    path.forEach(function (key, i) {
      if (i) nav.appendChild(el("span", "sep", "›"));
      var name = key ? (node(key) || {}).label || key : "Tầng đầu";
      if (key === tier) nav.appendChild(el("span", "here", name));
      else {
        var b = el("button", "", name);
        b.type = "button";
        var from = path[i + 1];  // lên tầng trên thì chọn sẵn ô vừa đi qua, như phím Escape
        b.addEventListener("click", function () { go(key, from, true); });
        nav.appendChild(b);
      }
    });
  }

  // `focus`: đưa focus bàn phím vào ô được chọn (hay ô đầu tầng) sau khi điều hướng từ nút, đường dẫn, phím Escape
  function go(key, sel, focus) {
    if (!Object.prototype.hasOwnProperty.call(D.tiers, key)) return;
    tier = key;
    selected = sel;
    draw();
    if (sel) card(sel); else intro();
    if (focus) focusNode(sel !== null ? sel : order(D.tiers[key])[0]);
  }
  function open(id) { go(id, null, true); }
  function select(id, focus) {
    var n = node(id);
    if (!n) return;
    if ((n.parent || "") !== tier) { go(n.parent || "", id, focus); return; }
    selected = id;
    mark();
    card(id);
    if (focus) focusNode(id);
  }

  // một hình: ảnh bấm để phóng to, tên và trang, vì sao gắn vào ô (kèm nút tới ô trung gian), chú thích của bài
  function figureBox(id, why, via) {
    var f = fig(id), box = el("figure", "fig"), src = image(id);
    if (src) {
      var b = el("button", "thumb");
      b.type = "button";
      b.setAttribute("aria-label", "Phóng to " + figName(id));
      var im = el("img", "shot");
      im.src = src;
      im.alt = "Ảnh cắt từ bài: " + figName(id);
      b.appendChild(im);
      b.addEventListener("click", function () { zoom(id, b); });
      box.appendChild(b);
    }
    var cap = el("figcaption", "");
    cap.appendChild(el("span", "fig-name", figName(id)));
    if (why) {
      cap.appendChild(el("span", "muted", " · " + why));
      if (via) {
        var go2 = el("button", "inline", (node(via) || {}).label || via);
        go2.type = "button";
        go2.addEventListener("click", function () { select(via, true); });
        cap.appendChild(el("span", "muted", " «"));
        cap.appendChild(go2);
        cap.appendChild(el("span", "muted", "»"));
      }
    }
    if (f.caption) cap.appendChild(el("span", "fig-cap", f.caption));
    box.appendChild(cap);
    return box;
  }

  function zoom(id, from) {
    var d = document.getElementById("zoom"), src = image(id), f = fig(id);
    if (!src || !d.showModal) return;
    var im = document.getElementById("zoom-img");
    im.src = src;
    im.alt = "Ảnh cắt từ bài: " + figName(id);
    document.getElementById("zoom-cap").textContent = figName(id) + (f.caption ? ". " + f.caption : "");
    d.showModal();
    d.addEventListener("close", function back() { d.removeEventListener("close", back); if (from) from.focus(); });
  }

  // danh sách mọi hình, bảng của bài, mỗi hình kèm các ô dùng nó
  function gallery() {
    selected = null;
    mark();
    var c = document.getElementById("card");
    while (c.firstChild) c.removeChild(c.firstChild);
    var ids = Object.keys(D.figures || {});
    c.appendChild(el("h2", "", "Hình và bảng của bài (" + ids.length + ")"));
    ids.forEach(function (id) {
      var box = figureBox(id, "", null), users = (fig(id).nodes || []).filter(function (x) { return node(x); });
      if (!users.length) box.appendChild(el("p", "users muted", "Chưa ô nào dùng hình này."));
      else {
        box.appendChild(el("p", "users muted", "Ô dùng hình này:"));
        var ul = el("ul", "links");
        users.forEach(function (u) {
          var li = el("li", ""), b = el("button", "", node(u).label);
          b.type = "button";
          b.addEventListener("click", function () { select(u, true); });
          li.appendChild(b);
          ul.appendChild(li);
        });
        box.appendChild(ul);
      }
      c.appendChild(box);
    });
    c.focus();
  }

  function intro() {
    var c = document.getElementById("card");
    while (c.firstChild) c.removeChild(c.firstChild);
    c.appendChild(el("p", "muted", tier ? "Tầng dưới của «" + ((node(tier) || {}).label || tier) + "»." :
      "Tầng đầu: bức tranh lớn của bài."));
    c.appendChild(el("p", "muted", "Bấm một ô để xem giải thích, câu trích nguyên văn và hình liên quan. Ô có dấu ▸ mở ra được tầng dưới."));
  }

  function card(id) {
    var n = node(id), c = document.getElementById("card");
    while (c.firstChild) c.removeChild(c.firstChild);
    var k = kindOf(n);
    var kind = el("span", "kind", KINDS[k]);
    c.appendChild(kind);
    c.appendChild(el("h2", "", n.label));
    if (n.term) c.appendChild(el("p", "term", n.term));
    var tags = el("div", "tags");
    if (n.basis === "inference") tags.appendChild(el("span", "tag warn", "suy luận của người dựng, không phải lời bài"));
    if (Object.prototype.hasOwnProperty.call(STATUS, n.status)) tags.appendChild(el("span", "tag", STATUS[n.status]));
    if (tags.firstChild) c.appendChild(tags);
    if (n.explain) c.appendChild(el("p", "explain", n.explain));
    if (n.children) {
      var b = el("button", "open", "Mở tầng dưới (" + n.children + " ô)");
      b.type = "button";
      b.addEventListener("click", function () { open(id); });
      c.appendChild(b);
    }
    var rf = (n.figures || []).filter(function (r) { return fig(r.id); });
    if (rf.length) {
      c.appendChild(el("h3", "", "Hình, bảng liên quan"));
      rf.forEach(function (r) {
        var why = Object.prototype.hasOwnProperty.call(WHY, r.why) ? WHY[r.why] : "";
        var via = r.via ? node(r.via) : null;
        c.appendChild(figureBox(r.id, why, via ? r.via : null));
      });
    }
    var anchors = n.anchors || [];
    if (anchors.length) {
      c.appendChild(el("h3", "", "Câu trích nguyên văn"));
      anchors.forEach(function (a) {
        var q = el("blockquote", "", a.quote);
        q.appendChild(el("span", "where", "trang " + num(a.page) + (a.block ? " · đoạn " + a.block : "")));
        var shot = a.block ? image(a.block) : null;
        if (shot) {
          var d = el("details", ""), s = el("summary", "", "Xem đoạn gốc trong bài");
          d.appendChild(s);
          var im2 = el("img", "shot");
          im2.alt = "Ảnh đoạn " + a.block + ", trang " + num(a.page);
          d.addEventListener("toggle", function () { if (d.open && !im2.src) im2.src = shot; });
          d.appendChild(im2);
          q.appendChild(d);
        }
        c.appendChild(q);
      });
    }
    var rel = D.edges.filter(function (e) { return e.from === id || e.to === id; });
    if (rel.length) {
      c.appendChild(el("h3", "", "Nối với"));
      var ul = el("ul", "links");
      rel.forEach(function (e) {
        var other = e.from === id ? e.to : e.from, o = node(other);
        if (!o) return;
        var k2 = edgeKind(e.kind), s = strengthOf(e.strength);
        var li = el("li", "");
        var verb = e.from === id ? EDGES[k2] : EDGES_IN[k2];
        li.appendChild(el("span", "muted", verb + (s ? " (" + STRENGTH[s] + ")" : "") + ": "));
        var btn = el("button", "", o.label);
        btn.type = "button";
        btn.addEventListener("click", function () { select(other, true); });
        li.appendChild(btn);
        ul.appendChild(li);
      });
      c.appendChild(ul);
    }
  }

  document.getElementById("title").textContent = String(D.title || "");
  document.getElementById("foot").textContent = D.note || "";
  var nfig = Object.keys(D.figures || {}).length, figsBtn = document.getElementById("figs");
  if (nfig) {
    figsBtn.textContent = "Hình và bảng (" + nfig + ")";
    figsBtn.hidden = false;
    figsBtn.addEventListener("click", gallery);
  }
  var zoomBox = document.getElementById("zoom");
  document.getElementById("zoom-close").addEventListener("click", function () { zoomBox.close(); });
  zoomBox.addEventListener("click", function (ev) { if (ev.target === zoomBox) zoomBox.close(); });  // bấm nền tối
  var resizing = null;
  window.addEventListener("resize", function () {
    clearTimeout(resizing);
    resizing = setTimeout(draw, 120);
  });
  document.addEventListener("keydown", function (ev) {
    if (zoomBox.open) return;  // Escape lúc xem hình to chỉ đóng hình (trình duyệt tự đóng dialog)
    if (ev.key === "Escape" && tier) { var up = (node(tier) || {}).parent || ""; go(up, tier, true); }
  });
  go("", null, false);
})();
