# Deploying LayerCalc

Same setup as Veiled Antiquity: a public GitHub repo, GitHub Pages served from a GitHub Actions
workflow, and a custom domain. One difference — Veiled Antiquity lives in the special
`TheGildedOne.github.io` repo, which a GitHub account only gets one of. This site goes in an
ordinary repo (`layercalc`), and GitHub Pages works the same way for it.

Total cost after this: the domain, about $10/year. Nothing else, ever.

---

## 1. Buy the domain

**layercalc.com** was available when this was written (checked against the .com registry).
Any registrar works; two good ones:

- **Cloudflare Registrar** (dash.cloudflare.com → Domain Registration) — sells at wholesale
  with no renewal markup, about $10.50/yr for .com. Requires a free Cloudflare account. DNS
  is then managed in Cloudflare, which is convenient in step 5.
- **Namecheap / Porkbun** — a dollar or two more; DNS managed on their site.

Turn on **auto-renew** and make sure the account has a payment card that won't expire
soon. A lapsed domain is the only way this site can go down.

If you pick a different name, change it in three places before pushing: `SITE["url"]` in
`build.py`, `public/CNAME`, and the `README.md` link.

---

## 2. Create the repo and push

From `D:\UsefulToolsSite` in a terminal (the `gh` CLI is already logged in as TheGildedOne):

```bash
git init -b main
```

```bash
git add -A && git commit -m "LayerCalc: 15 free 3D printing calculators"
```

```bash
gh repo create layercalc --public --source=. --remote=origin --description "Free 3D printing calculators: cost, pricing, calibration, filament" --push
```

The repo must be **public** — GitHub Pages on private repos needs a paid plan. There's
nothing secret in it.

---

## 3. Turn on GitHub Pages

1. Open <https://github.com/TheGildedOne/layercalc/settings/pages>.
2. Under **Build and deployment → Source**, choose **GitHub Actions** (not "Deploy from a branch").
3. Go to the **Actions** tab. The `Publish` workflow will already have run from the push in
   step 2 — it may show as failed because Pages wasn't enabled yet. Click it → **Re-run all jobs**.
4. When it's green, the site is live at `https://thegildedone.github.io/layercalc/`.

   *(Links use absolute paths like `/filament-cost-calculator/`, so at this temporary address
   the navigation won't work — that's expected. It's correct once the custom domain is on.)*

---

## 4. Attach the domain in GitHub

Still on the Pages settings page:

1. **Custom domain** → type `layercalc.com` → Save. GitHub checks DNS, which will fail until
   step 5 is done; that's fine.
2. Come back after DNS propagates (usually minutes, up to a day) and tick **Enforce HTTPS**.
   It's greyed out until GitHub has issued the certificate, which it does automatically.

`public/CNAME` already contains `layercalc.com`, so every deploy keeps the domain set.

---

## 5. Point DNS at GitHub Pages

In your registrar's DNS panel, create these records:

| Type | Name | Value |
|---|---|---|
| A | `@` | `185.199.108.153` |
| A | `@` | `185.199.109.153` |
| A | `@` | `185.199.110.153` |
| A | `@` | `185.199.111.153` |
| CNAME | `www` | `thegildedone.github.io` |

**If DNS is on Cloudflare:** set each record's proxy status to **DNS only** (grey cloud, not
orange). GitHub needs to see the real traffic to issue its certificate. You can switch the
orange cloud on later if you want Cloudflare's caching, but it isn't needed.

Delete any placeholder A or CNAME records the registrar created for `@` and `www`.

Check with:

```bash
nslookup layercalc.com
```

It should list the four 185.199.x.153 addresses. Then finish step 4.

---

## 6. Tell the search engines

Do this once, after the domain works over HTTPS. All free.

### Google Search Console
1. <https://search.google.com/search-console> → **Add property** → *Domain* → `layercalc.com`.
2. It gives you a TXT record to add at the registrar (same panel as step 5). Verify.
3. **Sitemaps** → submit `https://layercalc.com/sitemap.xml`.

### Bing Webmaster Tools
1. <https://www.bing.com/webmasters> → **Add site**. Choose **Import from Google Search
   Console** — it copies the verification and sitemap in one click.
2. That's it. IndexNow is already wired: every deploy pings Bing with the full URL list, and
   the key file (`public/c01117d6…txt`) is on the site. Bing feeds DuckDuckGo, Yahoo,
   Copilot and much of ChatGPT search, so this one submission covers a lot.

### Optional
- **Yandex Webmaster** (webmaster.yandex.com) if you care about Russian-language traffic;
  it also accepts IndexNow.
- Google's **Rich Results Test** (search.google.com/test/rich-results) on one calculator
  page, to confirm the FAQ and breadcrumb structured data are read correctly.

---

## 7. Launch nudges (an afternoon, once)

A new domain ranks for nothing for a few months regardless of quality. These bring the
first visitors and the links that shorten that:

- Post the **temp tower generator** to r/3Dprinting, r/ender3, r/klippers and r/BambuLab
  as "I made a free browser-based test tower generator, no plugin needed". Link the tool,
  not the home page. Answer questions in the thread.
- Post the **pricing calculator** to r/3Dprinting and r/Etsy ("what to actually charge —
  with Etsy fees built in").
- Reply to existing "how much filament is left / how do I calculate e-steps / what should I
  charge" threads with the specific tool when it genuinely answers the question.
- Ask a couple of calibration guides and wikis (e.g. the Ellis print tuning guide, the
  Teaching Tech calibration site issue tracker, printer subreddit wikis) to link the tools.

Then leave it alone. Check Search Console once a month; after 4–6 months you'll see which
pages Google is sending people to, and that tells you what to build next.

---

## Later: updating the site

```bash
cd D:\UsefulToolsSite && python build.py && python check.py && git add -A && git commit -m "describe the change" && git push
```

The push deploys within about two minutes. `check.py` must pass — it stops a page with a
broken link or a JavaScript error from ever going live.
