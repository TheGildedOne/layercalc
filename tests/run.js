#!/usr/bin/env node
/*
 * Calculator tests. Loads each built page, drives its real form, and checks the
 * real output text — no reimplementation of the formulas here, because a test
 * that restates the maths tests nothing.
 *
 * Run after a build:  node tests/run.js
 */
"use strict";

const fs = require("fs");
const path = require("path");
const { makeEnv } = require("./dom.js");

const DIST = path.join(__dirname, "..", "dist");
const APP = fs.readFileSync(path.join(DIST, "static", "app.js"), "utf8");

let passed = 0, failed = 0;
const failures = [];

function load(slug) {
  const html = fs.readFileSync(path.join(DIST, slug, "index.html"), "utf8");
  const env = makeEnv(html, APP);
  const doc = env.doc;
  return {
    doc,
    set(id, value) {
      const el = doc.getElementById(id);
      if (!el) throw new Error(`no element #${id} on /${slug}/`);
      if (el.type === "checkbox" || el.type === "radio") el.checked = !!value;
      else el.value = String(value);
      el.dispatchEvent({ type: el.tagName === "SELECT" ? "change" : "input" });
      // selects that feed other fields also listen for change
      if (el.tagName === "SELECT") el.dispatchEvent({ type: "input" });
      return this;
    },
    pick(id) {                       // choose a radio in a group
      const el = doc.getElementById(id);
      if (!el) throw new Error(`no radio #${id} on /${slug}/`);
      doc.getElementsByName(el.name).forEach(r => { r.checked = false; });
      el.checked = true;
      el.dispatchEvent({ type: "change" });
      return this;
    },
    text(id) {
      const el = doc.getElementById(id);
      if (!el) throw new Error(`no output #${id} on /${slug}/`);
      return String(el.textContent).trim();
    },
    hidden(id) { return !!doc.getElementById(id).hidden; }
  };
}

function check(name, actual, expected) {
  const ok = expected instanceof RegExp ? expected.test(actual) : actual === expected;
  if (ok) { passed++; }
  else { failed++; failures.push(`${name}\n      expected: ${expected}\n      actual:   ${actual}`); }
}

function group(title, fn) {
  process.stdout.write(`  ${title}\n`);
  try { fn(); } catch (e) { failed++; failures.push(`${title} threw: ${e.message}`); }
}

/* ------------------------------------------------------------------ cost */

group("filament-cost-calculator", () => {
  const p = load("filament-cost-calculator");
  // $20 per 1000 g, 50 g used, 5% waste, 0% failure
  check("cost of 50 g at $0.02/g", p.text("r_cost"), "$1.00");
  check("cost per gram", p.text("r_perg"), "$0.0200");
  check("with 5% waste", p.text("r_adj"), "$1.05");
  check("PLA g/m shown", p.text("r_gpm"), /2\.98 g per meter/);

  // failure rate divides, not multiplies
  p.set("fail", 10);
  check("10% failure -> /0.9", p.text("r_adj"), "$1.17");

  // meters mode converts via density
  p.set("fail", 0).set("waste", 0).set("unit", "m").set("used", 100);
  check("100 m of PLA = 298 g", p.text("r_grams"), /^298\.\d g/);

  // prints per spool, adjusted for waste and failures
  p.set("fail", 0).set("waste", 0).set("unit", "g").set("used", 50);
  check("20 prints from a clean kilo", p.text("r_prints"), "20");
  p.set("waste", 5).set("fail", 5);
  check("waste and failures cut it to 18", p.text("r_prints"), "18");
  p.set("waste", 5).set("fail", 0);

  // edge: zero spool weight must not print Infinity
  p.set("unit", "g").set("used", 50).set("spool", 0);
  check("zero spool weight", p.text("r_perg"), "—");
});

group("3d-print-pricing-calculator", () => {
  const p = load("3d-print-pricing-calculator");
  check("total cost", p.text("r_cost"), "$8.16");
  check("price at 50% markup", p.text("r_price"), "$12.24");
  check("margin stated correctly", p.text("r_margin"), "50% markup = 33% margin");
  check("profit", p.text("r_profit"), "$4.08");
  check("material line", p.text("b_mat"), "$1.32");
  check("depreciation line", p.text("b_dep"), "$0.80");

  // Etsy fees are worked backwards from the target, not added on
  p.set("mkt", "etsy");
  check("etsy list price", p.text("r_list"), "$14.02");
  check("etsy fee amount", p.text("r_fees"), /fees \$1\.78/);

  // no marketplace -> list == price
  p.set("mkt", "none");
  check("direct list == price", p.text("r_list"), p.text("r_price"));

  // G-code header parsing - PrusaSlicer/Orca/Bambu format
  p.set("gcode", "; filament used [g] = 61.2\n; estimated printing time (normal mode) = 6h 12m 30s\n");
  p.doc.getElementById("readgc").dispatchEvent({ type: "click" });
  check("gcode filled grams", p.doc.getElementById("g").value, "61.20");
  check("gcode filled hours", p.doc.getElementById("hrs").value, "6.21");
  check("gcode status reports both", p.text("gcstatus"), /61\.2 g and 6h 1[23]m/);

  // Cura format: seconds and metres
  p.set("gcode", ";Filament used: 20.4m\n;TIME:22350\n");
  p.doc.getElementById("readgc").dispatchEvent({ type: "click" });
  check("cura time parsed", p.doc.getElementById("hrs").value, "6.21");

  // nonsense input must not corrupt the form
  const gBefore = p.doc.getElementById("g").value;
  p.set("gcode", "hello, this is not gcode");
  p.doc.getElementById("readgc").dispatchEvent({ type: "click" });
  check("junk gcode says so", p.text("gcstatus"), /Couldn't find/);
  check("junk gcode leaves fields alone", p.doc.getElementById("g").value, gBefore);

  p.set("mkt", "none").set("g", 60).set("hrs", 6);
  // edge: zero labour must not break the per-hour line
  p.set("lab", 0);
  check("zero labour minutes", p.text("r_hourly"), "");
});

group("resin-print-cost-calculator", () => {
  const p = load("resin-print-cost-calculator");
  // defaults: $30/1000 ml, 25 ml, 10% waste, 1200 layers of 6000, $8 sheet
  check("resin incl. waste", p.text("r_resin"), "$0.83");
  check("per ml", p.text("r_perml"), /\$0\.030 per ml/);
  check("FEP by layers", p.text("r_fep"), "$1.60");
  check("FEP share text", p.text("r_feps"), /1,?200 of 6,?000 layers/);
  check("LCD amortisation", p.text("r_lcd"), "$0.090");   // <$0.10 renders 3 dp

  // FEP must scale with layer count - the whole point of the change
  p.set("layers", 2400);
  check("double layers doubles FEP", p.text("r_fep"), "$3.20");
  p.set("layers", 1200);

  // grams in, converted by density
  p.set("usedunit", "g").set("used", 27.5);       // 27.5 g / 1.10 = 25 ml
  check("27.5 g at 1.10 = 25 ml cost", p.text("r_resin"), "$0.83");

  // bottle sold by weight
  p.set("usedunit", "ml").set("used", 25).set("bsizeunit", "kg").set("bsize", 1);
  check("1 kg bottle at 1.10 = 909 ml", p.text("r_perml"), /\$0\.033 per ml/);

  // IPA per-change mode: 500 ml / 15 prints = 33 ml
  check("IPA per change", p.text("r_washs"), /33 ml per print/);
  p.pick("ipa_simple").set("ipaml", 30);
  check("IPA simple mode", p.text("r_wash"), "$0.24");

  // LCD toggle off
  p.set("uselcd", false);
  check("LCD excluded", p.text("r_lcd"), "—");

  // implausible density warns
  p.set("usedunit", "g").set("restype", "custom").set("dens", 2.5);
  check("silly density warns", p.hidden("warn"), false);
});

group("3d-printer-electricity-cost-calculator", () => {
  const p = load("3d-printer-electricity-cost-calculator");
  // Warm-up is modelled separately: 330 W for 4 min, then 120 W for the rest.
  // 0.022 + 0.952 = 0.974 kWh -> $0.146
  check("8 h incl. warm-up", p.text("r_print"), "$0.15");
  check("kWh incl. warm-up", p.text("r_kwh"), /0\.97 kWh/);
  check("warm-up share of a long print", p.text("r_warm"), "2 %");
  check("says heating is minor here", p.text("r_warms"), /small part of a print this long/);
  check("per 24 h", p.text("r_day"), "$0.43");

  // On a 15-minute print, heating is half the energy
  p.set("hrs", 0.25);
  check("warm-up dominates a short print", p.text("r_warm"), "50 %");
  check("and says so", p.text("r_warms"), /heating dominates/);
  p.set("hrs", 8);

  // with no warm-up entered it reduces to the simple model
  p.set("warmmin", 0);
  check("no warm-up = flat model", p.text("r_print"), "$0.14");
  check("no warm-up kWh", p.text("r_kwh"), /0\.96 kWh/);
  p.set("warmmin", 4);

  // idle draw: 8 W for 8 h/day is 23 kWh a year
  check("idle hidden until entered", p.hidden("idlebox"), true);
  p.set("idleh", 8);
  check("idle cost per year", p.text("r_idle"), "$3.50");
  p.set("idleh", 0);

  // zero steady draw still has the warm-up
  p.set("watts", 0);
  check("zero steady watts keeps warm-up", p.text("r_print"), "$0.003");
});

/* ----------------------------------------------------------- calibration */

group("e-steps-calculator", () => {
  const p = load("e-steps-calculator");
  // 93 steps, asked 100, mark 120, 23 left -> 97 actual -> 93*100/97
  p.set("rem", 23);
  check("marlin e-steps", p.text("r_new"), "95.88");
  check("actual extruded", p.text("r_actual"), "97 mm");
  check("under-extrusion wording", p.text("r_err"), /under-extruding by 3 mm/);
  check("marlin gcode", p.text("snippet"), /M92 E95\.88/);

  // Switching to Klipper adopts its documented procedure: 70 mm mark, 50 mm extruded
  p.pick("fw_klipper");
  check("klipper default extrude length", p.doc.getElementById("req").value, "50");
  check("klipper default mark", p.doc.getElementById("mark").value, "70");
  check("klipper cites F60", p.text("reqhint"), /G1 E50 F60/);

  // Klipper inverts the formula - the bug this tool exists to prevent - and
  // rounds to 3 dp per its own docs. 33.5 * 47 / 50 = 31.490
  p.set("cur", 33.5).set("rem", 23);
  check("klipper rotation_distance", p.text("r_new"), "31.490");
  check("klipper config snippet", p.text("snippet"), /rotation_distance: 31\.490/);
  // a >2 mm miss is Klipper's own repeat threshold
  check("klipper 3 mm miss prompts a repeat", p.hidden("warn"), false);

  // switching back restores the Marlin convention
  p.pick("fw_marlin");
  check("marlin default extrude length", p.doc.getElementById("req").value, "100");
  check("marlin default mark", p.doc.getElementById("mark").value, "120");

  // exact calibration reads cleanly, not "exactly-extruding by 0 mm"
  p.set("cur", 93).set("rem", 20);
  check("perfect calibration", p.text("r_new"), "93.00");
  check("no awkward zero wording", p.text("r_err"), "exactly what was requested");
  check("no warning when correct", p.hidden("warn"), true);

  // >10% change warns (slipping, not e-steps)
  p.set("rem", 60);
  check("large change warns", p.hidden("warn"), false);

  // --- Marlin <-> Klipper conversion. A different job from calibration.
  // Klipper documents: rotation_distance = full_steps x microsteps / steps_per_mm
  check("93 steps/mm -> rotation_distance", p.text("r_convert"), "34.409");
  check("shows the working", p.text("r_converts"), /200 × 16 ÷ 93/);
  check("config snippet", p.text("convsnippet"), /rotation_distance: 34\.409/);
  check("snippet carries microsteps", p.text("convsnippet"), /microsteps: 16/);
  check("no warning for a normal value", p.hidden("convwarn"), true);

  // Geared extruder: a BMG is 415 steps/mm with the 50:17 gearing baked in
  p.set("cspm", 415);
  check("BMG without gear_ratio", p.text("r_convert"), "7.711");
  check("warns about the gear_ratio trap", p.hidden("convwarn"), false);
  p.set("cusegear", true).set("cgear", "50:17");
  check("BMG with gear_ratio 50:17", p.text("r_convert"), "22.679");
  check("gear_ratio written to config", p.text("convsnippet"), /gear_ratio: 50:17/);

  // Back the other way must round-trip
  p.pick("conv_tomarlin").set("crd", 22.679);
  check("Klipper -> Marlin", p.text("r_convert"), "415.00");
  check("Marlin snippet", p.text("convsnippet"), /M92 E415\.00/);

  // Nonsense ratio must say so rather than return a number
  p.set("cgear", "banana");
  check("unparseable ratio warns", p.hidden("convwarn"), false);

  // 0.9 degree motor doubles it
  p.set("cusegear", false).pick("conv_tokl").set("cspm", 93).set("cfs", "400");
  check("0.9 deg motor", p.text("r_convert"), "68.817");
});

group("flow-rate-calculator", () => {
  const p = load("flow-rate-calculator");
  check("new flow percent", p.text("r_new"), "93.8 %");
  check("ratio equivalent", p.text("r_alt"), /0\.938/);
  check("average wall", p.text("r_avg"), "0.480 mm");
  p.set("fmt", "ratio").set("cur", 1);
  check("ratio mode output", p.text("r_new"), "0.938");
  // measurement sensitivity - 0.02 / 0.480 = 4.2%
  check("caliper sensitivity shown", p.text("r_sens"), "±4.2 %");
  // thicker walls are proportionally less sensitive
  p.set("w1", 0.9).set("w2", 0.9).set("w3", 0.9).set("w4", 0.9).set("exp", 0.85);
  check("thicker walls less sensitive", p.text("r_sens"), "±2.2 %");
  p.set("w1", 0.48).set("w2", 0.47).set("w3", 0.49).set("w4", 0.48).set("exp", 0.45);

  // wildly uneven walls warn
  p.set("fmt", "pct").set("cur", 100).set("w1", 0.4).set("w4", 0.6);
  check("uneven walls warn", p.hidden("warn"), false);
});

group("shrinkage-compensation-calculator", () => {
  const p = load("shrinkage-compensation-calculator");
  check("X scale", p.text("r_x"), "100.60 %");
  check("Y scale", p.text("r_y"), "100.50 %");
  check("XY scale factor", p.text("r_xy"), "100.55 %");
  check("Z not measured", p.text("r_z"), "—");

  // The two numbers are reciprocals and must never be confused: Orca wants the
  // measured percentage, everyone else wants the scale factor.
  check("measured percentage", p.text("r_shrinkpct"), "99.45 %");
  check("orca gets the measured percentage", p.text("r_value"), "99.45 %");
  check("orca field named", p.text("r_fieldlabel"), "Shrinkage (XY)");
  check("orca warned off the scale factor", p.text("note"), /Do not type 100\.55/);

  p.set("slicer", "prusa");
  check("prusa gets the scale factor", p.text("r_value"), "100.55 %");
  check("prusa has no shrinkage field", p.text("r_fieldlabel"), "Scale");
  // PrusaSlicer's XY size compensation moves every contour, so the sign flips
  // and it must warn about the side effect
  check("prusa hole value inverted", p.text("r_hole"), "-0.200 mm");
  check("prusa side effect stated", p.text("r_holes"), /also changes outer dimensions/);

  p.set("slicer", "cura");
  check("cura gets the scale factor", p.text("r_value"), "100.55 %");
  check("cura hole field", p.text("r_holelabel"), "Hole Horizontal Expansion");
  check("cura hole value", p.text("r_hole"), "+0.200 mm");

  p.set("slicer", "orca");
  // hole compensation is a radius, so half the diameter error
  check("hole compensation is per side", p.text("r_hole"), "+0.200 mm");

  // oversize part -> scale below 100, measured percentage above
  p.set("mx", 100.6).set("my", 100.5);
  check("oversize X", p.text("r_x"), "99.40 %");
  check("oversize inverts both", p.text("r_shrinkpct"), "100.55 %");
  p.set("mx", 99.4).set("my", 99.5);

  // X/Y disagreement is mechanical, not material - must warn
  p.set("my", 100.4);
  check("X/Y mismatch warns", p.hidden("warn"), false);
  p.set("my", 99.5);
  // implausibly large correction warns
  p.set("mx", 90).set("my", 90);
  check("absurd correction warns", p.hidden("warn"), false);
});

group("layer-height-calculator", () => {
  const p = load("layer-height-calculator");

  // --- geometry: 8 mm lead / 200 steps = 0.04 mm full step
  check("full step 0.04 mm", p.text("r_full"), "40.0 µm");

  // --- stair-stepping: cusp = h*cos(angle), step width = h/tan(angle)
  // 0.2 mm at 45 degrees -> 0.1414 mm deviation, 0.2 mm step
  check("cusp at 45 deg", p.text("r_cusp"), "141 µm deviation");
  check("step width at 45 deg", p.text("r_cusps"), /each step is 200 µm wide/);
  // the shallow-slope case the article cites: 15 deg gives a 0.75 mm step
  p.set("angle", 15);
  check("cusp at 15 deg", p.text("r_cusp"), "193 µm deviation");
  check("shallow slope steps 0.75 mm", p.text("r_cusps"), /each step is 0\.75 mm wide/);
  check("shallow slope reads as visible", p.text("r_cusps"), /prominent terracing/);
  // vertical walls never step, whatever the layer height
  p.set("angle", 90);
  check("vertical wall has no deviation", p.text("r_cusp"), "0 µm deviation");
  p.set("angle", 45);

  // --- inverse solve: height needed for under 50 um deviation on this slope
  check("height for 50 um at 45 deg", p.text("r_need"), /0\.071 mm or finer/);
  // 0.071 rounds down to a 0.04 mm full-step height, which is below the usable
  // range for a 0.4 nozzle - the tool must not recommend it
  check("no impractical suggestion", p.text("r_needs"), "for under 50 µm deviation");
  // on a steeper slope the answer is practical, and it names the full-step height
  p.set("angle", 75);
  check("steep slope suggestion", p.text("r_needs"), /nearest full-step height is 0\.16 mm/);
  p.set("angle", 45);

  // --- flow ceiling. area(0.2,0.45)=0.0814 -> 184 mm/s, above the 150 setting
  check("not flow limited at 0.2", p.text("r_max"), "150 mm/s");
  check("says so", p.text("r_maxs"), /not flow-limited/);
  // coarser layers hit the ceiling: area(0.28,0.45)=0.1092 -> 137 mm/s
  p.set("check", 0.28);
  check("flow limited at 0.28", p.text("r_max"), "137 mm/s");
  check("flags the cap", p.text("r_maxs"), /flow-limited/);
  p.set("check", 0.2);

  // --- feature fit: 5 mm is exactly 25 layers at 0.2
  check("5 mm fits 0.2 exactly", p.text("r_fit"), "Exact");
  check("layer count given", p.text("r_fits"), /25 layers exactly/);
  // at 0.3 it is 16.67 layers -> printer makes 17 -> 5.1 mm
  p.set("check", 0.3);
  check("5 mm at 0.3 overshoots", p.text("r_fit"), "+100 µm out");
  check("shows the rounding", p.text("r_fits"), /16\.67 layers/);
  check("suggests heights that divide exactly", p.text("r_exact"), /0\.2/);
  p.set("check", 0.2);
  // blank feature height must not break anything
  p.set("feat", "");
  check("blank feature height", p.text("r_fit"), "—");
  p.set("feat", 5);

  // --- magic numbers, correctly weighted
  check("0.20 mm is on full steps", p.text("r_period"), "none");
  check("verdict for a magic height", p.text("r_verdict"), "No downside");
  p.set("check", 0.15);
  check("0.15 mm repeat period", p.text("r_period"), "every 4 layers");
  check("repeat distance given", p.text("r_periods"), /every 0\.60 mm/);
  check("modern driver verdict", p.text("r_verdict"), "Doesn't matter");
  p.set("driver", "legacy");
  check("legacy driver verdict", p.text("r_verdict"), /Worth choosing/);
  p.set("driver", "modern").set("check", 0.2);

  // --- comparison table
  const rows = p.doc.getElementById("rows").innerHTML;
  check("table marks non-magic heights", /✗/.test(rows), true);
  check("table flags flow-capped rows", /\*/.test(rows), true);
  check("selected row is marked", /◀/.test(rows), true);

  // --- fine-lead Z: 0.01 mm full step
  p.set("preset", "2,200,16,1");
  check("T8x2 full step", p.text("r_full"), "10.0 µm");
});

group("max-volumetric-speed-calculator", () => {
  const p = load("max-volumetric-speed-calculator");
  check("flow at defaults", p.text("r_flow"), "12.2 mm³/s");
  check("max speed", p.text("r_max"), "184 mm/s");
  check("verdict comfortable", p.text("r_verdict"), /81% of the hotend limit/);
  // exceeding the limit must flag
  p.set("speed", 300);
  check("over limit flagged", p.text("r_verdict"), /the slicer will cap this/);
  p.set("speed", 150);

  // derated figure for the slicer - bench tests read high
  check("10% margin off 15", p.text("r_safe"), "13.5 mm³/s");
  check("margin explained", p.text("r_safes"), /10% below your measured 15/);
  p.set("derate", 0);
  check("no margin", p.text("r_safe"), "15.0 mm³/s");
  p.set("derate", 10);

  // Ellis-style test commands: feed speed = flow / filament cross-section.
  // 1.75 mm area = 2.4053 mm^2, so 10 mm3/s = 4.157 mm/s = F249
  const gc = p.text("testgc");
  check("test commands generated", gc, /M83/);
  check("10 mm3\/s line", gc, /G1 E100 F249 {3}; 10 mm³\/s/);
  check("filament feed rate shown", gc, /4\.2 mm\/s of filament/);
  // 2.85 mm filament needs a much lower feed rate for the same flow
  p.set("fdia", "2.85");
  check("2.85 mm rescales the test", p.text("testgc"), /G1 E100 F94 {3}; 10 mm³\/s/);
});

group("belt-tension-calculator", () => {
  const p = load("belt-tension-calculator");
  // T = 4 L^2 f^2 mu = 4 * 0.15^2 * 110^2 * 0.008
  check("110 Hz at 150 mm", p.text("r_t"), "8.7 N");
  check("in range note", p.text("r_ts"), /within the usual 5–15 N range/);
  // same tension over a 200 mm span
  p.set("span", 200);
  check("110 Hz@150 -> 200 mm span", p.text("r_conv"), "82.5 Hz");
  p.set("span", 150);

  // CoreXY belt matching: relative tension matters more than the absolute value
  check("no second belt yet", p.text("r_match"), "—");
  p.set("freqb", 110);
  check("identical belts match", p.text("r_match"), "Matched");
  p.set("freqb", 111);
  check("1 Hz apart is fine", p.text("r_match"), "1 Hz apart");
  check("close enough wording", p.text("r_matchs"), /close enough/);
  p.set("freqb", 125);
  check("15 Hz apart flagged", p.text("r_match"), "15 Hz apart");
  check("skew warning", p.text("r_matchs"), /will skew prints/);
});

group("temp-tower-generator", () => {
  const p = load("temp-tower-generator");
  check("6 sections, 60 mm", p.text("r_summary"), /6 sections · 60 mm tall · 230 → 205 °C/);
  check("layer count", p.text("r_detail"), /300 layers/);
  p.pick("test_rdist");
  check("retraction mode relabels", p.text("r_summary"), /0\.2 → 1\.2 mm/);
  // --- cooling fan tower: M106 per section, and no blanket fan-on at layer 2
  p.pick("test_fan");
  check("fan defaults", p.text("r_summary"), /0 → 100 %/);
  p.doc.getElementById("preview").dispatchEvent({ type: "click" });
  check("fan test emits M106 steps", p.text("gpre"), /M106 S0/);

  // --- print speed tower: feedrate changes per section
  p.pick("test_speed");
  check("speed defaults", p.text("r_summary"), /40 → 140 mm\/s/);

  // --- pressure advance: firmware-specific command
  p.pick("test_pa");
  check("PA firmware picker shown", p.hidden("pabox"), false);
  check("PA defaults", p.text("r_summary"), /0 → 0\.05/);
  p.doc.getElementById("preview").dispatchEvent({ type: "click" });
  check("klipper PA command", p.text("gpre"), /SET_PRESSURE_ADVANCE ADVANCE=0/);
  p.set("pafw", "marlin");
  p.doc.getElementById("preview").dispatchEvent({ type: "click" });
  check("marlin PA command", p.text("gpre"), /M900 K0/);
  // the firmware picker is hidden again for other tests
  p.pick("test_temp");
  check("PA picker hidden for temp", p.hidden("pabox"), true);

  // a gap too wide for the bed must warn
  p.pick("test_temp").set("gap", 210);
  check("oversize footprint warns", p.hidden("warn"), false);
});

/* -------------------------------------------------------------- filament */

group("filament-remaining-calculator", () => {
  const p = load("filament-remaining-calculator");
  check("640 - 220 tare", p.text("r_g"), "420 g");
  check("length left", p.text("r_m"), "140.8 m");
  check("percent of a kilo", p.text("r_pct"), "42% of a 1 kg spool");
  // enough for the print?
  p.set("need", 300);
  check("enough filament", p.text("r_fit"), "Yes");
  p.set("need", 500);
  check("not enough", p.text("r_fit"), "No");
  check("shortfall stated", p.text("r_fits"), /short by 80 g/);
  // geometric method: annulus ratio, so packing factor and width cancel
  check("geometry needs an outer diameter", p.text("r_geo"), "—");
  p.set("od", 150);
  check("150 mm roll on a 95/200 spool", p.text("r_geo"), "435 g");
  check("shows fraction and gap to the scale", p.text("r_geos"), /44% of a full roll .* 15 g from the weighed figure/);
  // nonsense geometry must be caught, not silently produce a number
  p.set("od", 50);
  check("outer smaller than core", p.text("r_geo"), "check the numbers");
  p.set("od", "");

  // tare heavier than the spool is a user error, and must say so
  p.set("need", "").set("gross", 100);
  check("tare too heavy warns", p.hidden("warn"), false);
  check("never negative", p.text("r_g"), "0 g");
});

group("filament-length-weight-calculator", () => {
  const p = load("filament-length-weight-calculator");
  check("100 g PLA -> meters", p.text("r_m"), "33.53 m");
  check("100 g PLA -> volume", p.text("r_v"), "80.65 cm³");
  check("g per meter", p.text("r_gpm"), "2.983 g/m");
  p.set("known", "m").set("val", 100);
  check("100 m PLA -> grams", p.text("r_g"), "298.3 g");
  p.set("known", "v").set("val", 100);
  check("100 cm³ PLA -> grams", p.text("r_g"), "124 g");
  // weight goes with diameter squared, so tolerance matters more than it looks
  p.set("known", "g").set("val", 100);
  check("tolerance on 1.75 mm", p.text("r_tol"), "±2.3 %");
  check("tolerance explained", p.text("r_tols"), /nominal/);

  // a measured diameter overrides the nominal and changes the answer
  p.set("meas", 1.74);
  check("measured diameter used", p.text("r_tols"), /1\.74 mm \(measured\)/);
  check("measured changes length", p.text("r_m"), /33\.9\d m/);
  p.set("meas", "");
  check("back to nominal", p.text("r_m"), "33.53 m");

  // 2.85 mm is 2.65x the cross-section, and proportionally less tolerance-sensitive
  p.set("known", "g").set("val", 1000).set("dia", "2.85");
  check("1 kg of 2.85 mm PLA", p.text("r_m"), /126\.\d+ m/);
  check("thicker filament less sensitive", p.text("r_tol"), "±1.4 %");
});

group("3d-model-scale-calculator", () => {
  const p = load("3d-model-scale-calculator");
  check("75% scale dims", p.text("r_dims"), "90 × 60 × 112.5 mm");
  check("volume is cubic", p.text("r_vol"), "42.2 %");
  // scale to a target Z
  p.pick("mode_target").set("taxis", "z").set("tval", 100);
  check("scale to 100 mm tall", p.text("r_scale"), "66.67 %");
  // inch/mm mixup detection
  p.pick("mode_pct").set("pct", 2540);
  check("inch->mm factor flagged", p.text("r_scales"), /inches → mm fix/);
  // scaled height rarely lands on a layer boundary - 112.5 / 0.2 = 562.5
  p.pick("mode_pct").set("pct", 75).set("lh", 0.2);
  check("scaled height off a layer", p.text("r_q"), "+100 µm out");
  check("shows the layer count", p.text("r_qs"), /562\.5 layers/);
  p.set("pct", 100);
  check("150 mm at 0.2 is exact", p.text("r_q"), "Exact");
  check("layer count exact", p.text("r_qs"), /750 layers exactly/);

  // fit mode
  p.pick("mode_fit").set("printer", "220,220,250").set("margin", 5);
  check("fits after scaling down", p.text("r_fit"), /Yes/);

  // a part too wide square-on can still go corner to corner.
  // Must be out of fit mode, where the scale is chosen so it always fits.
  p.pick("mode_pct").set("pct", 100).set("x", 260).set("y", 60).set("z", 100);
  check("diagonal placement spotted", p.text("r_fit"), /rotated/);
  check("diagonal explained", p.text("r_fits"), /bed diagonal is 297 mm/);
});

group("print-time-estimator", () => {
  const p = load("print-time-estimator");
  check("time estimate", p.text("r_time"), "0h 46m");
  check("range given", p.text("r_range"), /likely 0h 3\dm – 1h 0\dm/);
  check("filament weight", p.text("r_g"), "23 g");
  // if a sliced file exists, read the slicer's real answer instead of estimating
  p.set("gcode", "; filament used [g] = 23.4\n; estimated printing time (normal mode) = 46m 12s\n");
  p.doc.getElementById("readgc").dispatchEvent({ type: "click" });
  check("reads the slicer's figures", p.text("gcstatus"), /Your slicer says 0h 46m and 23\.4 g/);
  check("tells you to trust it", p.text("gcstatus"), /use it instead of the estimate/);
  p.set("gcode", "not gcode at all");
  p.doc.getElementById("readgc").dispatchEvent({ type: "click" });
  check("junk handled", p.text("gcstatus"), /Couldn't find/);

  // halving layer height should roughly double the time
  const before = p.text("r_time");
  p.set("lh", 0.1);
  check("finer layers take longer", p.text("r_time") !== before, true);
});

/* ------------------------------------------------------- cross-cutting */

group("shared behaviour", () => {
  const p = load("filament-cost-calculator");
  // blank inputs must never produce NaN or Infinity in the output
  ["price", "spool", "used", "waste", "fail"].forEach(id => p.set(id, ""));
  ["r_cost", "r_adj", "r_perg", "r_perm"].forEach(id => {
    check(`blank inputs -> no NaN in #${id}`, /NaN|Infinity|undefined/.test(p.text(id)), false);
  });
  // negatives must not crash
  p.set("price", -5).set("spool", 1000).set("used", 50);
  check("negative price does not crash", /NaN|Infinity/.test(p.text("r_cost")), false);
});

/* ------------------------------------------------------------------ done */

console.log("");
if (failed) {
  console.log(`  ${failed} failing check(s):\n`);
  failures.forEach(f => console.log("    ✗ " + f + "\n"));
  console.log(`  ${passed} passed, ${failed} failed`);
  process.exit(1);
}
console.log(`  ${passed} checks passed across all calculators`);
