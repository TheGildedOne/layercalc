#!/usr/bin/env python3
"""
LayerCalc - static site builder.

Reads content/calculators/*.html and content/pages/*.html (each with a JSON
metadata header) and emits dist/, a complete, deployable static site.

Standard library only. Run:  python build.py
"""

import html
import json
import re
import shutil
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
CALC_DIR = ROOT / "content" / "calculators"
PAGE_DIR = ROOT / "content" / "pages"
TEMPLATES = ROOT / "templates"
STATIC = ROOT / "static"
PUBLIC = ROOT / "public"    # copied to the site root verbatim (CNAME, verification files)
DIST = ROOT / "dist"

# ------------------------------------------------------------------ settings

SITE = {
    "name": "LayerCalc",
    "tagline": "Free 3D printing calculators",
    "description": (
        "Free 3D printing calculators: filament cost, print pricing, e-steps, flow rate, "
        "shrinkage, belt tension and test-tower G-code. No signup, runs in your browser."
    ),
    "url": "https://layercalc.com",
    "lang": "en",
    "locale": "en_US",
    "launched": "2026-09-07",
}

# Revenue plumbing. Everything here is inert until an ID is filled in, so the
# site ships clean and switches on one line at a time when you're ready.
# See docs/ADS.md for the exact steps.
MONETIZATION = {
    # Google AdSense publisher ID, e.g. "ca-pub-1234567890123456".
    # Setting this alone enables Auto ads on every page and writes ads.txt.
    "adsense_client": "",
    # Optional manual ad units. Leave blank to rely on Auto ads. Each value is
    # the numeric "data-ad-slot" from an ad unit you created in AdSense.
    "adsense_slots": {
        "after_calc": "",     # directly under the calculator, above the article
        "before_faq": "",     # between the article and the FAQ
        "hub": "",            # on the home page and category pages
    },
    # Google Analytics 4 measurement ID, e.g. "G-XXXXXXXXXX". Optional.
    "ga4_id": "G-38ZP28C97M",
    "contact_email": "hello@layercalc.com",
}

CATEGORIES = {
    "cost": {
        "slug": "cost-calculators",
        "nav": "Cost",
        "title": "3D Printing Cost Calculators",
        "h1": "3D printing cost & pricing calculators",
        "description": "Work out what a 3D print really costs and what to charge for it: filament cost per gram, full print quotes with marketplace fees, resin costs and electricity.",
        "intro": "Filament, resin, electricity, machine wear and your time — these calculators add it all up and, if you sell prints, tell you what to charge so the marketplace fees don't eat the margin.",
        "guide": "<h2>What a 3D print actually costs</h2>\n<p>Material is the number everyone reaches for and the smallest part of the answer. On a six-hour print the filament might be a dollar; the machine has aged six hours, drawn most of a kilowatt-hour, and needed you to slice it, watch the first layer, prise it off and clean it up. Any of those individually outweighs the plastic.</p>\n<p>A full cost breaks into five parts, and these calculators handle them in the order that matters:</p>\n<ol>\n<li><strong>Material</strong> — grams from the slicer times your cost per gram, plus an allowance for purge, waste and the prints that fail.</li>\n<li><strong>Machine time</strong> — the printer's price spread over its realistic working life, typically 2,000&ndash;5,000 hours, plus nozzles, belts, plates and hotends.</li>\n<li><strong>Electricity</strong> — small but real, and much larger for enclosed ABS printing than for PLA on an open bedslinger.</li>\n<li><strong>Labour</strong> — usually the biggest line on anything under a few hundred grams, and the one most often set to zero.</li>\n<li><strong>Failure allowance</strong> — if one print in ten fails, every good print carries an extra 11% of machine-side cost.</li>\n</ol>\n<h3>If you sell prints</h3>\n<p>Two things separate a price that works from one that quietly loses money. The first is charging for your time at a rate you would actually accept. The second is that marketplace fees come off the listed price, not added to it &mdash; so to keep a given amount you have to work backwards, dividing rather than adding. A 9.5% fee on a $12 target is not $13.14; it is $13.76 once the fixed listing and payment charges are in. The pricing calculator does that arithmetic, and its Etsy and eBay presets are editable because those schedules change.</p>\n<h3>Where to start</h3>\n<p>If you just want to know what a spool is costing you, start with the filament cost calculator. If you are quoting work for someone else, go straight to the pricing calculator &mdash; it contains the others.</p>",
    },
    "calibration": {
        "slug": "calibration-calculators",
        "nav": "Calibration",
        "title": "3D Printer Calibration Calculators",
        "h1": "3D printer calibration calculators",
        "description": "E-steps, flow rate, shrinkage compensation, magic layer heights, volumetric flow, belt tension and a test tower G-code generator. Free, in your browser.",
        "intro": "Dial in a printer in the right order: extruder steps, then flow, then dimensional accuracy, then speed. Each tool tells you exactly which number to type into your firmware or slicer.",
        "guide": "<h2>An order that works</h2>\n<p>There is no single agreed sequence &mdash; OrcaSlicer's own guide runs temperature before flow, and the reasoning cuts both ways. What is not in dispute is that each step assumes the one before it is already correct. Tuning flow before the extruder is delivering the right length of filament, for instance, just bakes the extruder error into a flow number that will be wrong again the moment you fix it. The order below is the one that converges.</p>\n<ol>\n<li><strong>Extruder steps</strong> &mdash; e-steps on Marlin, rotation_distance on Klipper. Done once per extruder, not per material. Confirms the printer pushes 100&nbsp;mm when you ask for 100&nbsp;mm.</li>\n<li><strong>Flow rate</strong> &mdash; the extrusion multiplier, tuned per material. Corrects for how the plastic actually spreads once it leaves the nozzle: filament diameter tolerance, melt temperature, and the slicer's assumptions.</li>\n<li><strong>Temperature and retraction</strong> &mdash; a test tower per filament. Do this after flow, or over-extrusion will look exactly like printing too hot.</li>\n<li><strong>Dimensional accuracy</strong> &mdash; shrinkage compensation and hole offsets, per material. Only meaningful once the right amount of plastic is coming out.</li>\n<li><strong>Speed</strong> &mdash; find the hotend's volumetric ceiling last, since it determines which of your speed settings are doing anything at all.</li>\n</ol>\n<h3>Mechanical checks sit outside that sequence</h3>\n<p>Belt tension and layer-height selection are not part of the extrusion chain, but they set a ceiling on what any amount of tuning can achieve. Loose belts produce ringing that looks like an acceleration problem; a layer height that lands between full motor steps can show faint banding on glossy walls that no flow adjustment will remove. Both are worth checking before you spend an evening chasing extrusion settings.</p>\n<h3>How much of this does a modern printer need?</h3>\n<p>Less than it used to. Bambu, Prusa and most Klipper machines ship with the extruder already calibrated and the mechanics square, so flow and temperature per filament is often the whole job. E-steps matter most on budget machines and on anything you have modified &mdash; a new extruder, motor or mainboard puts you back at step one.</p>",
    },
    "filament": {
        "slug": "filament-calculators",
        "nav": "Filament",
        "title": "Filament & Model Calculators",
        "h1": "Filament & model calculators",
        "description": "How much filament is left on a spool, length to weight conversion by material, model scaling and bed-fit checks, and a pre-slice print time estimator.",
        "intro": "The everyday questions: is there enough filament left, how many meters is 300 g, will this model fit the bed if I scale it, and roughly how long will it take.",
        "guide": '<h2>The everyday filament questions</h2>\n<p>These are the ones that come up mid-project, usually when you are about to start a print and want to know whether it will finish. None of them are difficult; they are just tedious enough that people guess instead, and guessing about whether 400&nbsp;g remains is how a twelve-hour print fails at hour eleven.</p>\n<h3>How much is left</h3>\n<p>Weight is the only reliable answer, because you cannot see how many winds are underneath the top layer. Weigh the spool, subtract what the empty spool weighs, and the remainder is filament. The awkward part is the empty weight: a "1&nbsp;kg" spool sits on a reel weighing anywhere from 12&nbsp;g for a cardboard refill core to 250&nbsp;g for a Bambu reusable spool, and that difference is worth a quarter of the print. When a spool does run out, weigh it and write the number down &mdash; after a few months you will have exact tares for every brand you buy.</p>\n<h3>Length, weight and volume</h3>\n<p>Slicers report all three and they are not interchangeable between materials. A metre of 1.75&nbsp;mm PLA weighs about 2.98&nbsp;g; the same metre of ABS weighs 2.50&nbsp;g, so a kilogram of ABS runs roughly 65&nbsp;m further. Filled filaments break the pattern harder: metal-filled PLA can be three times the density of plain PLA, so a "1&nbsp;kg" spool holds a fraction of the length you would expect.</p>\n<h3>Scaling and fitting the bed</h3>\n<p>The trap here is that volume scales with the <em>cube</em> of the linear scale. Doubling a model uses eight times the filament and roughly eight times the time; halving it uses an eighth. That is also why scaled parts stop fitting hardware &mdash; walls, holes and clearances shrink with everything else, and a 2&nbsp;mm wall at 50% is thinner than two extrusion lines.</p>\n<h3>Estimating before you slice</h3>\n<p>Useful mainly for quoting, when someone asks roughly what something will cost before they send you a file. Expect a pre-slice estimate to land within about 30% for ordinary parts, and further out for anything with many small islands, thin towers or heavy supports. Let the slicer give the final number.</p>',
    },
}

REFERENCE_NAV = [("Reference", "/filament-settings-reference/")]

# Line icons for the cards, keyed by slug (24x24 viewBox, stroked in CSS).
ICONS = {
    "filament-cost-calculator": '<circle cx="12" cy="12" r="9"/><path d="M12 7v10M9.5 9.5h3.5a1.75 1.75 0 0 1 0 3.5h-2a1.75 1.75 0 0 0 0 3.5H15"/>',
    "3d-print-pricing-calculator": '<path d="M20.5 12.5 12.5 20.5a1.5 1.5 0 0 1-2.1 0L3 13V3h10l7.5 7.5a1.5 1.5 0 0 1 0 2z"/><circle cx="7.5" cy="7.5" r="1.5"/>',
    "resin-print-cost-calculator": '<path d="M12 3s6.5 7 6.5 11.5a6.5 6.5 0 0 1-13 0C5.5 10 12 3 12 3z"/>',
    "3d-printer-electricity-cost-calculator": '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
    "e-steps-calculator": '<path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1"/><circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="18" r="2"/>',
    "flow-rate-calculator": '<path d="M4 16a8 8 0 0 1 16 0"/><path d="M12 16l4.5-5"/><circle cx="12" cy="16" r="1.5"/><path d="M2 20h20"/>',
    "shrinkage-compensation-calculator": '<path d="M4 20 20 4M4 20v-6M4 20h6M20 4v6M20 4h-6"/>',
    "layer-height-calculator": '<path d="m12 3 9 4.5-9 4.5-9-4.5z"/><path d="m3 12 9 4.5 9-4.5"/><path d="m3 16.5 9 4.5 9-4.5"/>',
    "max-volumetric-speed-calculator": '<path d="M3 12h4l3-8 4 16 3-8h4"/>',
    "belt-tension-calculator": '<path d="M2 12c2-7 4-7 6 0s4 7 6 0 4-7 6 0"/>',
    "temp-tower-generator": '<rect x="8" y="3" width="8" height="18" rx="1.5"/><path d="M8 8.5h8M8 13h8M8 17.5h8"/>',
    "filament-remaining-calculator": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3"/><path d="M12 3v6M12 15v6M3 12h6M15 12h6"/>',
    "filament-length-weight-calculator": '<rect x="3" y="8" width="18" height="8" rx="1.5"/><path d="M7 8v3M11 8v4M15 8v3M19 8v4"/>',
    "3d-model-scale-calculator": '<path d="M8 3H3v5M16 3h5v5M8 21H3v-5M16 21h5v-5"/><rect x="8.5" y="8.5" width="7" height="7" rx="1"/>',
    "print-time-estimator": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    "filament-settings-reference": '<path d="M4 4.5h5.5A2.5 2.5 0 0 1 12 7v13a2 2 0 0 0-2-2H4z"/><path d="M20 4.5h-5.5A2.5 2.5 0 0 0 12 7v13a2 2 0 0 1 2-2h6z"/>',
}
DEFAULT_ICON = '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 12h8M12 8v8"/>'


def icon_svg(slug: str) -> str:
    return (f'<span class="card-icon" aria-hidden="true"><svg viewBox="0 0 24 24">'
            f'{ICONS.get(slug, DEFAULT_ICON)}</svg></span>')

# ------------------------------------------------------------------ helpers

def esc(s: str) -> str:
    return html.escape(str(s), quote=True)


def strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s)


def render(template: str, ctx: dict) -> str:
    """Minimal {{key}} substitution. Values are inserted raw."""
    ctx = {"head_extra": analytics_head() + adsense_head(), **ctx}

    def sub(m):
        key = m.group(1).strip()
        if key not in ctx:
            raise KeyError(f"template key not provided: {key}")
        return str(ctx[key])
    return re.sub(r"\{\{([a-z0-9_]+)\}\}", sub, template)


def load_template(name: str) -> str:
    return (TEMPLATES / name).read_text(encoding="utf-8")


def parse_content(path: Path) -> tuple[dict, str]:
    """A file is a JSON object followed by HTML."""
    text = path.read_text(encoding="utf-8")
    meta, end = json.JSONDecoder().raw_decode(text)
    return meta, text[end:].strip("\n")


def human_date(iso: str) -> str:
    return datetime.strptime(iso, "%Y-%m-%d").strftime("%B %-d, %Y") if sys.platform != "win32" \
        else datetime.strptime(iso, "%Y-%m-%d").strftime("%B %d, %Y").replace(" 0", " ")


# ------------------------------------------------------------- monetization

def analytics_head() -> str:
    gid = MONETIZATION["ga4_id"]
    if not gid:
        return ""
    return (f'<script async src="https://www.googletagmanager.com/gtag/js?id={gid}"></script>\n'
            f"<script>window.dataLayer=window.dataLayer||[];function gtag(){{dataLayer.push(arguments);}}"
            f"gtag('js',new Date());gtag('config','{gid}');</script>\n")


def adsense_head() -> str:
    client = MONETIZATION["adsense_client"]
    if not client:
        return ""
    return (f'<script async src="https://pagead2.googlesyndication.com/pagead/js/'
            f'adsbygoogle.js?client={client}" crossorigin="anonymous"></script>\n')


def ad_unit(slot_key: str) -> str:
    """One ad placement. Renders nothing visible until AdSense is configured.

    With only a client ID set, Auto ads decide placement and this stays as a
    comment. With a slot ID too, a responsive manual unit is placed here.
    """
    client = MONETIZATION["adsense_client"]
    slot = MONETIZATION["adsense_slots"].get(slot_key, "")
    if not client or not slot:
        return f"  <!-- ad slot: {slot_key} -->"
    return (f'  <div class="ad-slot"><ins class="adsbygoogle" style="display:block" '
            f'data-ad-client="{client}" data-ad-slot="{slot}" data-ad-format="auto" '
            f'data-full-width-responsive="true"></ins>'
            f'<script>(adsbygoogle=window.adsbygoogle||[]).push({{}});</script></div>')


def ads_txt() -> str | None:
    client = MONETIZATION["adsense_client"]
    if not client:
        return None
    pub = client.replace("ca-", "")
    return f"google.com, {pub}, DIRECT, f08c47fec0942fa0\n"


# ------------------------------------------------------------------ loading

def load_calculators() -> list[dict]:
    tools = []
    for path in sorted(CALC_DIR.glob("*.html")):
        meta, body = parse_content(path)
        meta["slug"] = path.stem
        if "<!--ARTICLE-->" not in body:
            raise SystemExit(f"{path.name}: missing <!--ARTICLE--> separator")
        meta["calculator"], meta["article"] = body.split("<!--ARTICLE-->", 1)
        for key in ("title", "description", "lede", "short", "category", "updated", "faq"):
            if key not in meta:
                raise SystemExit(f"{path.name}: missing '{key}' in header")
        if meta["category"] not in CATEGORIES:
            raise SystemExit(f"{path.name}: unknown category {meta['category']}")
        if len(meta["description"]) > 160:
            raise SystemExit(f"{path.name}: description is {len(meta['description'])} chars (max 160)")
        meta.setdefault("order", 50)
        tools.append(meta)
    tools.sort(key=lambda t: (t["order"], t["title"]))
    return tools


def load_pages() -> list[dict]:
    pages = []
    for path in sorted(PAGE_DIR.glob("*.html")):
        meta, body = parse_content(path)
        meta["slug"] = path.stem
        meta["body"] = body
        pages.append(meta)
    return pages


# ---------------------------------------------------------------- rendering

def nav_html(current: str = "") -> str:
    items = [(c["nav"], f"/{c['slug']}/") for c in CATEGORIES.values()] + REFERENCE_NAV
    out = []
    for label, href in items:
        cur = ' aria-current="page"' if href == current else ""
        out.append(f'<a href="{href}"{cur}>{label}</a>')
    return "".join(out)


def footer_nav_html(tools: list[dict]) -> str:
    return "".join(f'<a href="/{t["slug"]}/">{esc(t["title"])}</a>' for t in tools)


def card(tool: dict) -> str:
    return (f'<a class="card" href="/{tool["slug"]}/">{icon_svg(tool["slug"])}<h3>{esc(tool["title"])}</h3>'
            f'<p>{esc(tool["short"])}</p></a>')


def og_image_for(slug: str) -> str:
    candidate = STATIC / "og" / f"{slug}.png"
    name = slug if candidate.exists() else "default"
    return f'{SITE["url"]}/static/og/{name}.png'


def page_shell(base: str, *, content: str, title: str, page_title: str, description: str,
               canonical_path: str, jsonld: dict, tools: list[dict], nav_current: str = "",
               og_image: str | None = None) -> str:
    return render(base, {
        "lang": SITE["lang"], "locale": SITE["locale"], "site_name": SITE["name"],
        "tagline": SITE["tagline"], "page_title": esc(page_title), "og_title": esc(title),
        "description": esc(description), "canonical": SITE["url"] + canonical_path,
        "og_image": og_image or og_image_for("default"),
        "jsonld": json.dumps(jsonld, ensure_ascii=False, indent=1),
        "nav": nav_html(nav_current), "footer_nav": footer_nav_html(tools),
        "content": content, "year": date.today().year,
    })


def faq_html(faq: list[dict]) -> str:
    if not faq:
        return ""
    parts = ['  <section class="faq" aria-labelledby="faq-h">', '    <h2 id="faq-h">Frequently asked questions</h2>']
    for item in faq:
        parts.append(f'    <h3>{esc(item["q"])}</h3>\n    <p>{item["a"]}</p>')
    parts.append("  </section>")
    return "\n".join(parts)


def tool_jsonld(tool: dict, canonical: str, cat: dict) -> dict:
    graph = [
        {
            "@type": "SoftwareApplication",
            "name": tool["title"],
            "url": canonical,
            "description": tool["description"],
            "applicationCategory": "UtilitiesApplication",
            "operatingSystem": "Any (web browser)",
            "browserRequirements": "Requires JavaScript",
            "isAccessibleForFree": True,
            "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            "publisher": {"@type": "Organization", "name": SITE["name"], "url": SITE["url"]},
        },
        {
            "@type": "WebPage",
            "name": tool["title"],
            "url": canonical,
            "datePublished": tool.get("published", SITE["launched"]),
            "dateModified": tool["updated"],
            "author": {"@type": "Organization", "name": SITE["name"], "url": SITE["url"] + "/about/"},
            "publisher": {"@type": "Organization", "name": SITE["name"], "url": SITE["url"]},
            "isPartOf": {"@type": "WebSite", "name": SITE["name"], "url": SITE["url"]},
        },
        {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE["url"] + "/"},
                {"@type": "ListItem", "position": 2, "name": cat["title"], "item": f'{SITE["url"]}/{cat["slug"]}/'},
                {"@type": "ListItem", "position": 3, "name": tool["title"], "item": canonical},
            ],
        },
    ]
    if tool["faq"]:
        graph.append({
            "@type": "FAQPage",
            "mainEntity": [
                {"@type": "Question", "name": f["q"],
                 "acceptedAnswer": {"@type": "Answer", "text": strip_tags(f["a"])}}
                for f in tool["faq"]
            ],
        })
    return {"@context": "https://schema.org", "@graph": graph}


def build_tool(tool: dict, tools: list[dict], base: str, tpl: str) -> str:
    cat = CATEGORIES[tool["category"]]
    by_slug = {t["slug"]: t for t in tools}
    related = [by_slug[s] for s in tool.get("related", []) if s in by_slug]
    # top up with siblings from the same category so the block is never thin
    for t in tools:
        if len(related) >= 4:
            break
        if t is not tool and t not in related and t["category"] == tool["category"]:
            related.append(t)
    canonical_path = f'/{tool["slug"]}/'
    content = render(tpl, {
        "cat_slug": cat["slug"], "cat_title": cat["title"], "title": esc(tool["title"]),
        "lede": tool["lede"], "calculator": tool["calculator"], "article": tool["article"],
        "ad_after_calc": ad_unit("after_calc"), "ad_before_faq": ad_unit("before_faq"),
        "faq": faq_html(tool["faq"]), "updated_human": human_date(tool["updated"]),
        "related": "".join(card(t) for t in related),
    })
    return page_shell(base, content=content, title=tool["title"],
                      page_title=tool.get("page_title") or f'{tool["title"]} – {SITE["name"]}',
                      description=tool["description"], canonical_path=canonical_path,
                      jsonld=tool_jsonld(tool, SITE["url"] + canonical_path, cat), tools=tools,
                      nav_current=f'/{cat["slug"]}/', og_image=og_image_for(tool["slug"]))


def build_home(tools: list[dict], base: str, hub: str) -> str:
    parts = ['<div class="home">', '<section class="hero">',
             '  <p class="eyebrow">Free · No signup · Runs in your browser</p>',
             '  <h1>3D printing calculators that give you <em>the exact number</em> to type in</h1>',
             '  <p>Filament cost, print quotes, e-steps, flow rate, shrinkage, belt tension, test-tower G-code and more — '
             'each with the formula and a worked example, so you can check it rather than trust it.</p>',
             '  <div class="hero-search"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>'
             '<label class="visually-hidden" for="toolsearch">Search calculators</label>'
             f'<input type="search" id="toolsearch" placeholder="Search {len(tools)} calculators — e-steps, Etsy fees, belt tension…" autocomplete="off"></div>',
             f'  <div class="hero-stats"><span><b>{len(tools)}</b> calculators</span><span><b>0</b> accounts or paywalls</span>'
             '<span><b>100%</b> in your browser</span></div>',
             '</section>']
    for key, cat in CATEGORIES.items():
        parts.append(f'<section class="section" data-section="{key}">')
        parts.append(f'<div class="section-head"><h2>{esc(cat["h1"])}</h2><a href="/{cat["slug"]}/">All {cat["nav"].lower()} tools &rarr;</a></div>')
        parts.append(f'<p>{esc(cat["intro"])}</p>')
        parts.append('<div class="cards">' + "".join(card(t) for t in tools if t["category"] == key) + "</div>")
        parts.append('</section>')
        if key == "cost":
            parts.append(ad_unit("hub"))
    parts.append('<section class="section" data-section="reference"><div class="section-head"><h2>Reference</h2></div>')
    parts.append(f'<div class="cards"><a class="card" href="/filament-settings-reference/">{icon_svg("filament-settings-reference")}'
                 '<h3>Filament settings & drying reference</h3>'
                 '<p>Nozzle and bed temperatures, fan, enclosure, drying time, density and shrinkage for every common material, in one table.</p></a></div></section>')
    parts.append('<p class="no-results" id="no-results" hidden>Nothing matches that. Try a material, a setting name, or what you\'re trying to work out.</p>')
    parts.append('<div class="why">'
                 '<div><h3>Built for one niche</h3><p>Every calculator here is for 3D printing. The defaults, presets and units are the ones you actually use.</p></div>'
                 '<div><h3>Shows the working</h3><p>Each page explains the formula and walks through a real example, so you can check the result rather than trust it.</p></div>'
                 '<div><h3>Private by design</h3><p>Everything runs in your browser. Your inputs are remembered on your device only.</p></div>'
                 '<div><h3>Free, no signup</h3><p>No accounts, no email gates, no watermarks, no limits.</p></div>'
                 '</div>')
    parts.append('<script>(function(){var q=document.getElementById("toolsearch"),cards=document.querySelectorAll(".card"),'
                 'secs=document.querySelectorAll(".section"),none=document.getElementById("no-results");'
                 'q.addEventListener("input",function(){var t=q.value.trim().toLowerCase(),any=false;'
                 'for(var i=0;i<cards.length;i++){var hit=!t||cards[i].textContent.toLowerCase().indexOf(t)>=0;cards[i].hidden=!hit;any=any||hit;}'
                 'for(var j=0;j<secs.length;j++){secs[j].hidden=!!t&&!secs[j].querySelector(".card:not([hidden])");}'
                 'none.hidden=any;});})();</script>')
    parts.append('<section class="home-faq"><h2>Common questions</h2>'
                 '<h3>Which calculator should I start with?</h3>'
                 '<p>If you sell prints: the <a href="/3d-print-pricing-calculator/">pricing calculator</a>. If prints look wrong: '
                 '<a href="/e-steps-calculator/">e-steps</a>, then <a href="/flow-rate-calculator/">flow rate</a>, then '
                 '<a href="/shrinkage-compensation-calculator/">shrinkage</a>, in that order.</p>'
                 '<h3>Are the results accurate?</h3>'
                 '<p>The math is exact; the inputs are the limit. Where a value is an estimate (spool tares, hotend flow limits, print time) the page says so and tells you how to measure your own.</p>'
                 '<h3>Do you store what I enter?</h3>'
                 '<p>Only in your own browser, so the form is filled in when you come back. Nothing is sent to a server.</p>'
                 '</section>')
    parts.append('</div>')
    content = render(hub, {"content": "\n".join(parts)})
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebSite", "name": SITE["name"], "url": SITE["url"] + "/", "description": SITE["description"]},
        {"@type": "Organization", "name": SITE["name"], "url": SITE["url"] + "/", "logo": SITE["url"] + "/static/apple-touch-icon.png"},
        {"@type": "ItemList", "name": "3D printing calculators",
         "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": t["title"], "url": f'{SITE["url"]}/{t["slug"]}/'}
                             for i, t in enumerate(tools)]},
    ]}
    return page_shell(base, content=content, title=f'{SITE["name"]} – Free 3D Printing Calculators',
                      page_title=f'{SITE["name"]} – Free 3D Printing Calculators',
                      description=SITE["description"], canonical_path="/", jsonld=jsonld, tools=tools)


def build_category(key: str, tools: list[dict], base: str, hub: str) -> str:
    cat = CATEGORIES[key]
    mine = [t for t in tools if t["category"] == key]
    parts = [f'<nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Home</a> &rsaquo; <span>{esc(cat["title"])}</span></nav>',
             '<section class="hero">', f'  <h1>{esc(cat["h1"])}</h1>', f'  <p>{esc(cat["intro"])}</p>', '</section>',
             '<h2>Choose a calculator</h2>',
             '<div class="cards">' + "".join(card(t) for t in mine) + "</div>", ad_unit("hub")]
    parts.append('<section class="home-faq">')
    parts.append('<h2>What each one does</h2>')
    for t in mine:
        parts.append(f'<h3><a href="/{t["slug"]}/">{esc(t["title"])}</a></h3><p>{t["lede"]}</p>')
    parts.append(cat["guide"])
    parts.append('</section>')
    content = render(hub, {"content": "\n".join(parts)})
    path = f'/{cat["slug"]}/'
    jsonld = {"@context": "https://schema.org", "@graph": [
        {"@type": "CollectionPage", "name": cat["title"], "url": SITE["url"] + path, "description": cat["description"],
         "isPartOf": {"@type": "WebSite", "name": SITE["name"], "url": SITE["url"]}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": SITE["url"] + "/"},
            {"@type": "ListItem", "position": 2, "name": cat["title"], "item": SITE["url"] + path}]},
        {"@type": "ItemList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": t["title"], "url": f'{SITE["url"]}/{t["slug"]}/'}
                                                  for i, t in enumerate(mine)]},
    ]}
    return page_shell(base, content=content, title=cat["title"], page_title=f'{cat["title"]} – {SITE["name"]}',
                      description=cat["description"], canonical_path=path, jsonld=jsonld, tools=tools, nav_current=path)


def build_page(page: dict, tools: list[dict], base: str, tpl: str) -> str:
    body = page["body"]
    # The privacy page describes ads only when ads are actually on.
    body = body.replace("{{ads_paragraph}}", privacy_ads_paragraph())
    body = body.replace("{{analytics_paragraph}}", privacy_analytics_paragraph())
    body = body.replace("{{ads_note}}", "is supported by unobtrusive advertising, which is the only way it's funded."
                        if MONETIZATION["adsense_client"] else
                        "is free; if it ever carries advertising, the privacy page will say so the day it starts.")
    body = body.replace("{{contact_email}}", MONETIZATION["contact_email"])
    body = body.replace("{{site_url}}", SITE["url"])
    content = render(tpl, {"title": esc(page["title"]), "body": body})
    path = f'/{page["slug"]}/'
    jsonld = {"@context": "https://schema.org", "@type": "WebPage", "name": page["title"], "url": SITE["url"] + path,
              "description": page["description"],
              "datePublished": page.get("published", SITE["launched"]),
              "dateModified": page.get("updated", SITE["launched"]),
              "author": {"@type": "Organization", "name": SITE["name"], "url": SITE["url"] + "/about/"},
              "publisher": {"@type": "Organization", "name": SITE["name"], "url": SITE["url"]},
              "isPartOf": {"@type": "WebSite", "name": SITE["name"], "url": SITE["url"]}}
    nav_current = path if page["slug"] == "filament-settings-reference" else ""
    return page_shell(base, content=content, title=page["title"], page_title=f'{page["title"]} – {SITE["name"]}',
                      description=page["description"], canonical_path=path, jsonld=jsonld, tools=tools,
                      nav_current=nav_current)


def privacy_ads_paragraph() -> str:
    if MONETIZATION["adsense_client"]:
        return ("<p>This site shows advertising served by Google AdSense. Google and its partners use cookies and similar "
                "technologies to serve ads based on your prior visits to this and other websites, and to measure them. "
                "You can opt out of personalized advertising at <a href=\"https://www.google.com/settings/ads\" rel=\"noopener\" "
                "target=\"_blank\">Google Ads Settings</a>, and read how Google uses data at "
                "<a href=\"https://policies.google.com/technologies/partner-sites\" rel=\"noopener\" target=\"_blank\">"
                "policies.google.com/technologies/partner-sites</a>. Visitors in regions that require it are shown a consent "
                "prompt before any advertising cookies are set.</p>")
    return "<p>This site does not currently show advertising and sets no advertising cookies. If that changes, this page will say so.</p>"


def privacy_analytics_paragraph() -> str:
    if MONETIZATION["ga4_id"]:
        return ("<p>We use Google Analytics to understand which pages are used. It sets cookies and records anonymized usage "
                "data (pages viewed, approximate location, device type). You can block it with any content blocker or the "
                "<a href=\"https://tools.google.com/dlpage/gaoptout\" rel=\"noopener\" target=\"_blank\">Google Analytics opt-out</a>.</p>")
    return "<p>We do not run analytics scripts. The hosting provider keeps standard, anonymized server logs.</p>"


def not_found(tools: list[dict], base: str, hub: str) -> str:
    content = render(hub, {"content":
        '<section class="hero"><h1>That page doesn\'t exist</h1><p>The address may have a typo, or the tool moved. '
        'Everything on the site is listed below.</p></section>'
        '<h2>Every calculator</h2>'
        '<div class="cards">' + "".join(card(t) for t in tools) + "</div>"})
    return page_shell(base, content=content, title="Page not found", page_title=f'Page not found – {SITE["name"]}',
                      description="The page you asked for could not be found. Every LayerCalc calculator is listed here.",
                      canonical_path="/404.html", jsonld={"@context": "https://schema.org", "@type": "WebPage", "name": "Page not found"},
                      tools=tools).replace('<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">',
                                           '<meta name="robots" content="noindex">')


# ----------------------------------------------------------------- outputs

def sitemap(urls: list[tuple[str, str]]) -> str:
    items = "".join(f"  <url><loc>{esc(loc)}</loc><lastmod>{mod}</lastmod></url>\n" for loc, mod in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{items}</urlset>\n'


def robots() -> str:
    return f"User-agent: *\nAllow: /\n\nSitemap: {SITE['url']}/sitemap.xml\n"


def llms_txt(tools: list[dict]) -> str:
    lines = [f"# {SITE['name']}", "", f"> {SITE['description']}", "",
             "All calculators are free, need no account, and run entirely in the browser. "
             "Each page states its formula and a worked example.", "", "## Calculators", ""]
    for t in tools:
        lines.append(f"- [{t['title']}]({SITE['url']}/{t['slug']}/): {t['short']}")
    lines += ["", "## Reference", "",
              f"- [Filament settings & drying reference]({SITE['url']}/filament-settings-reference/): temperatures, fan, enclosure, drying, density and shrinkage by material"]
    return "\n".join(lines) + "\n"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    tools = load_calculators()
    pages = load_pages()
    base, tool_tpl, hub, page_tpl = (load_template(n) for n in ("base.html", "tool.html", "hub.html", "page.html"))

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    shutil.copytree(STATIC, DIST / "static")
    if PUBLIC.exists():
        for f in PUBLIC.iterdir():
            if f.is_file():
                shutil.copy(f, DIST / f.name)

    today = date.today().isoformat()
    # lastmod has to mean "this page changed", not "the site was rebuilt". A date
    # that moves on every deploy teaches crawlers to ignore the field, so hubs
    # inherit the newest date of the content they actually list.
    all_dates = [t["updated"] for t in tools] + [p.get("updated", today) for p in pages]
    newest = max(all_dates) if all_dates else today
    urls = [(SITE["url"] + "/", newest)]

    write(DIST / "index.html", build_home(tools, base, hub))
    for key, cat in CATEGORIES.items():
        write(DIST / cat["slug"] / "index.html", build_category(key, tools, base, hub))
        cat_dates = [t["updated"] for t in tools if t["category"] == key]
        urls.append((f'{SITE["url"]}/{cat["slug"]}/', max(cat_dates) if cat_dates else newest))
    for tool in tools:
        write(DIST / tool["slug"] / "index.html", build_tool(tool, tools, base, tool_tpl))
        urls.append((f'{SITE["url"]}/{tool["slug"]}/', tool["updated"]))
    for page in pages:
        write(DIST / page["slug"] / "index.html", build_page(page, tools, base, page_tpl))
        urls.append((f'{SITE["url"]}/{page["slug"]}/', page.get("updated", today)))
    write(DIST / "404.html", not_found(tools, base, hub))
    write(DIST / "sitemap.xml", sitemap(urls))
    write(DIST / "robots.txt", robots())
    write(DIST / "llms.txt", llms_txt(tools))
    write(DIST / ".nojekyll", "")
    if (txt := ads_txt()):
        write(DIST / "ads.txt", txt)

    print(f"built {len(tools)} calculators, {len(CATEGORIES)} category pages, {len(pages)} pages -> dist/")


if __name__ == "__main__":
    main()
