// Trang làm bài đo hiểu bài của paper-graph. Dữ liệu nhúng trong #data (JSON đã thoát ký tự); chữ chỉ vào trang bằng
// textContent (TM-13). Chấm ngay trong trang, đo thời gian từ lúc bấm "Bắt đầu", và cho một dòng kết quả để chép lại.
(function () {
  "use strict";
  var D = JSON.parse(document.getElementById("data").textContent);
  var started = 0, how = "";
  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined && text !== null) e.textContent = String(text);
    return e;
  }
  function kindName(k) { return D.kinds && Object.prototype.hasOwnProperty.call(D.kinds, k) ? D.kinds[k] : ""; }
  document.getElementById("title").textContent = String(D.title || "");

  document.getElementById("begin").addEventListener("click", function () {
    var picked = document.querySelector('input[name="how"]:checked');
    if (!picked) { document.getElementById("start-err").textContent = "Chọn cách bạn đã đọc bài trước."; return; }
    how = picked.value;
    started = Date.now();
    document.getElementById("start").hidden = true;
    build();
  });
  document.querySelectorAll('input[name="how"]').forEach(function (r) {
    r.addEventListener("change", function () { document.getElementById("start-err").textContent = ""; });
  });

  function build() {
    var f = document.getElementById("quiz");
    D.questions.forEach(function (q, i) {
      var fs = el("fieldset", "q");
      var lg = el("legend", "", (i + 1) + ". " + q.q);
      fs.appendChild(lg);
      fs.appendChild(el("p", "kind", kindName(q.kind)));
      q.choices.concat(["Không biết"]).forEach(function (c, j) {
        var lab = el("label", "choice"), r = el("input", "");
        r.type = "radio";
        r.name = "q-" + i;
        r.value = String(j < q.choices.length ? j : -1);
        lab.appendChild(r);
        lab.appendChild(el("span", "", " " + c));
        fs.appendChild(lab);
      });
      f.appendChild(fs);
    });
    var err = el("p", "err");
    err.setAttribute("role", "alert");
    f.appendChild(err);
    var b = el("button", "", "Nộp bài");
    b.type = "submit";
    f.appendChild(b);
    f.hidden = false;
    f.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var answers = D.questions.map(function (q, i) {
        var r = f.querySelector('input[name="q-' + i + '"]:checked');
        return r ? Number(r.value) : null;
      });
      var missing = answers.indexOf(null);
      if (missing >= 0) { err.textContent = "Câu " + (missing + 1) + " chưa chọn (chọn \"Không biết\" nếu không biết)."; return; }
      err.textContent = "";
      grade(answers);
    });
    f.querySelector("input").focus();
  }

  function grade(answers) {
    var secs = Math.round((Date.now() - started) / 1000), right = 0;
    var f = document.getElementById("quiz"), res = document.getElementById("result");
    f.querySelectorAll("input").forEach(function (x) { x.disabled = true; });
    f.querySelector('button[type="submit"]').hidden = true;
    D.questions.forEach(function (q, i) {
      var ok = answers[i] === q.answer;
      if (ok) right += 1;
      var fs = f.querySelectorAll("fieldset.q")[i];
      fs.classList.add(ok ? "ok" : "bad");
      var fb = el("div", "fb");
      fb.appendChild(el("p", "verdict", ok ? "Đúng." : "Chưa đúng. Đáp án: " + q.choices[q.answer]));
      if (q.explain) fb.appendChild(el("p", "", q.explain));
      (q.anchors || []).forEach(function (a) {
        var bq = el("blockquote", "", a.quote);
        bq.appendChild(el("span", "where", "trang " + Number(a.page)));
        fb.appendChild(bq);
      });
      fs.appendChild(fb);
    });
    while (res.firstChild) res.removeChild(res.firstChild);
    res.appendChild(el("h2", "", "Đúng " + right + "/" + D.questions.length + " câu, trong " + Math.floor(secs / 60) + " phút " + (secs % 60) + " giây"));
    var line = JSON.stringify({ bai: String(D.sha256).slice(0, 12), cach_doc: how, dung: right, tong: D.questions.length,
      giay: secs, tra_loi: answers });
    res.appendChild(el("p", "", "Chép dòng dưới đây gửi cho người tổ chức đo:"));
    var pre = el("pre", "line", line);
    res.appendChild(pre);
    var copy = el("button", "", "Chép");
    copy.type = "button";
    copy.addEventListener("click", function () {
      var done = function () { copy.textContent = "Đã chép"; };
      var fallback = function () {
        var r = document.createRange(); r.selectNodeContents(pre);
        var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
        copy.textContent = "Đã chọn, bấm Cmd/Ctrl+C";
      };
      try { navigator.clipboard.writeText(line).then(done, fallback); } catch (e) { fallback(); }
    });
    res.appendChild(copy);
    res.hidden = false;
    res.scrollIntoView();
  }
})();
