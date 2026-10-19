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
      var pinned = Array.isArray(L.pinned) && L.pinned.indexOf(id) >= 0;
      g.setAttribute("class", "node k-" + kindOf(n) + (n.basis === "inference" ? " inference" : "") +
        (n.status === "locked" ? " locked" : "") + (pinned ? " pinned" : ""));
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
      g.addEventListener("click", function () { if (justDragged) { justDragged = false; return; } select(id); });
      g.addEventListener("dblclick", function () { if (n.children) open(id); });
      g.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); if (selected === id && n.children) open(id); else select(id); }
        var step = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[ev.key];
        if (D.edit && ev.altKey && step) { ev.preventDefault(); nudge(id, g, b, step[0] * GRID, step[1] * GRID); }
      });
      if (D.edit) draggable(g, id, b);
      svg.appendChild(g);
      shown.set(id, g);
    });
    mark();
    crumbs();
    var rl = document.getElementById("relayout");
    rl.hidden = !(D.edit && Array.isArray(L.pinned) && L.pinned.length);
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
    if (D.edit) flushNudge();  // đổi tầng giữa lúc Alt + mũi tên: lưu ngay cho tầng cũ
    tier = key;
    selected = sel;
    draw();
    if (sel) card(sel); else intro();
    if (focus) focusNode(sel !== null ? sel : order(D.tiers[key])[0]);
  }
  function open(id) {
    var n = node(id);
    if (predicting && n && n.children && !guessOf(id)) { askGuess(id); return; }
    go(id, null, true);
  }
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

  // ---------------------------------------------------------------- chế độ sửa (chỉ khi trang do `serve` phục vụ)
  var GRID = 8;
  var justDragged = false;

  function say(text, bad) {
    var m = document.getElementById("msg");
    m.textContent = text;
    m.className = "msg" + (bad ? " bad" : "");
  }

  // gửi sửa đổi; server trả sơ đồ mới (bố cục, ô, hình) thì vẽ lại, giữ tầng và ô đang chọn
  function api(path, body, done) {
    body.version = D.edit.version;
    say("Đang lưu…", false);
    return fetch(path, {
      method: "POST", credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-PG-Token": String(D.edit.token) },
      body: JSON.stringify(body)
    }).then(function (r) {
      return r.json().then(function (j) { return { ok: r.ok, status: r.status, j: j }; });
    }).then(function (res) {
      if (!res.ok) {
        say(String(res.j.error || ("lỗi " + res.status)), true);
        draw();  // ô đang kéo về chỗ cũ
        if (done) done(res.j);
        return;
      }
      var keep = focused(), inCard = document.getElementById("card").contains(document.activeElement);
      D.tiers = res.j.tiers; D.nodes = res.j.nodes; D.figures = res.j.figures; D.edges = res.j.edges;
      D.edit.version = res.j.version;
      if (typeof res.j.note === "string" && res.j.note) document.getElementById("foot").textContent = res.j.note;
      if (!Object.prototype.hasOwnProperty.call(D.tiers, tier)) tier = "";
      if (selected !== null && !node(selected)) selected = null;
      draw();
      if (selected !== null) card(selected); else intro();
      focusNode(keep !== null ? keep : (inCard ? selected : null));  // thẻ dựng lại: focus về ô vừa sửa
      say("Đã lưu", false);
      if (done) done(null);
    }).catch(function () { say("Không gửi được: server đã dừng?", true); });
  }

  function editTools(c, id, n) {
    var box = el("div", "edit"), row = el("div", "row");
    if (n.status !== "locked") {
      var eb = el("button", "", "Sửa chữ");
      eb.type = "button";
      eb.addEventListener("click", function () { editForm(c, box, id, n); });
      row.appendChild(eb);
    }
    var lock = el("button", "", n.status === "locked" ? "Mở khoá" : "Khoá ô");
    lock.type = "button";
    lock.addEventListener("click", function () { api("/api/edit", { node: id, set: { status: n.status === "locked" ? "accepted" : "locked" } }); });
    row.appendChild(lock);
    box.appendChild(row);
    if (n.status === "locked") box.appendChild(el("p", "muted", "Ô đã khoá: lần dựng lại sau giữ nguyên ô này. Mở khoá để sửa chữ."));
    c.appendChild(box);
  }

  function field(form, label, name, value, max, area) {
    var wrap = el("label", "fld");
    wrap.htmlFor = "edit-" + name;
    wrap.appendChild(el("span", "", label));
    var inp = el(area ? "textarea" : "input", "");
    inp.id = "edit-" + name;
    inp.name = name;
    inp.value = value || "";
    inp.maxLength = max;
    if (area) inp.rows = 5;
    wrap.appendChild(inp);
    form.appendChild(wrap);
    return inp;
  }

  function editForm(c, box, id, n) {
    while (box.firstChild) box.removeChild(box.firstChild);
    var form = el("form", "editform");
    var lab = field(form, "Nhãn", "label", n.label, 120, false);
    var term = field(form, "Thuật ngữ", "term", n.term, 160, false);
    var exp = field(form, "Giải thích", "explain", n.explain, 1500, true);
    var errs = el("ul", "errs");
    form.appendChild(errs);
    var row = el("div", "row"), save = el("button", "", "Lưu"), cancel = el("button", "", "Huỷ");
    save.type = "submit";
    cancel.type = "button";
    row.appendChild(save);
    row.appendChild(cancel);
    form.appendChild(row);
    form.appendChild(el("p", "muted", "Lưu xong ô thành «đã duyệt». Sơ đồ phải qua kiểm tra: số liệu trong nhãn phải có trong câu trích."));
    cancel.addEventListener("click", function () { card(id); focusNode(id); });
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      while (errs.firstChild) errs.removeChild(errs.firstChild);
      if (!lab.value.trim()) { errs.appendChild(el("li", "", "Nhãn không được trống.")); lab.focus(); return; }
      save.disabled = true;
      api("/api/edit", { node: id, set: { label: lab.value, term: term.value, explain: exp.value } }, function (err) {
        save.disabled = false;
        if (err) (err.diags || []).forEach(function (d) { errs.appendChild(el("li", "", d)); });
      });
    });
    box.appendChild(form);
    lab.focus();
  }

  // toạ độ gửi lên là toạ độ ghim: toạ độ trên hình trừ độ dịch của tầng lúc bắt đầu kéo, bám lưới, không âm
  function shiftOf(key) {
    var sh = D.tiers[key] && Array.isArray(D.tiers[key].shift) ? D.tiers[key].shift : [0, 0];
    return [num(sh[0]), num(sh[1])];
  }
  function sendPin(key, sh, id, b, dx, dy) {
    function snap(v) { return Math.max(0, Math.round(v / GRID) * GRID); }
    var pos = {};
    pos[id] = [snap(num(b.x) + dx - sh[0]), snap(num(b.y) + dy - sh[1])];
    api("/api/move", { tier: key, pos: pos });
  }

  function draggable(g, id, b) {
    var start = null;
    g.addEventListener("pointerdown", function (ev) {
      if (ev.button !== 0) return;
      var svg = document.getElementById("svg");
      start = { x: ev.clientX, y: ev.clientY, k: num(D.tiers[tier].width) / (svg.clientWidth || 1), moved: false };
      g.setPointerCapture(ev.pointerId);
    });
    g.addEventListener("pointermove", function (ev) {
      if (!start) return;
      var dx = (ev.clientX - start.x) * start.k, dy = (ev.clientY - start.y) * start.k;
      if (!start.moved && Math.abs(dx) + Math.abs(dy) < 6) return;
      start.moved = true;
      start.dx = dx; start.dy = dy;
      g.setAttribute("transform", "translate(" + dx + "," + dy + ")");
      g.classList.add("dragging");
    });
    function end() {
      if (start && start.moved) {
        justDragged = true;  // click ngay sau pointerup (cùng một lượt) không tính là chọn ô
        setTimeout(function () { justDragged = false; }, 0);
        sendPin(tier, shiftOf(tier), id, b, start.dx, start.dy);
      }
      start = null;
    }
    g.addEventListener("pointerup", end);
    g.addEventListener("pointercancel", function () { start = null; g.removeAttribute("transform"); });
  }

  // Alt + mũi tên: gom các bước bấm liền nhau thành một lần lưu; tầng và độ dịch chốt từ bước đầu
  var nudging = null;
  function flushNudge() {
    if (!nudging) return;
    var cur = nudging;
    nudging = null;
    clearTimeout(cur.timer);
    sendPin(cur.tier, cur.shift, cur.id, cur.b, cur.dx, cur.dy);
  }
  function nudge(id, g, b, dx, dy) {
    if (nudging && nudging.id !== id) flushNudge();
    if (!nudging) nudging = { id: id, tier: tier, shift: shiftOf(tier), b: b, dx: 0, dy: 0 };
    nudging.dx += dx; nudging.dy += dy;
    g.setAttribute("transform", "translate(" + nudging.dx + "," + nudging.dy + ")");
    clearTimeout(nudging.timer);
    nudging.timer = setTimeout(flushNudge, 450);
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
      var box = figureBox(id, "", null), all = (fig(id).nodes || []).filter(function (x) { return node(x); });
      var users = all.filter(function (x) { return !unseen(x); }), hidden = all.length - users.length;
      if (hidden) box.appendChild(el("p", "users muted", hidden + " ô ở tầng bạn chưa đoán dùng hình này (ẩn tới khi đoán)."));
      if (!all.length) box.appendChild(el("p", "users muted", "Chưa ô nào dùng hình này."));
      else if (users.length) {
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

  // ---------------------------------------------------------------- tự đoán trước rồi mở (Mốc 5)
  // Người đọc viết ra điều mình nghĩ tầng dưới sẽ có, rồi mới mở và tự so: tự tạo ra trước khi xem giúp nhớ và hiểu
  // hơn chỉ xem sơ đồ dựng sẵn. Dự đoán chỉ lưu trong trình duyệt này (localStorage, theo SHA-256 của bài).
  var predicting = false;
  var STORE = "paper-graph:guess:" + String(D.sha256 || "");
  function load(k, fallback) {
    try { var v = window.localStorage.getItem(k); return v === null ? fallback : JSON.parse(v); } catch (e) { return fallback; }
  }
  var warned = false;
  function save(k, v) {
    try { window.localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; }
  }
  var mem = null;  // bản trong bộ nhớ: localStorage đầy, bị chặn hay ở chế độ riêng tư thì dự đoán vẫn còn tới khi đóng trang
  function guesses() {
    if (mem) return mem;
    var g = load(STORE, {});
    return g && typeof g === "object" && !Array.isArray(g) ? g : {};
  }
  function guessOf(id) {
    var g = guesses();
    var v = Object.prototype.hasOwnProperty.call(g, id) ? g[id] : null;
    return v && typeof v.text === "string" ? v : null;
  }
  function putGuess(id, v) {
    var g = Object.assign(Object.create(null), guesses());
    if (v === null) delete g[id]; else g[id] = v;
    mem = g;
    if (!save(STORE, g) && !warned) {
      warned = true;
      say("Trình duyệt không cho lưu: dự đoán chỉ giữ tới khi đóng trang.", true);
    }
  }
  // ô nằm dưới một ô cha (ở bậc nào cũng được) mà người đọc chưa đoán: đang tự đoán thì chưa được thấy nhãn của nó
  function unseen(id) {
    if (!predicting) return false;
    for (var p = (node(id) || {}).parent; p; p = (node(p) || {}).parent) if (!guessOf(p)) return true;
    return false;
  }
  function childrenOf(id) {
    var L = D.tiers[id];
    return L ? order(L).filter(function (x) { return node(x); }) : [];
  }

  function askGuess(id) {
    var n = node(id);
    if ((n.parent || "") !== tier) go(n.parent || "", id, false);
    selected = id;
    mark();
    var c = document.getElementById("card");
    while (c.firstChild) c.removeChild(c.firstChild);
    c.appendChild(el("span", "kind", "Tự đoán trước"));
    c.appendChild(el("h2", "", n.label));
    c.appendChild(el("p", "", "Tầng dưới của ô này có " + n.children + " ô. Trước khi mở, viết ra bạn nghĩ chúng là gì: " +
      "các bước, các tuyên bố, hay các khái niệm, mỗi ý một dòng."));
    var form = el("form", "editform");
    var wrap = el("label", "fld");
    wrap.htmlFor = "guess-text";
    wrap.appendChild(el("span", "", "Dự đoán của bạn"));
    var ta = el("textarea", "");
    ta.id = "guess-text";
    ta.rows = 6;
    ta.maxLength = 2000;
    var old = guessOf(id);
    if (old) ta.value = old.text;
    wrap.appendChild(ta);
    form.appendChild(wrap);
    var err = el("p", "errs");
    err.setAttribute("role", "alert");
    form.appendChild(err);
    var row = el("div", "row"), go1 = el("button", "", "Mở và so"), skip = el("button", "", "Bỏ qua, mở luôn");
    go1.type = "submit";
    skip.type = "button";
    row.appendChild(go1);
    row.appendChild(skip);
    form.appendChild(row);
    form.addEventListener("submit", function (ev) {
      ev.preventDefault();
      if (ta.value.trim().length < 10) {
        err.textContent = "Viết ít nhất một ý (10 ký tự) trước khi mở.";
        ta.focus();
        return;
      }
      putGuess(id, { text: ta.value.trim(), hits: [], at: new Date().toISOString().slice(0, 10) });
      go(id, null, true);
    });
    ta.addEventListener("input", function () { err.textContent = ""; });
    skip.addEventListener("click", function () { go(id, null, true); });
    var box = el("div", "edit");
    box.appendChild(form);
    c.appendChild(box);
    ta.focus();
  }

  // đặt điều người đọc đoán cạnh các ô thật; người đọc tự tick ý mình đã đoán trúng
  function compare(c, id) {
    var g = guessOf(id);
    if (!g) return;
    var kids = childrenOf(id), hits = Array.isArray(g.hits) ? g.hits.filter(function (x) { return kids.indexOf(x) >= 0; }) : [];
    var box = el("div", "guess");
    box.appendChild(el("h3", "", "Bạn đã đoán"));
    box.appendChild(el("p", "guess-text", g.text));
    box.appendChild(el("h3", "", "Tầng dưới thật: tick ý bạn đã đoán trúng"));
    var score = el("p", "muted", "");
    score.setAttribute("aria-live", "polite");
    function show() { score.textContent = "Trúng " + hits.length + "/" + kids.length + " ý."; }
    var ul = el("ul", "links");
    kids.forEach(function (k) {
      var li = el("li", ""), lab = el("label", "hit"), cb = el("input", "");
      cb.type = "checkbox";
      cb.checked = hits.indexOf(k) >= 0;
      cb.addEventListener("change", function () {
        hits = hits.filter(function (x) { return x !== k; });
        if (cb.checked) hits.push(k);
        putGuess(id, { text: g.text, hits: hits, at: g.at });
        show();
      });
      lab.appendChild(cb);
      lab.appendChild(el("span", "", " " + node(k).label));
      li.appendChild(lab);
      ul.appendChild(li);
    });
    box.appendChild(ul);
    show();
    box.appendChild(score);
    var again = el("button", "", "Đoán lại");
    again.type = "button";
    again.addEventListener("click", function () { askGuess(id); });  // bản cũ còn tới khi gửi bản mới
    var row = el("div", "row");
    row.appendChild(again);
    box.appendChild(row);
    c.appendChild(box);
  }

  function intro() {
    var c = document.getElementById("card");
    while (c.firstChild) c.removeChild(c.firstChild);
    if (tier && guessOf(tier)) {
      c.appendChild(el("p", "muted", "Tầng dưới của «" + ((node(tier) || {}).label || tier) + "»."));
      compare(c, tier);
      return;
    }
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
    if (D.edit) editTools(c, id, n);
    if (tier && guessOf(tier)) {
      var back = el("button", "inline", "So với dự đoán của bạn");
      back.type = "button";
      back.addEventListener("click", function () { selected = null; mark(); intro(); });
      c.appendChild(el("p", "", "")).appendChild(back);
    }
    var rf = (n.figures || []).filter(function (r) {  // đang tự đoán: hình "ở tầng dưới" kèm nhãn ô con, chưa hiện
      return fig(r.id) && !(predicting && r.why === "child" && !guessOf(id));
    });
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
  var predictBtn = document.getElementById("predict");
  function setPredict(on) {
    predicting = !!on;
    predictBtn.setAttribute("aria-pressed", predicting ? "true" : "false");
    predictBtn.textContent = "Tự đoán trước: " + (predicting ? "bật" : "tắt");
    save("paper-graph:predict-mode", predicting);
  }
  setPredict(load("paper-graph:predict-mode", false) === true);
  predictBtn.addEventListener("click", function () {
    setPredict(!predicting);
    if (selected !== null) card(selected); else intro();
  });
  document.getElementById("relayout").addEventListener("click", function () {
    if (D.edit) api("/api/move", { tier: tier, reset: true });
  });
  if (D.edit) say("Chế độ sửa: kéo ô để đặt chỗ (Alt + mũi tên bằng bàn phím), sửa chữ và khoá ô trong thẻ.", false);
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
    var t = ev.target && ev.target.tagName;
    if (t === "TEXTAREA" || t === "INPUT") return;  // đang gõ (dự đoán, sửa chữ): Escape không lùi tầng, không mất chữ
    if (ev.key === "Escape" && tier) { var up = (node(tier) || {}).parent || ""; go(up, tier, true); }
  });
  go("", null, false);
})();
