# Turning on ads (and analytics)

Everything is already plumbed. Switching ads on is filling in one field in `build.py` and
pushing. Nothing renders — no scripts, no empty slots, no `ads.txt` — until you do.

## When to apply

Google AdSense reviews the site before approving it, and rejects sites that look thin or new.
Apply when all of these are true:

- The domain has been live for **at least a month** (they check).
- Search Console shows pages being indexed and some clicks.
- Roughly **1,000+ visitors a month**. Approval below that is possible but flaky, and
  earnings would be pennies anyway.

The site already has what reviewers look for: substantial original text on every page, an
About page, a Contact page, a Privacy Policy and Terms. Don't add anything for the review.

## Step by step

1. Sign up at <https://adsense.google.com> with your Google account. Add `layercalc.com` as a
   site. It gives you a **publisher ID** like `ca-pub-1234567890123456`.

2. In `build.py`, set it:
   ```python
   "adsense_client": "ca-pub-1234567890123456",
   ```
   Build, check, commit, push. The next deploy adds the AdSense script to every page's head,
   writes `ads.txt` at the site root (AdSense requires this and will nag until it sees it),
   and switches the privacy page's advertising paragraph from "no ads" to the real one.

3. Back in AdSense, click **Verify** / **Request review**. It reads the script from your
   pages and the `ads.txt` file. Review takes days to a few weeks.

4. Once approved, **Auto ads** are on by default: Google chooses placements itself. That's
   the zero-effort setting and is fine to leave forever.

## Consent (EU / UK / Switzerland / some US states)

AdSense requires a consent prompt for visitors in those regions. Use Google's own: in
AdSense → **Privacy & messaging** → GDPR → create a message → publish. It's delivered by the
same script that's already on the page; no code changes. Do this before the site gets much
European traffic.

## Optional: manual placements

Auto ads sometimes put a unit somewhere ugly. If you'd rather choose, the templates have
three named positions:

| Key | Where |
|---|---|
| `after_calc` | directly under the calculator card, before the article |
| `before_faq` | between the article and the FAQ |
| `hub` | on the home page (after the cost section) and on each category page |

In AdSense → **Ads → By ad unit → Display ad**, create a responsive unit for each position
you want and copy its numeric **slot ID** into `adsense_slots` in `build.py`. Positions left
blank stay empty (Auto ads may still fill them). You can then turn Auto ads off in AdSense
if you want only these.

## Analytics

Not required for AdSense, but Search Console alone doesn't tell you which calculators people
actually *use*. If you want that:

1. <https://analytics.google.com> → create a GA4 property for `layercalc.com` → copy the
   **Measurement ID** (`G-XXXXXXXXXX`).
2. Set `"ga4_id"` in `build.py`, build, push. The privacy page updates itself.

## Expectations

This niche pays roughly **$4–12 per 1,000 page views** after ad blockers (a third or more of
3D printing readers run one). The cost/pricing pages attract sellers and pay at the top of
that range; the calibration pages attract tinkerers and pay at the bottom. Meaningful money
means tens of thousands of monthly page views, which for a well-linked tools site typically
takes 9–18 months from launch. AdSense pays out monthly once the balance passes $100.

## Turning it off

Blank the field, build, push. Everything reverts, including `ads.txt` and the privacy page.
