# פיט בוט — Demand Smoke Test (Pre-WoZ)

**Date:** 2026-04-20
**Owner:** Avishay
**Status:** Pre-launch
**Budget:** ₪700 (CBO ₪100/day × 7 days, unchanged)
**Timeline:** Ship ASAP; 7-day ad run; decision gate Day 7.

## Why this replaces the direct CTW → WoZ plan

The approved plan in [TODO.md](TODO.md) bundled too many assumptions into one test (demand + engagement + retention + WhatsApp-format fit, all at once). Per the lean-startup principle of *testing the riskiest assumption that can be tested cheapest*, we're sequencing them:

1. **This test (smoke test): demand signal.** Do Israelis read the pitch and commit a phone number? If no, kill; no need to proceed.
2. **Next test (WoZ, if this passes): engagement signal.** Do the committed signups actually engage for 7+ days in WhatsApp?

All the existing WoZ machinery (SPEC.md, prompts, onboarding.md, tracker.md, library/) remains ready and deferred. If this smoke test passes, signups roll into the WoZ test in Week 2.

## The riskiest assumption being tested

> **"Israelis aged 22-40 will read the פיט pitch and commit a phone number at a rate that makes the unit economics plausible."**

This stacks three sub-claims that all need to hold:

1. **Value (V2):** The articulated pain ("restart cycle + overwhelm") resonates with the target.
2. **Channel (M1):** Meta Hebrew ads can reach this audience at feasible cost.
3. **Messaging (M2):** "AI fitness coach in WhatsApp" is compelling enough once read to trigger commitment.

If *any* of these three fails, no amount of backend polish rescues the product. Test them first, cheaply, with no product exposure.

## What is explicitly NOT being tested here

- Whether the bot's responses are useful (V3, P1, P2) — needs WoZ exposure.
- Whether users engage for 7+ days (E1) — needs WoZ exposure.
- Whether users love the product unprompted (E2, E3) — needs WoZ exposure.

These are downstream. Do not confuse demand-signal with product-quality-signal.

## MVP shape

```
Meta ad (2 statics, 1 per angle)
    ↓
Landing page (Hebrew, mobile-first)
  - Headline + subhead
  - 2-paragraph pitch + chat mockup image
  - Form: name + phone + goal (optional) + consent checkbox
  - Submit button
    ↓
Thank-you page
  - Explicit expectation: "אשלח הודעה בוואטסאפ בימים הקרובים"
  - No bot message goes out tonight — operator sends manually in D+2 to D+4
    after Phase 0.1 dog-food
```

No backend, no auto-reply, no WhatsApp infra required to launch. The landing page captures phones into a list; the WoZ test in Week 2 (if this passes) converts the list into participants.

## Metrics (actionable, not vanity)

| Metric | What it measures | Decision weight |
|---|---|---|
| **Ad CTR** (per angle, per creative) | Is the concept hook-worthy? | Directional — informs kill triggers |
| **Landing-page CVR** (visits → form submits) | Is the positioning compelling once read? | **Primary signal** |
| **Cost per phone** (spend / valid phones) | Channel economics | **Primary signal** |
| **Angle split CPA** (A vs B) | Which pain framing converts? | Directional |
| **Completed goal selection** (optional field filled %) | Bonus — segmentation for WoZ invitation |

Vanity traps explicitly avoided: total impressions, total page views, total clicks. These will be visible in dashboards; do not make decisions from them.

## Pre-committed decision criteria (Day 7)

| Outcome | Decision | Reasoning |
|---|---|---|
| **15+ valid phones** at **≤ ₪35 CPA** | **Persevere → WoZ.** Invite the 8-12 best-fit signups to the 7-day WoZ. | Enough demand signal to justify operator-heavy WoZ. |
| **5–14 valid phones** at **₪35–₪70 CPA** | **Iterate.** Rewrite one angle, pick whichever angle had more pull, run a second smaller test (~₪300). Do not proceed to WoZ yet. | Mid signal; messaging or audience may be off. |
| **<5 valid phones** or **CPA > ₪70** | **Pivot or kill.** Document in [notes.md](notes.md). Consider channel pivot (organic, Telegram, Instagram) or kill the thesis entirely. | Demand signal too weak to support paid acquisition. |

**Kill triggers mid-flight (from [TODO.md §1.2](TODO.md), unchanged):**

- Ad set CPA > ₪30 → pause that ad set.
- Creative CTR < 0.8% after 1,500 impressions → pause that creative.
- Campaign spend > ₪200 with < 3 phones → emergency stop, review before continuing.

## Landing page specification

**Tool:** Carrd ([carrd.co](https://carrd.co/)). Free tier, Hebrew-capable, RTL support, 5-minute setup. Alternatives: Framer, Webflow — pick whichever you can ship fastest.

**Domain:** subdomain.carrd.co is acceptable for the smoke test. No custom domain needed for validation.

**Structure (top to bottom, mobile-first, single scroll):**

1. **Hero headline:** `מאמן אישי בוואטסאפ`
2. **Subhead:** `פיט בוט. שואל מה קורה בבוקר ובערב, עונה על שאלות, מסתכל על תמונה של הארוחה ואומר כמה קלוריות. בגרסת בטא, חינם.`
3. **Visual:** mockup image of a WhatsApp chat thread with פיט (can use the same mockup built for Creative 3 / Creative 6 in [creatives.md](creatives.md)).
4. **Pitch block** (2 short paragraphs):

   ```
   יש לכם כבר 3 אפליקציות כושר בטלפון ולא פתחתם אף אחת פעמיים?
   כל משפיען אומר משהו אחר על מה לאכול ואיך להתאמן?

   פיט בוט זה מאמן אישי שיושב באפליקציה שאתם כבר פתוחים בה 100 פעם ביום.
   שואל מה קורה בבוקר ובערב, עונה על שאלות בלי לשפוט, מסתכל על תמונה
   של הארוחה ואומר כמה קלוריות.

   בלי להוריד שום דבר חדש. בלי התחייבות. בטא, חינם.
   ```

5. **Form block:**

   - Headline: `רוצים להיות מבין הראשונים שנפתח להם?`
   - Subhead: `השאירו מספר וואטסאפ ואשלח הודעה ברגע שנתחיל.`

   Fields:
   | Field | Type | Required | Placeholder |
   |---|---|---|---|
   | `שם פרטי` | text | yes | `מה השם שלך?` |
   | `מספר וואטסאפ` | tel | yes | `05x-xxxxxxx` |
   | `מה המטרה שלך?` | dropdown | no | options: `לרדת במשקל` / `להעלות מסה` / `להרגיש טוב` / `להתחיל מאפס` / `משהו אחר` |
   | Consent checkbox | checkbox | yes | label: `אני מסכים/ה שפיט בוט ישלח לי הודעה בוואטסאפ` |

   Submit button: `שמור לי מקום`

6. **Thank-you state** (after submit):

   ```
   מעולה, רשמתי את המספר.
   נשלח הודעה בוואטסאפ בימים הקרובים כשנתחיל.
   אם התחרטת, פשוט תגיד לי כשאשלח.
   ```

**Storage:** Carrd form submissions can go to Google Sheets (via Carrd's built-in integration) or to a ConvertKit/beehiiv list. Google Sheets is simplest. Capture: timestamp, name, phone, goal, consent=TRUE, IP (for consent record).

**Pixel:** Install Meta Pixel on the page. Configure "Lead" standard event to fire on form submit. Meta will optimize toward that event.

## Compliance — Israeli law (critical, do not skip)

Israel's **Communications Law (Amendment 40 — "חוק הספאם")** prohibits sending commercial/marketing messages (SMS, email, **WhatsApp**) without prior explicit consent. Violating it exposes you to ₪1,000 per message statutory damages and class-action risk.

Requirements for the LP:

- **Consent checkbox must be explicit and unchecked by default.** Cannot be pre-ticked.
- **Consent text must specify WhatsApp as the channel.** Do not use vague "marketing messages" language.
- **Record of consent must be retained.** Store timestamp, IP, and consent-text-version alongside the phone number. Google Sheets auto-captures timestamp; Carrd auto-captures IP.
- **Easy opt-out must be honored.** Respect any "stop"/"הסר" reply in WhatsApp when the time comes.

The text in §5 above (`אני מסכים/ה שפיט בוט ישלח לי הודעה בוואטסאפ`) satisfies the requirement. Do not soften it.

## Ad creatives

Reuse Creatives 3 and 6 from [creatives.md](creatives.md) (the two 1:1 statics, one per angle). They were already designed for Advantage+ placements and will auto-crop to feed/story placements acceptably.

- **Angle A (Pain)** static → Ad Set A
- **Angle B (Friend)** static → Ad Set B

**Important copy tweak vs. creatives.md:** the CTA on these ads should be `שלח הודעה בוואטסאפ` replaced with **`למד עוד`** (Learn More), since we're driving to a landing page, not WhatsApp. Update the static's in-image CTA and the Meta CTA button both.

All other creative elements (headline, description, primary text) from [creatives.md](creatives.md) carry over unchanged.

The 4 video creatives in [creatives.md](creatives.md) are **deferred** until after this demand test passes. No production tonight.

## Meta campaign configuration

| Setting | Value |
|---|---|
| **Campaign objective** | Leads |
| **Conversion location** | Website |
| **Optimization event** | Lead (configured via Pixel on form submit) |
| **Budget** | CBO ₪100/day |
| **Schedule** | 7 days, starts on launch approval |
| **Structure** | 1 campaign → 2 ad sets (A, B) → 1 creative per ad set |
| **Audience** | Advantage+, Israel, Hebrew, ages 22–40 |
| **Placements** | Advantage+ placements (auto) |
| **Special ad category** | None (consumer wellness, not restricted) |

## Tonight's execution order (sequential, cannot parallelize)

1. **[Meta verification gate — see Meta-setup.md]** Confirm identity verification is in progress or clear. If not done and can't launch tonight, still complete steps 2-4 below so we launch the moment verification clears.
2. **Landing page** — Carrd, ~30 min including copy paste and form wiring.
3. **Pixel + Lead event** — install Meta Pixel, test the Lead event fires.
4. **Two static creatives** — produce in Canva, ~40 min, using copy from [creatives.md](creatives.md) with CTA swapped to `למד עוד`.
5. **Google Sheet** — create for form captures; connect Carrd form.
6. **Test end-to-end** — submit a real test form submission, verify Pixel fires, verify row lands in sheet.
7. **Meta campaign** — configure per table above, upload creatives, submit for review.
8. **Calendar reminders** — Day 3 check-in (mid-week review), Day 5 kill check, Day 7 decision gate.
9. **Stop editing.** Meta learning phase needs 72 hours of no changes.

## What Phase 0.1 (solo dog-food) becomes

The original plan required dog-fooding the bot *before* launching ads. This smoke test changes that: since no strangers reach the bot tonight, you can **dog-food in parallel** with the campaign running. Use the 7 days of ad-test window to run the solo dog-food per [TODO.md §0.1](TODO.md). By Day 7, if the demand signal is green, you also have 7 days of self-dogfood data ready to de-risk Week 2's WoZ.

## What passes forward to the WoZ (if demand validates)

- Phone list with names + goals → WoZ participant candidates.
- Confirmed demand signal → justification for operator time commitment.
- Angle winner → primary copy for WoZ recruitment / onboarding tone calibration.
- Creative A/B learnings → inform video production for Week 2+ (Motion + full video creatives).

## Open items

- [ ] Carrd vs. Framer vs. Webflow — confirm tool choice before building.
- [ ] Meta identity verification status (see [meta-setup.md](meta-setup.md)).
- [ ] Thumb-sized chat mockup image for the LP — can reuse from Creative 3 / 6 design work, or build a quick one in Figma/Canva.
- [ ] Google Sheet template set up with consent-record columns.
