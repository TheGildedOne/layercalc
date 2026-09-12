#!/usr/bin/env python3
"""Ad, consent and ads.txt plumbing tests.

Ads are switched off on the live site, so check.py and tests/run.js never
exercise that code. This builds the whole site into a temporary directory with
dummy AdSense and Analytics IDs, in four combinations, and checks what would
actually ship the day ads are switched on. The real dist/ is never touched.

Run:  python tests/test_ads.py
"""
import contextlib
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import build  # noqa: E402

CLIENT = "ca-pub-1234567890123456"
SLOTS = {"after_calc": "1111111111", "before_faq": "2222222222", "hub": "3333333333"}
GA = "G-TEST123456"
ORIGINAL = dict(build.MONETIZATION)
ORIGINAL_DIST = build.DIST

TOOL = "filament-cost-calculator/index.html"
PAGES = ["index.html", TOOL, "cost-calculators/index.html", "privacy/index.html", "404.html"]

passed = 0
failures = []


def check(name, cond, detail=""):
    global passed
    if cond:
        passed += 1
    else:
        failures.append(name + (f"\n      {detail}" if detail else ""))


def build_with(client="", slots=None, ga=""):
    tmp = Path(tempfile.mkdtemp(prefix="layercalc-ads-"))
    build.DIST = tmp / "dist"
    build.MONETIZATION = {**ORIGINAL, "adsense_client": client, "ga4_id": ga,
                          "adsense_slots": dict(slots or {k: "" for k in SLOTS})}
    with contextlib.redirect_stdout(io.StringIO()):
        build.main()
    return build.DIST, tmp


def read(d, rel):
    return (d / rel).read_text(encoding="utf-8")


def head(html):
    return html.split("</head>")[0]


try:
    # 1. Everything off: no Google code of any kind ships.
    d, tmp = build_with()
    for page in PAGES:
        html = read(d, page)
        check(f"off: no consent script in {page}", "gtag('consent'" not in html)
        check(f"off: no analytics in {page}", "googletagmanager" not in html)
        check(f"off: no AdSense in {page}", "adsbygoogle" not in html)
    check("off: no ads.txt", not (d / "ads.txt").exists())
    check("off: privacy says no ads", "does not currently show advertising" in read(d, "privacy/index.html"))
    check("off: privacy says no analytics", "do not run analytics" in read(d, "privacy/index.html"))
    check("off: slots are comments only", "<!-- ad slot: after_calc -->" in read(d, TOOL))
    shutil.rmtree(tmp)

    # 2. Analytics only - today's live configuration.
    d, tmp = build_with(ga=GA)
    h = head(read(d, TOOL))
    check("ga: consent default present", "gtag('consent','default'" in h)
    check("ga: consent default comes before gtag.js",
          0 <= h.find("gtag('consent'") < h.find("googletagmanager.com/gtag/js"))
    check("ga: config present", f"gtag('config','{GA}')" in h)
    check("ga: gtag defined exactly once", h.count("function gtag(") == 1, f"count={h.count('function gtag(')}")
    check("ga: no AdSense", "adsbygoogle" not in read(d, TOOL))
    check("ga: no ads.txt", not (d / "ads.txt").exists())
    m = re.search(r"region:(\[[^\]]*\])", h)
    regions = json.loads(m.group(1)) if m else []
    for cc in ["DE", "FR", "IE", "GB", "CH", "NO", "IS", "LI"]:
        check(f"ga: {cc} defaults to denied", cc in regions)
    check("ga: US is not defaulted to denied", "US" not in regions)
    check("ga: 32 regions (EU 27 + IS, LI, NO + GB + CH)", len(regions) == 32, f"got {len(regions)}")
    check("ga: global default is granted", "analytics_storage:'granted'" in h)
    check("ga: denied default waits for the banner", "wait_for_update:500" in h)
    check("ga: privacy says EEA analytics is off by default", "off by default" in read(d, "privacy/index.html"))
    shutil.rmtree(tmp)

    # 3. AdSense publisher ID, no manual slots: Auto ads.
    d, tmp = build_with(client=CLIENT, ga=GA)
    for page in PAGES:
        h = head(read(d, page))
        check(f"auto: AdSense script in {page}", f"adsbygoogle.js?client={CLIENT}" in h)
        check(f"auto: consent default before AdSense in {page}",
              0 <= h.find("gtag('consent'") < h.find("adsbygoogle.js"))
    txt = (d / "ads.txt").read_text(encoding="utf-8") if (d / "ads.txt").exists() else ""
    check("auto: ads.txt has Google's line", txt == "google.com, pub-1234567890123456, DIRECT, f08c47fec0942fa0\n", repr(txt))
    check("auto: no manual units without slot IDs", '<ins class="adsbygoogle"' not in read(d, TOOL))
    privacy = read(d, "privacy/index.html")
    check("auto: privacy names AdSense", "Google AdSense" in privacy)
    check("auto: privacy describes the certified consent tool", "Google-certified consent tool" in privacy)
    check("auto: about page mentions advertising", "supported by unobtrusive advertising" in read(d, "about/index.html"))
    shutil.rmtree(tmp)

    # 4. Publisher ID plus manual slots.
    d, tmp = build_with(client=CLIENT, slots=SLOTS, ga=GA)
    t = read(d, TOOL)
    check("manual: after_calc unit", 'data-ad-slot="1111111111"' in t)
    check("manual: before_faq unit", 'data-ad-slot="2222222222"' in t)
    check("manual: hub unit on the home page", 'data-ad-slot="3333333333"' in read(d, "index.html"))
    check("manual: hub unit on category pages", 'data-ad-slot="3333333333"' in read(d, "cost-calculators/index.html"))
    check("manual: both tool-page units are labelled",
          t.count('<span class="ad-label">Advertisement</span>') == 2)
    calc, after, article = t.find('id="calc"'), t.find("ad-after_calc"), t.find('class="article"')
    check("manual: after_calc sits between calculator and article", 0 <= calc < after < article)
    check("manual: nothing ad-related inside the calculator", "adsbygoogle" not in t[calc:after])
    check("manual: before_faq sits before the FAQ", 0 <= t.find("ad-before_faq") < t.find('id="faq-h"'))

    node = shutil.which("node")
    if node:
        for i, script in enumerate(re.findall(r"<script>(.*?)</script>", t, re.S)):
            f = tmp / f"inline{i}.js"
            f.write_text(script, encoding="utf-8")
            r = subprocess.run([node, "--check", str(f)], capture_output=True, text=True)
            check(f"manual: inline script #{i + 1} parses", r.returncode == 0, r.stderr.strip()[:300])

    css = read(d, "static/style.css")
    check("css: ad slots reserve height (no layout shift)", re.search(r"\.ad-slot\s*\{[^}]*min-height", css) is not None)
    check("css: unfilled units collapse", 'data-ad-status="unfilled"' in css)
    check("css: extra room below the calculator", ".ad-after_calc" in css)
    shutil.rmtree(tmp)
finally:
    build.MONETIZATION = ORIGINAL
    build.DIST = ORIGINAL_DIST

if failures:
    print(f"\n  {len(failures)} failing check(s):\n")
    for f in failures:
        print("    x " + f + "\n")
    print(f"  {passed} passed, {len(failures)} failed")
    sys.exit(1)
print(f"  {passed} ad and consent plumbing checks passed")
