# LayerCalc

Free 3D printing calculators — cost, pricing, calibration and filament — at
**[layercalc.com](https://layercalc.com)**. Fifteen tools, each on its own page with the
formula, a worked example and an FAQ. Everything runs in the visitor's browser.

Nothing here needs a server, a database or a subscription. The only recurring cost is the
domain. Push to `main` and GitHub Actions builds and deploys it.

---

## How it runs

| What | When | Where |
|---|---|---|
| **Build + deploy** | every push to `main` | GitHub Actions → GitHub Pages (`.github/workflows/publish.yml`) |
| **Validation** | every build | `check.py` — fails the deploy on broken links, missing SEO tags, bad JSON-LD or JS syntax errors |
| **Tests** | every build | `node tests/run.js` — drives each calculator headlessly and checks its real output |
| **Indexing** | every deploy | `sitemap.xml` + IndexNow ping to Bing/DuckDuckGo/Yandex |
| **Ads / analytics** | when you switch them on | `MONETIZATION` block at the top of `build.py` — see `docs/ADS.md` |

Setup walkthrough (repo, domain, DNS, search consoles): **`docs/DEPLOY.md`**.
What's done for SEO and what's deliberately skipped: **`docs/SEO.md`**.

---

## Layout

| Path | What it is |
|---|---|
| `content/calculators/` | One file per calculator: a JSON header, the calculator HTML + script, `<!--ARTICLE-->`, then the article. **This is where the tools live.** |
| `content/pages/` | About, contact, privacy, terms, and the filament settings reference. Same JSON-header format. |
| `build.py` | Builds `dist/`. Site name, URL, categories and monetization settings are at the top. Standard library only. |
| `check.py` | Post-build validation. Must pass before anything deploys. |
| `templates/` | Page shells: `base.html` (head, header, footer), `tool.html`, `hub.html`, `page.html`. |
| `static/` | Stylesheet, shared calculator helpers (`app.js`), logo, share images (`og/`). |
| `public/` | Copied to the site root verbatim: `CNAME`, the IndexNow key, search-engine verification files. |
| `scripts/` | `indexnow.py` (run by the deploy), `make_og.py` (regenerates share images; needs Pillow). |
| `docs/` | Deployment walkthrough, ads setup, launch/SEO checklist. |

`dist/` is build output and isn't committed.

---

## Working on it

**Preview locally**

```bash
python build.py && python check.py && node tests/run.js && python -m http.server 8765 -d dist
```

then open <http://localhost:8765>.

**Edit a calculator** — open its file in `content/calculators/`, edit, build, check, commit, push.
The push deploys it.

**Add a calculator**

1. Copy an existing file in `content/calculators/` to `new-slug.html`. The file name becomes the URL.
2. Fill in the header: `title`, `page_title`, `description` (≤160 chars), `lede`, `short`, `category`
   (`cost`, `calibration` or `filament`), `order`, `updated`, `related` (slugs), `faq`.
3. Write the form. Give every input an `id`; call `LC.bind("f", calc)` at the end of the script and it
   recalculates on every keystroke and remembers the values. Helpers in `static/app.js`:
   `LC.num(id)`, `LC.val(id)`, `LC.out(id, text)`, `LC.fmt(x, decimals)`, `LC.money(x)`, `LC.hours(h)`,
   `LC.show(id, bool)`, `LC.currencyPicker(containerId)`, `LC.copyButton(btnId, fn)`, `LC.download(name, text)`,
   `LC.modePanels(radioName, attr)`, `LC.parseGcode(text)` (pulls grams/hours/layers out of a pasted
   slicer header — PrusaSlicer, Orca, Bambu and Cura formats).
4. Put `<!--ARTICLE-->` after the script, then the article HTML (formula, worked example, guidance).
5. Add assertions for it in `tests/run.js` — a couple of known-good input/output pairs and any edge case
   (zero, blank, absurd values). The tests drive the real built page, so they catch a broken formula
   that `check.py` cannot see.
6. `python scripts/make_og.py` to generate its share image, then build, check, test, commit, push.

**Tests** — `node tests/run.js` after a build. `tests/dom.js` is a small DOM shim (no dependencies) that
runs each page's real script; `tests/run.js` sets inputs and asserts on the rendered output text rather
than reimplementing any maths.

**Change the site name, domain or categories** — the `SITE` and `CATEGORIES` blocks at the top of
`build.py`, plus `public/CNAME` for the domain.

**Switch on ads or analytics** — `MONETIZATION` block in `build.py`. Every field is inert until
filled in. Steps in `docs/ADS.md`.

---

## License

[MIT](LICENSE). The code is free to reuse; the calculator explanations and article
text are the site's own content, so please don't republish those wholesale.
