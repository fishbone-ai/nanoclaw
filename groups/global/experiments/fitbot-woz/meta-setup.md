# פיט בוט — Meta Business Setup & Verification

**Purpose:** Critical-path checklist to get the Meta Ads Manager ready to launch the [smoke-test.md](smoke-test.md) campaign.
**Audience:** Avishay, first-time Meta advertiser for this project.

## Summary: what you need, in order

| Step | Effort | Can block launch? | Done? |
|---|---|---|---|
| 1. Personal Facebook account with 2FA enabled | 5 min | Yes | [ ] |
| 2. Meta Business Portfolio (formerly "Business Portfolio") at business.facebook.com | 10 min | Yes | [ ] |
| 3. Meta Business Page for פיט בוט | 10 min | Yes | [ ] |
| 4. Ad Account inside Business Portfolio | 5 min | Yes | [ ] |
| 5. Payment method added to ad account | 5 min | Yes | [ ] |
| 6. Meta Pixel created + installed on landing page | 20 min | Yes | [ ] |
| 7. Phone number verification (when creating first campaign) | 5 min | Yes (instant) | [ ] |
| 8. **Advertiser Identity Verification** | 10 min upload + **48h to 14 days wait** | **Likely yes — biggest risk** | [ ] |
| 9. Business Verification (domain / registration docs) | 30 min + 2-5 days | **Probably not needed for this test** | — |

**The critical-path question is #8: Advertiser Identity Verification.** If Meta triggers this on your first campaign, you wait 48 hours to 14 business days before ads can serve. Everything else is self-serve and near-instant.

## What's different as of 2026 (important context)

As of March 2026, Meta [explicitly requires every ad account to be associated with a verified entity](https://www.auditsocials.com/blog/meta-ad-account-legitimacy-verification-requirement-2026). Meta's stated goal is to cover 90% of ad revenue under advertiser verification by end of 2026. For new accounts, this means:

- Phone verification at first campaign creation is **always triggered** now (not optional).
- Identity verification (government ID upload) is **frequently triggered automatically** based on signals (new account, new page, new payment method, policy-sensitive vertical, etc.).
- Wellness/fitness is not a restricted category, but "new-new-new-new" is itself a risk signal.

Plan for identity verification to be required. If it isn't, great, you save 48 hours.

Source: [Meta Verification Requirements for Advertisers](https://www.facebook.com/business/help/810450577622394), [Meta Ad Account Legitimacy Check 2026](https://www.auditsocials.com/blog/meta-ad-account-legitimacy-verification-requirement-2026).

## Step-by-step

### 1. Personal Facebook account with 2FA

- Log in to your Facebook account.
- Settings → Security → **Two-Factor Authentication** → enable (authenticator app preferred over SMS).
- Confirm your legal name on the profile matches your government ID (this matters for step 8).

### 2. Business Portfolio

- Go to [business.facebook.com](https://business.facebook.com/).
- Create Business → name it "פיט בוט" or "Fitbot" (English name avoids RTL quirks in Meta backend).
- Add your legal name as primary admin.
- Business email: use one you control.

### 3. Business Page

- Inside Business Portfolio → Pages → Add → Create New Page.
- Category: "Health/Beauty" or "Brand" works; "App Page" if you prefer.
- Name: `פיט בוט`.
- Add a profile image + cover image (can be simple text-on-color for now; placeholder is fine).
- Page details: short description (`מאמן אישי בוואטסאפ, בטא`), website (the Carrd LP once live).

### 4. Ad Account

- Business Portfolio → Ad Accounts → Add → Create New Ad Account.
- Time zone: Asia/Jerusalem.
- Currency: ILS.
- Account name: `פיט בוט - Ad Account`.
- Assign yourself as Admin.

### 5. Payment method

- Ad Account → Billing → Payment Settings → Add Payment Method.
- Credit card works fastest. PayPal also accepted in Israel.
- Set a spending limit: start with ₪1,000 as a safety ceiling (prevents runaway spend if something goes wrong).

### 6. Meta Pixel

- Business Portfolio → Events Manager → Connect Data Sources → Web → Meta Pixel → Create.
- Name: `Fitbot LP Pixel`.
- Get the Pixel base code snippet.
- Install on the Carrd landing page:
  - Carrd → Site Settings → Analytics → paste Pixel base code into the `<head>` section.
  - Alternative: Carrd has a native Facebook Pixel integration in Site Settings → Analytics, where you paste only the Pixel ID.
- Configure the **Lead** standard event to fire on form submit:
  - Option A (easiest): Carrd's form "on submit" action → redirect to `/thank-you` page, and install a second Pixel fire block on that thank-you page with the Lead event.
  - Option B: use Meta's Event Setup Tool in Events Manager to point-and-click-configure the form-submit event.
- Test: submit the form once yourself; open Events Manager → Test Events → confirm the Lead event fires.

### 7. Phone verification

- Triggered automatically the first time you create a campaign in Ads Manager.
- Enter your phone, receive SMS code, enter code. Done in ~2 minutes.
- Cannot be done ahead of time — it unlocks at campaign creation.

### 8. Advertiser Identity Verification (the slow one)

This is the step that determines whether you launch tonight or in 2-14 days.

**What triggers it:**

- New ad account on a new Business Portfolio with no prior spend history → high probability of trigger.
- Meta detects "signals of possible misrepresentation" — vague, often just "new entity."
- Sometimes the trigger appears only **after** you submit your first campaign for review.

**What you'll need (have ready before starting):**

- Government-issued photo ID (Israeli teudat zehut / driver's license / passport). See [accepted IDs list](https://www.meta.com/help/policies/804481810668573/).
- A phone camera for selfie + document photos.
- Address confirmation document in some cases (utility bill, bank statement).

**How to proactively start it:**

- Business Portfolio → Security Center → Identity Confirmation → Start Verification.
- Upload government ID (both sides if applicable).
- Take a selfie per Meta's guided flow.
- Submit.

**Timing expectations:**

- Fastest case: 48 hours.
- Typical case: 3-5 business days.
- Worst case: 14 business days.
- During Israeli holidays/weekends: add 1-3 days buffer.

**If you don't proactively start it:** Meta may let your first campaign run and then request verification mid-flight. If flagged mid-flight, your ads are paused until verification clears. This is worse than proactive verification.

**Recommendation: start step 8 TONIGHT even if you can't launch the campaign tonight.** The verification clock starts ticking while you finish other prep. Worst case it wasn't needed and you wasted 10 minutes of ID upload. Best case you shave 2-14 days off the timeline.

### 9. Business Verification — likely skip for this test

This is a separate, heavier verification that requires business registration documents (like a עוסק מורשה certificate or חברה בע"מ docs) and domain ownership proof.

- **When it's required:** WhatsApp Business API, Political/Social Issue ads, high-spend accounts, Advantage+ enterprise features.
- **When it's NOT required:** consumer wellness landing-page ads at ₪100/day. Which is us.

If Meta prompts for Business Verification during your campaign flow, it's likely because you connected a WhatsApp Business asset. For this smoke test we're not routing to WhatsApp natively — we're routing to a landing page — so do not connect any WhatsApp asset to the ad account. Avoids the trigger.

If prompted anyway, you can register as an עוסק מורשה individual (not a company) and supply that documentation; or pivot the identity to your personal name and skip business verification entirely. Lean toward "personal" identity for a solo test to minimize surface area.

## Common failure modes (and how to avoid)

| Failure | Cause | Fix |
|---|---|---|
| Campaign submitted, stuck "In Review" for days | Identity verification triggered post-submit | Proactively verify before submitting campaign |
| Campaign rejected for policy | Accidental health claim in ad copy | Review Meta's [Health & Wellness policy](https://transparency.meta.com/policies/ad-standards/); "בגרסת בטא, חינם" is fine, "תרדו 5 ק"ג בשבוע" is a banned claim |
| Ad account disabled | Mismatched identity info across Business Portfolio / Page / Ad Account / Pixel / domain | Before launch, audit every asset: name, address, phone, website — all must match |
| Pixel not firing | Install order, ad blocker during test, wrong page | Use Meta Pixel Helper browser extension to verify on the actual LP in a clean browser session |
| Budget runaway | Spending limit not set | Set account spending limit to ₪1,000 as safety ceiling (step 5) |

## Decision tree for tonight

```
Have you completed steps 1-4 (Business Portfolio, Page, Ad Account, Payment)?
├── No  → Do these now. ~30 min. Does not require verification wait.
└── Yes → proceed

Have you started Step 8 (Identity Verification)?
├── No → Start NOW. It runs in the background.
└── Yes → proceed

Is the landing page live with Pixel firing?
├── No → Build it. Steps 2-6 of smoke-test.md §Tonight's execution order.
└── Yes → proceed

Submit campaign to Meta for review.
Expected outcomes:
├── Approved (no verification trigger)  → ads serve within ~24 hours, you're live.
├── Approved pending verification        → complete ID upload, wait 48h-14d, then live.
└── Rejected                             → address policy flag, resubmit.
```

## What to do right now

1. Open business.facebook.com → confirm you have a Business Portfolio. If not, create it. (5 min)
2. In Business Portfolio → Security Center → Identity Confirmation → **start the ID verification process right now**, before anything else. Upload your teudat zehut. This clock runs in parallel with everything else. (10 min)
3. Meanwhile I'll draft the LP copy and help wire up Carrd + Pixel.

If verification completes in 48h, we launch on Day 2 at latest. If Meta never prompts you, we launch the moment the LP + campaign are ready.

Sources:
- [Verification Requirements for Advertisers — Meta Business Help Center](https://www.facebook.com/business/help/810450577622394)
- [Advertiser Identity Verification on Meta Ads — AdAmigo](https://www.adamigo.ai/blog/advertiser-identity-verification-on-meta-ads)
- [Meta Ad Account Legitimacy Check 2026 — AuditSocials](https://www.auditsocials.com/blog/meta-ad-account-legitimacy-verification-requirement-2026)
- [Types of ID that Meta supports for ID verification — Meta Help Center](https://www.meta.com/help/policies/804481810668573/)
