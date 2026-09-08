/*
 * A DOM shim just large enough to run the calculators headlessly.
 *
 * The calculators use a deliberately narrow slice of the DOM — getElementById,
 * a handful of querySelectorAll patterns, value/checked/textContent/hidden, and
 * input/change events. Implementing that slice in ~200 lines is far less
 * fragile than pulling in jsdom, and it keeps the repo dependency-free, which
 * is the whole point of how this site is built.
 *
 * Elements are parsed out of the built HTML by regex. That is not a real HTML
 * parser and would be wrong for arbitrary markup; it is fine here because the
 * markup is ours and its shape is known.
 */

"use strict";

function Element(tag, attrs) {
  this.tagName = (tag || "div").toUpperCase();
  this.attrs = attrs || {};
  this.id = this.attrs.id || "";
  this.type = this.attrs.type || (this.tagName === "SELECT" ? "select" : "text");
  this.value = this.attrs.value != null ? this.attrs.value : "";
  this.checked = "checked" in this.attrs;
  this.name = this.attrs.name || "";
  this.hidden = "hidden" in this.attrs;
  this.className = this.attrs.class || "";
  this.textContent = "";
  this._innerHTML = "";
  this._injected = [];
  this.options = [];
  this._listeners = {};
  this.children = [];
}
Object.defineProperty(Element.prototype, "innerHTML", {
  get: function () { return this._innerHTML; },
  set: function (v) {
    this._innerHTML = String(v);
    if (!this._doc) return;
    // drop anything this element injected previously, then register the new markup
    var doc = this._doc, mine = this._injected;
    doc.all = doc.all.filter(function (e) { return mine.indexOf(e) < 0; });
    this._injected = doc._scan(this._innerHTML, true);
  }
});
Element.prototype.addEventListener = function (type, fn) {
  (this._listeners[type] = this._listeners[type] || []).push(fn);
};
Element.prototype.dispatchEvent = function (ev) {
  var ls = this._listeners[ev.type] || [];
  for (var i = 0; i < ls.length; i++) ls[i].call(this, ev);
  return true;
};
Element.prototype.getAttribute = function (n) {
  return n in this.attrs ? this.attrs[n] : null;
};
Element.prototype.setAttribute = function (n, v) { this.attrs[n] = v; };
Element.prototype.querySelectorAll = function (sel) { return this._doc._select(sel, this); };
Element.prototype.querySelector = function (sel) { var r = this.querySelectorAll(sel); return r[0] || null; };
Element.prototype.reset = function () {
  for (var i = 0; i < this._doc.all.length; i++) {
    var e = this._doc.all[i];
    if (!e._inForm) continue;
    if (e.type === "checkbox" || e.type === "radio") e.checked = "checked" in e.attrs;
    else e.value = e.attrs.value != null ? e.attrs.value : (e.tagName === "SELECT" ? e._defaultOption : "");
  }
};

function parseAttrs(s) {
  var out = {}, re = /([a-zA-Z_:][-a-zA-Z0-9_:.]*)(?:\s*=\s*"([^"]*)")?/g, m;
  while ((m = re.exec(s))) out[m[1]] = m[2] != null ? m[2] : "";
  return out;
}

function Document(html) {
  this.all = [];
  this._listeners = {};
  this._scan(html, true);
  this.body = new Element("body", {});
  this.body._doc = this;
  this.documentElement = new Element("html", {});
}

/* Pull elements out of a chunk of markup and, if `register`, add them to the
   document. Returns the elements found, so innerHTML can undo its own injection. */
Document.prototype._scan = function (html, register) {
  var tagRe = /<(input|select|option|textarea|button|form|div|span|p|pre|table|tbody|tr|td|section|fieldset|label)(\s[^>]*)?>/gi;
  var m, inForm = false, currentSelect = null, found = [];
  while ((m = tagRe.exec(html))) {
    var tag = m[1].toLowerCase(), attrs = parseAttrs(m[2] || "");
    if (tag === "option") {
      if (currentSelect) {
        var val = attrs.value != null ? attrs.value : "";
        currentSelect.options.push({ value: val, selected: "selected" in attrs });
        if ("selected" in attrs) { currentSelect.value = val; currentSelect._defaultOption = val; }
      }
      continue;
    }
    if (currentSelect) {
      // a select ends at the next </select>; anything after that is outside it
      var rest = html.slice(0, m.index);
      if (rest.lastIndexOf("</select>") > rest.lastIndexOf("<select")) currentSelect = null;
    }
    var el = new Element(tag, attrs);
    el._doc = this;
    el._inForm = inForm || tag === "form";
    if (tag === "form") inForm = true;
    if (tag === "select") { currentSelect = el; el.value = ""; el._defaultOption = ""; }
    found.push(el);
    if (register !== false) this.all.push(el);
  }
  for (var i = 0; i < found.length; i++) {
    var sel = found[i];
    if (sel.tagName === "SELECT" && sel.value === "" && sel.options.length) {
      sel.value = sel.options[0].value; sel._defaultOption = sel.options[0].value;
    }
  }
  return found;
};

Document.prototype.getElementById = function (id) {
  for (var i = 0; i < this.all.length; i++) if (this.all[i].id === id) return this.all[i];
  return null;
};
Document.prototype.getElementsByName = function (n) {
  return this.all.filter(function (e) { return e.name === n; });
};
Document.prototype._select = function (sel, scope) {
  var all = this.all;
  sel = sel.trim();
  // comma-separated tag list, e.g. "input, select, textarea"
  if (/^[a-z]+(\s*,\s*[a-z]+)+$/i.test(sel)) {
    var tags = sel.split(",").map(function (t) { return t.trim().toUpperCase(); });
    return all.filter(function (e) { return tags.indexOf(e.tagName) >= 0; });
  }
  // attribute selector, e.g. "[data-cur]", "[data-fep]", "[data-reset]"
  var am = sel.match(/^\[([-a-zA-Z0-9_]+)\]$/);
  if (am) return all.filter(function (e) { return am[1] in e.attrs; });
  // class selector, possibly with :not([hidden])
  var cm = sel.match(/^\.([-a-zA-Z0-9_]+)(:not\(\[hidden\]\))?$/);
  if (cm) {
    return all.filter(function (e) {
      var has = (" " + e.className + " ").indexOf(" " + cm[1] + " ") >= 0;
      return has && (!cm[2] || !e.hidden);
    });
  }
  if (/^[a-z]+$/i.test(sel)) {
    return all.filter(function (e) { return e.tagName === sel.toUpperCase(); });
  }
  return [];
};
Document.prototype.querySelectorAll = function (sel) { return this._select(sel); };
Document.prototype.querySelector = function (sel) { var r = this._select(sel); return r[0] || null; };
Document.prototype.addEventListener = function (t, fn) { (this._listeners[t] = this._listeners[t] || []).push(fn); };
Document.prototype.dispatchEvent = function (ev) {
  var ls = this._listeners[ev.type] || [];
  for (var i = 0; i < ls.length; i++) ls[i].call(this, ev);
  return true;
};
Document.prototype.createElement = function (t) { var e = new Element(t, {}); e._doc = this; return e; };

/* Build a sandbox: parse `html`, run app.js, then each inline <script>. */
function makeEnv(html, appJs) {
  var doc = new Document(html);
  var store = {};
  var sandbox = {
    document: doc,
    localStorage: {
      getItem: function (k) { return k in store ? store[k] : null; },
      setItem: function (k, v) { store[k] = String(v); },
      removeItem: function (k) { delete store[k]; }
    },
    location: { pathname: "/test/" },
    navigator: {},
    console: console,
    Event: function (type) { this.type = type; },
    Math: Math, JSON: JSON, parseFloat: parseFloat, parseInt: parseInt,
    isFinite: isFinite, isNaN: isNaN, Date: Date, String: String,
    Number: Number, Array: Array, Object: Object, RegExp: RegExp,
    setTimeout: function () {}, Blob: function () {}, URL: { createObjectURL: function () { return ""; }, revokeObjectURL: function () {} }
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;

  var vm = require("vm");
  var ctx = vm.createContext(sandbox);
  vm.runInContext(appJs, ctx, { filename: "app.js" });

  var scripts = html.match(/<script>([\s\S]*?)<\/script>/g) || [];
  for (var i = 0; i < scripts.length; i++) {
    var body = scripts[i].replace(/^<script>/, "").replace(/<\/script>$/, "");
    if (!body.trim()) continue;
    vm.runInContext(body, ctx, { filename: "inline-" + i + ".js" });
  }
  return { doc: doc, sandbox: sandbox };
}

module.exports = { makeEnv: makeEnv, Document: Document };
