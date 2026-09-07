#!/usr/bin/env python3
"""Post-build validation: required SEO tags, JSON-LD, internal links, leftovers.

Fails the build (exit 1) on any error so a broken page never deploys.
Run after build.py:  python check.py
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

DIST = Path(__file__).parent / "dist"
errors, checked = [], 0

GENERATED_AT_ROOT = {"index.html", "404.html"}
pages = [p for p in sorted(DIST.rglob("*.html"))
         if p.parent != DIST or p.name in GENERATED_AT_ROOT]

for page in pages:
    rel = page.relative_to(DIST).as_posix()
    html = page.read_text(encoding="utf-8")

    for label, pattern in [
        ("<title>", r"<title>[^<]{10,}</title>"),
        ("meta description", r'<meta name="description" content="[^"]{20,}"'),
        ("canonical", r'<link rel="canonical" href="https://[^"]+"'),
        ("og:title", r'<meta property="og:title"'),
        ("og:image", r'<meta property="og:image" content="https://[^"]+\.png"'),
        ("h1", r"<h1[^>]*>"),
    ]:
        if not re.search(pattern, html):
            errors.append(f"{rel}: missing {label}")
        checked += 1

    if len(re.findall(r"<h1[^>]*>", html)) != 1:
        errors.append(f"{rel}: expected exactly one <h1>")

    m = re.search(r'<meta name="description" content="([^"]*)"', html)
    if m and len(m.group(1)) > 165:
        errors.append(f"{rel}: meta description is {len(m.group(1))} chars")

    if "{{" in html:
        errors.append(f"{rel}: unrendered template tag")

    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL):
        checked += 1
        try:
            json.loads(block)
        except json.JSONDecodeError as e:
            errors.append(f"{rel}: invalid JSON-LD ({e})")

    # every internal link resolves to a built file
    for href in re.findall(r'href="(/[^"#?]*)"', html):
        checked += 1
        target = DIST / href.lstrip("/")
        if href.endswith("/"):
            target = target / "index.html"
        if not target.exists():
            errors.append(f"{rel}: broken internal link {href}")
    for src in re.findall(r'src="(/[^"#?]*)"', html):
        checked += 1
        if not (DIST / src.lstrip("/")).exists():
            errors.append(f"{rel}: missing asset {src}")

    # tool pages must actually contain a calculator
    if page.parent != DIST and page.parent.name not in {"about", "contact", "privacy", "terms",
                                                          "filament-settings-reference"} \
            and not page.parent.name.endswith("-calculators"):
        if "<form" not in html or "LC.bind(" not in html:
            errors.append(f"{rel}: tool page has no bound calculator form")

# JavaScript syntax check for every inline script, when node is available.
node = shutil.which("node")
if node:
    for page in pages:
        rel = page.relative_to(DIST).as_posix()
        html = page.read_text(encoding="utf-8")
        for i, script in enumerate(re.findall(r"<script>(.*?)</script>", html, re.DOTALL)):
            checked += 1
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as tmp:
                tmp.write(script)
            result = subprocess.run([node, "--check", tmp.name], capture_output=True, text=True)
            Path(tmp.name).unlink(missing_ok=True)
            if result.returncode != 0:
                errors.append(f"{rel}: inline script #{i + 1} has a syntax error:\n{result.stderr.strip()}")
    js = DIST / "static" / "app.js"
    result = subprocess.run([node, "--check", str(js)], capture_output=True, text=True)
    if result.returncode != 0:
        errors.append(f"static/app.js: syntax error:\n{result.stderr.strip()}")
else:
    print("  (node not found - skipping JavaScript syntax check)")

for required in ("sitemap.xml", "robots.txt", "404.html", "llms.txt", "CNAME"):
    checked += 1
    if not (DIST / required).exists():
        errors.append(f"missing {required}")

if errors:
    print(f"\n{len(errors)} problem(s):")
    for e in errors:
        print("  -", e)
    sys.exit(1)
print(f"  {len(pages)} pages, {checked} checks, no problems")
