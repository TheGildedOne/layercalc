/* LayerCalc shared helpers. Loaded in <head> without defer so each
   calculator's inline script can use window.LC as soon as it runs. */
window.LC = (function () {
  "use strict";
  var PAGE_KEY = "lc:" + location.pathname;
  var CURRENCIES = ["$", "€", "£", "¥", "A$", "C$", "₹", "kr", "zł", "R$", "CHF"];

  function store(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function load(k) { try { var v = localStorage.getItem(k); return v == null ? null : JSON.parse(v); } catch (e) { return null; } }

  function currency() { return load("lc:currency") || "$"; }
  function setCurrency(s) {
    store("lc:currency", s);
    var els = document.querySelectorAll("[data-cur]");
    for (var i = 0; i < els.length; i++) els[i].textContent = s;
    document.dispatchEvent(new Event("lc:currency"));
  }

  function el(id) { return document.getElementById(id); }
  function num(id) {
    var e = el(id); if (!e) return NaN;
    var v = parseFloat(String(e.value).replace(",", "."));
    return isFinite(v) ? v : NaN;
  }
  function val(id) { var e = el(id); return e ? e.value : ""; }
  function checked(id) { var e = el(id); return !!(e && e.checked); }

  function fmt(x, d) {
    if (!isFinite(x)) return "—";
    if (d == null) d = Math.abs(x) >= 100 ? 1 : Math.abs(x) >= 10 ? 2 : 3;
    return x.toLocaleString(undefined, { maximumFractionDigits: d });
  }
  function money(x, d) {
    if (!isFinite(x)) return "—";
    if (d == null) d = Math.abs(x) < 0.1 && x !== 0 ? 3 : 2;
    return currency() + x.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function hours(h) {
    if (!isFinite(h)) return "—";
    var m = Math.round(h * 60);
    var d = Math.floor(m / 1440), hh = Math.floor((m % 1440) / 60), mm = m % 60;
    return (d ? d + "d " : "") + hh + "h " + (mm < 10 ? "0" : "") + mm + "m";
  }

  function out(id, text) { var e = el(id); if (e) e.textContent = text; }
  function html(id, h) { var e = el(id); if (e) e.innerHTML = h; }
  function show(id, on) { var e = el(id); if (e) e.hidden = !on; }
  function setClass(id, cls) { var e = el(id); if (e) e.className = cls; }

  /* Wire every field in a form to a compute function, persist values per page,
     and restore them on the next visit. Reset buttons restore HTML defaults. */
  function bind(formId, compute) {
    var form = el(formId); if (!form) return;
    var fields = form.querySelectorAll("input, select, textarea");
    var saved = load(PAGE_KEY) || {};
    var i, f;
    for (i = 0; i < fields.length; i++) {
      f = fields[i]; if (!f.id || saved[f.id] == null) continue;
      if (f.type === "checkbox" || f.type === "radio") f.checked = !!saved[f.id];
      else f.value = saved[f.id];
    }
    function persist() {
      var o = {};
      for (var j = 0; j < fields.length; j++) {
        var g = fields[j]; if (!g.id) continue;
        o[g.id] = (g.type === "checkbox" || g.type === "radio") ? g.checked : g.value;
      }
      store(PAGE_KEY, o);
    }
    function run() { try { compute(); } catch (e) { if (window.console) console.error(e); } }
    function onEdit() { persist(); run(); }
    for (i = 0; i < fields.length; i++) {
      fields[i].addEventListener("input", onEdit);
      fields[i].addEventListener("change", onEdit);
    }
    form.addEventListener("submit", function (e) { e.preventDefault(); run(); });
    var resets = form.querySelectorAll("[data-reset]");
    for (i = 0; i < resets.length; i++) {
      resets[i].addEventListener("click", function () {
        try { localStorage.removeItem(PAGE_KEY); } catch (e) {}
        form.reset();
        // selects with data-fill handlers need a change event to repopulate
        var ch = form.querySelectorAll("select");
        for (var k = 0; k < ch.length; k++) ch[k].dispatchEvent(new Event("change"));
        run();
      });
    }
    document.addEventListener("lc:currency", run);
    run();
  }

  /* A currency picker for cost tools. Renders into a container and keeps
     every [data-cur] symbol on the page in sync. */
  function currencyPicker(containerId) {
    var c = el(containerId); if (!c) return;
    var cur = currency();
    var h = '<label class="cur-label">Currency <select id="lc-currency" aria-label="Currency symbol">';
    for (var i = 0; i < CURRENCIES.length; i++) {
      h += '<option value="' + CURRENCIES[i] + '"' + (CURRENCIES[i] === cur ? " selected" : "") + ">" + CURRENCIES[i] + "</option>";
    }
    h += "</select></label>";
    c.innerHTML = h;
    el("lc-currency").addEventListener("change", function () { setCurrency(this.value); });
    var els = document.querySelectorAll("[data-cur]");
    for (var j = 0; j < els.length; j++) els[j].textContent = cur;
  }

  function copyButton(btnId, getText) {
    var b = el(btnId); if (!b) return;
    b.addEventListener("click", function () {
      var t = getText();
      var done = function () { var old = b.textContent; b.textContent = "Copied"; setTimeout(function () { b.textContent = old; }, 1500); };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(t).then(done, function () { fallback(t); done(); });
      else { fallback(t); done(); }
    });
    function fallback(t) {
      var ta = document.createElement("textarea"); ta.value = t; ta.style.position = "fixed"; ta.style.opacity = "0";
      document.body.appendChild(ta); ta.select(); try { document.execCommand("copy"); } catch (e) {} document.body.removeChild(ta);
    }
  }

  function download(filename, text, mime) {
    var blob = new Blob([text], { type: mime || "text/plain" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a"); a.href = url; a.download = filename;
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
  }

  /* Swap which radio-controlled panels are visible: data-mode on panels,
     name on the radios. */
  function modePanels(radioName, attr) {
    attr = attr || "data-mode";
    var radios = document.getElementsByName(radioName);
    function apply() {
      var v = "";
      for (var i = 0; i < radios.length; i++) if (radios[i].checked) v = radios[i].value;
      var panels = document.querySelectorAll("[" + attr + "]");
      for (var j = 0; j < panels.length; j++) {
        var modes = panels[j].getAttribute(attr).split(" ");
        panels[j].hidden = modes.indexOf(v) === -1;
      }
      return v;
    }
    for (var i = 0; i < radios.length; i++) radios[i].addEventListener("change", apply);
    return apply;
  }

  return {
    num: num, val: val, checked: checked, fmt: fmt, money: money, hours: hours,
    out: out, html: html, show: show, setClass: setClass, bind: bind,
    currency: currency, currencyPicker: currencyPicker, copyButton: copyButton,
    download: download, modePanels: modePanels, el: el, store: store, load: load
  };
})();
