# Turning on ads (and analytics)

Everything is already plumbed and tested. Switching ads on is filling in one field in
`build.py`, publishing Google's consent message, and pushing. Nothing ad-related renders
— no scripts, no empty slots, no `ads.txt` — until you do.

To confirm the plumbing still works at any point, without switching anything on:

```bash
python tests/test_ads.py
```

It builds the site into a temporary folder with dummy IDs and checks every piece below.
It also runs on every deploy.

## When to apply

Google AdSense reviews the site before approving it, and rejects sites that look thin or new.
Apply when all of these are true:

- The domain has been live for **at least a month**.
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
   Build, check, commit, push. The next deploy adds the AdSense script to every page, writes
   `ads.txt` at the site root, and switches the privacy and about pages to describe the ads.

3. **Publish the consent message before requesting review** — see the next section.

4. Back in AdSense, click **Verify** / **Request review**. It reads the script from your
   pages and the `ads.txt` file. Review takes days to a few weeks.

5. Once approved, **Auto ads** are on by default: Google chooses placements itself. That's
   the zero-effort setting and is fine to leave forever.

## Consent (EEA, UK, Switzerland)

This is required, not optional. Google requires a **Google-certified consent tool integrated
with the IAB Transparency and Consent Framework** for anyone serving ads to visitors in the
European Economic Area, the UK and Switzerland. Without one, those visitors only get
non-personalised or limited ads.

Google's own tool qualifies and costs nothing:

1. AdSense → **Privacy & messaging** → **European regulations** → create a message.
2. Publish it for `layercalc.com`.

It is delivered by the AdSense script that is already on the page, so there is no code to add.
It supports TCF v2.3, which became mandatory in February 2026.

### What the site already does

Every page sets **Google Consent Mode v2 defaults** before any Google script runs:

- **Denied** in the 32 countries that require consent: the 27 EU states, Iceland,
  Liechtenstein, Norway, the UK and Switzerland. Covers ad storage, ad user data,
  ad personalisation and analytics storage.
- **Granted** everywhere else.
- A 500 ms wait so the consent message can answer before tags fire.

When a visitor answers Google's consent message, it updates those signals and both AdSense
and Analytics respect the answer. Until the message is published, visitors in those countries
simply stay denied: no advertising or analytics cookies are set for them.

This is already live for Analytics, so European visitors are not getting analytics cookies
without consent today.

### US state privacy laws

Privacy & messaging also offers a **US state regulations** message for states such as
California. It is not required to get approved, but it is worth publishing once ads are on.

## Optional: manual placements

Auto ads sometimes put a unit somewhere ugly. If you'd rather choose, the templates have
three named positions:

| Key | Where |
|---|---|
| `after_calc` | under the calculator card, before the article |
| `before_faq` | between the article and the FAQ |
| `hub` | on the home page (after the cost section) and on each category page |

In AdSense → **Ads → By ad unit → Display ad**, create a responsive unit for each position
you want and copy its numeric **slot ID** into `adsense_slots` in `build.py`. Positions left
blank stay empty (Auto ads may still fill them). You can then turn Auto ads off in AdSense
if you want only these.

How the manual slots are built:

- **Labelled "Advertisement"**, so an ad is never mistaken for part of the tool.
- **Kept clear of the calculator.** AdSense's placement policy prohibits ads that invite
  accidental clicks near interactive elements, so the slot under the calculator gets extra
  space above it, and no slot is ever placed inside a calculator.
- **Space is reserved** before the ad loads, so the page does not jump. Layout shift counts
  against Core Web Vitals, which affects rankings.
- **Unfilled slots collapse**, so a slot with no ad doesn't leave a blank gap.

## Analytics

Already on (`G-38ZP28C97M`). To change it: <https://analytics.google.com> → your property →
copy the **Measurement ID**, set `"ga4_id"` in `build.py`, build, push. The privacy page
updates itself.

## Expectations

This niche pays roughly **$4–12 per 1,000 page views** after ad blockers (a third or more of
3D printing readers run one). The cost/pricing pages attract sellers and pay at the top of
that range; the calibration pages attract tinkerers and pay at the bottom. Meaningful money
means tens of thousands of monthly page views, which for a well-linked tools site typically
takes 9–18 months from launch. AdSense pays out monthly once the balance passes $100.

## Turning it off

Blank the field, build, push. Everything reverts, including `ads.txt` and the privacy page.
Consent Mode defaults stay in place as long as Analytics is on.
