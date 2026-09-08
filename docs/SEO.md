# SEO: what's in place, and what's deliberately not

Audited against the live site on 2026-09-08. This file exists so the next person
(or the next you) doesn't re-litigate decisions that were already made on purpose.

## In place

| | |
|---|---|
| **One tool, one URL** | Each calculator is its own page targeting one query. Never a tabbed app. |
| **Titles** | All ≤ 60 characters, unique, primary keyword first. Longer titles truncate in results and lose the differentiating half. |
| **Descriptions** | All ≤ 160 characters, unique. `build.py` refuses to build if one is longer. |
| **Canonicals** | Absolute, self-referencing, verified matching on every page. |
| **Headings** | One `h1` per page, no level skips. Card grids sit under an `h2` for this reason. |
| **Structured data** | `SoftwareApplication`, `WebPage` (with `author`, `publisher`, `datePublished`, `dateModified`), `BreadcrumbList`, `FAQPage` on tools; `CollectionPage` + `ItemList` on categories; `WebSite` + `Organization` on the home page. |
| **Sitemap** | `lastmod` is derived from real content dates. Hub pages inherit the newest date of what they list, so a rebuild alone never changes it. |
| **Internal linking** | Hub and spoke, plus a related-tools block and contextual links in every article. Zero orphans, zero broken links, everything one click from the home page. |
| **Redirects** | `http → https`, `www → apex`, and `/slug → /slug/` all 301. |
| **Performance** | ~6 KB per page gzipped, one 24 KB font preloaded, no third-party CSS or JS beyond GA4. |
| **Indexing** | Google Search Console + Bing Webmaster, and IndexNow fires on every deploy. |

## Deliberately not done

**`HowTo` schema** — Google removed HowTo rich results in 2023. Adding it now
marks up content for a feature that no longer exists.

**`FAQPage` is kept, but expect no rich result.** Google deprecated FAQ rich
results in May 2026. The schema is still valid, costs nothing, and pages carrying
it appear more often in AI Overviews, so it stays — but nobody should expect
expanded listings from it.

**`AggregateRating` / `Review`** — we have no genuine reviews. Inventing them is
both a manual-action risk and dishonest.

**`llms.txt`** — the file is served, and it is close to useless. Studies of AI
crawler traffic find the overwhelming majority of `llms.txt` files are never
requested at all, and Google has said on the record it does not support the
format. It is ~1 KB, so it stays on the off-chance the situation changes, but do
not count it as doing anything. What actually gets you cited by AI search is the
same thing that ranks: clean HTML, clear factual statements, tables, and being
crawlable.

**`changefreq` and `priority` in the sitemap** — Google ignores both, and has
said so for years.

**Security headers (HSTS, CSP, X-Content-Type-Options)** — GitHub Pages does not
allow custom response headers. Not fixable without moving hosts, and not worth
moving hosts for.

**A web app manifest** — no ranking effect. Padding.

## The things that actually matter now

The technical side is done and is not the constraint. Rankings are limited by
domain age and backlinks, neither of which is a code change. In rough order of
value:

1. **Links from places the audience already trusts** — the calibration guides,
   subreddit wikis, `awesome-*` lists. One good link beats any amount of markup.
2. **Answering existing questions** on Stack Exchange and Reddit, where the
   thread itself already ranks.
3. **Search Console's query report**, monthly. The queries where you sit on page
   two or three are the cheapest wins available: editing an existing page beats
   writing a new one.

## Re-running the audit

There's no saved script — it was a one-off. If you want to repeat it, the checks
worth automating are already in `check.py` (tags, canonicals, links, JSON-LD
validity, heading count) and `tests/run.js` (calculator output). What those
don't cover, and what the manual pass added, was: trailing-slash redirect
behaviour, heading-level skips, `lastmod` honesty, and authorship fields.
