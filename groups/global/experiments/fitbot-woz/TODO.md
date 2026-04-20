# פיט בוט — Execution TODO

**Owner:** Avishay
**Status:** Pre-launch
**Approach:** Lean-startup-aligned — solo dog-food → smoke test (Meta CTW) → WoZ with stranger opt-ins → decision gate
**Budget:** ~₪700–₪910 total (ads + virtual line + ChatGPT)
**Timeline:** ~2 weeks from Phase 0 start to Phase 4 final decision

See also: [SPEC.md](SPEC.md) · [README.md](README.md) · [prompt_he.md](prompt_he.md) · [prompt_en.md](prompt_en.md)

---

## Phase 0 — Pre-launch setup (est. 3–4 days)

### 0.1 Solo dog-food (2–3 days, zero cost)

Goal: catch bot-quality and prompt issues before strangers see them. Zero social cost.

- [ ] Open a fresh ChatGPT session, paste `prompt_he.md` (or `prompt_en.md`), verify `מוכן` response
- [ ] Run onboarding with yourself as the user — use real, honest answers
- [ ] Day 1: send morning + evening check-ins via `[שליחה: ...]`; log real food via photos; ask 2–3 real fitness questions
- [ ] Day 2: send more food logs, provoke a workout/recipe request, share a real struggle
- [ ] Day 3: deliberately create an ambiguous moment (vague message, off-topic question, late-night ping with `[זמן: 23:45]`)
- [ ] After each session, log in [notes.md](notes.md): what felt right, what felt off, what was missing
- [ ] Iterate the prompt inline when issues show up; commit each fix

**Kill gate:** if the bot doesn't feel useful to *you* after 3 days, do not spend on ads. Iterate or pivot first.

### 0.2 Creative production (1 day)

Target: **6 Hebrew ad creatives = 2 angles × 3 formats each**

- [ ] Draft Hebrew ad copy for angle A (Pain): headline, primary text, CTA
- [ ] Draft Hebrew ad copy for angle B (Friend): headline, primary text, CTA
- [ ] Drop Utility angle (already decided weak)
- [ ] Produce Angle A creatives:
  - [ ] 1× 9:16 vertical video, 15–20s, sound-on, hook in first 2s
  - [ ] 1× 4:5 feed video, 15s
  - [ ] 1× 1:1 static (fallback)
- [ ] Produce Angle B creatives (same 3 formats)
- [ ] Hook test: the first 2 seconds of each video must work without sound
- [ ] Mobile preview: view every creative on an actual phone at native size

### 0.3 Meta + WhatsApp infrastructure

- [ ] Meta Business Manager account (create or confirm existing)
- [ ] Meta Business Page connected
- [ ] WhatsApp Business Platform connected to the Fitbot number via Meta Business Suite
- [ ] Placeholder landing page (Carrd, 5 min) — even if running CTW, you need a pixel target
- [ ] Meta Pixel installed on placeholder page
- [ ] Conversions API (CAPI) installed alongside Pixel
- [ ] Events Manager: verify Lead event fires correctly from a test click
- [ ] Special Ad Category: declare "Not restricted" (consumer wellness, no housing/finance/employment)
- [ ] Payment method added, account verified
- [ ] Advertising Standards identity verification complete (can take 1–2 days — start early)

### 0.4 Operational prep

- [ ] Block calendar for the 7 days of the WoZ — operator availability roughly 08:00–22:00
- [ ] Decide ChatGPT model and confirm vision capability (GPT-4o or newer)
- [ ] Seed [library/workouts/](library/workouts/) with 3 curated starter workouts:
  - [ ] Home bodyweight — 20 min full body
  - [ ] Gym — upper/lower split, beginner-intermediate
  - [ ] No-equipment apartment workout (for "machine busy" type scenarios)
- [ ] Seed [library/nutrition/](library/nutrition/) with 2–3 references:
  - [ ] Macro estimates for common Israeli foods (shakshuka, pita, humus, bourekas, cottage)
  - [ ] High-protein meal ideas under 10 min prep
- [ ] Pre-fill [tracker.md](tracker.md) row headers ready for opt-ins
- [ ] Pick prompt variant (Hebrew or English) — commit before launch, use the same for every participant

---

## Phase 1 — Smoke test launch (D0)

### 1.1 Meta campaign setup

- [ ] Campaign objective: **Leads**
- [ ] Conversion location: **Click to WhatsApp** (not landing page)
- [ ] Budget: **CBO at ₪100/day** (₪700 over 7 days)
- [ ] Structure: 1 campaign → 2 ad sets (1 per angle) → 3 creatives per ad set
- [ ] Audience: **Advantage+**, Israel, Hebrew, ages 22–40
- [ ] Placements: **Advantage+ placements** (auto)
- [ ] Schedule: 7 days
- [ ] Connect the WhatsApp Business number so "Send Message" button routes correctly

### 1.2 Kill triggers configured upfront

- [ ] Ad set CPA > ₪30 → pause
- [ ] Creative CTR < 0.8% after 1,500 impressions → pause that creative
- [ ] Campaign spend > ₪200 with < 3 opt-ins → emergency stop, review before continuing

### 1.3 Launch

- [ ] Submit campaign for review
- [ ] Confirm approval (usually < 24h, can take longer first time)
- [ ] **Do not edit for 72 hours.** Learning phase violation invalidates the test.

---

## Phase 2 — Observation window (D0 → D+2)

Quiet period. No decisions, no edits.

- [ ] Check Meta Business Suite **once per day max**
- [ ] Note: total spend, opt-ins so far, CPA, CTR per creative
- [ ] Resist the urge to tweak. Learning phase needs volume.

---

## Phase 3 — Opt-in processing (ongoing from D0 onward)

### Per new WhatsApp opt-in

- [ ] In WhatsApp Business, create a Label for the contact (`WoZ-N` or their name)
- [ ] Open a **new** ChatGPT conversation, paste system prompt, verify `מוכן`
- [ ] Send M1 from [onboarding.md](onboarding.md) to the participant via WhatsApp
- [ ] When they reply, paste reply into their ChatGPT session → review → send
- [ ] Continue conversationally until onboarding checklist complete (name, age, gender inferred or asked, goal, routine/level, equipment, injuries, anything else)
- [ ] Add a row to [tracker.md](tracker.md) with their details
- [ ] Set phone calendar reminders for 08:00 and 20:00 (defaults) unless they asked to change

### Daily (per active participant)

- [ ] **~08:00:** send `[שליחה: צ'ק-אין בוקר]` → review → send to WhatsApp (confirm `[נשלח: ...]` if edited)
- [ ] **Inbound messages:** paste into their ChatGPT session (images directly, no marker); include `[זמן: HH:MM]` when time-relevant. Review → send → `[נשלח: ...]` if edited.
- [ ] **~20:00:** send `[שליחה: צ'ק-אין ערב]` → review → send
- [ ] **24h silence from participant:** send `[שליחה: אישור שתיקה]` **once**. No further nudges after that.
- [ ] **End of day:** update [tracker.md](tracker.md): active-on-day-N (✓/✗), unsolicited message count, notes

---

## Phase 4 — Decision gates

### D+3: First ad performance read (learning phase exited)

- [ ] CPA per ad set — calculated
- [ ] CTR per creative — reviewed
- [ ] Pause any ad set with CPA > ₪30
- [ ] Pause any creative with CTR < 0.8% @ 1,500 impressions
- [ ] Note any anomalies in [notes.md](notes.md)

### D+5: WoZ kill check

- [ ] Compute active-on-day-5 rate from tracker
- [ ] **If < 40% active → stop campaign and WoZ immediately.** Format doesn't work as-is. Document lessons; consider channel pivot (Telegram) or zoom-in pivot (drop check-ins, keep meal logging).
- [ ] Any participant reported Hebrew quality issues unprompted? → pause, fix prompt, consider restart
- [ ] Any participant reported feeling judged / unsafe advice? → stop immediately, address

### D+7: Final decision gate

Compute the full scorecard:

- [ ] Angle winner by CPA (directional; budget too small for statistical confidence)
- [ ] Day-7 active rate — target **≥ 60%**
- [ ] Participants with ≥ 1 unsolicited message — target **≥ 3**
- [ ] Participants who said "this is actually useful" unprompted — target **≥ 3**

Outcome decision:

- [ ] **All four green → Phase 5** (proceed)
- [ ] **Mixed (40–60% active, strong qualitative) → iterate** prompt/tone, re-run smaller version
- [ ] **Clearly failing → kill,** write up lessons in `notes.md`, archive

---

## Phase 5 — Post-test (only if green)

- [ ] Full write-up in [notes.md](notes.md): what worked, what didn't, winning angle, CPA curve, retention curve, qualitative highlights, surprises, open questions
- [ ] Pick next experiment:
  - [ ] Scaled ad test (₪3,000 over 2 weeks with winning angle only)
  - [ ] Add payment gate at day 30 to test monetization hypothesis
  - [ ] Build a real backend (leave WoZ mode) — this becomes a new spec
- [ ] Update [SPEC.md](SPEC.md) with validated learnings; start v1 spec for whatever comes next
- [ ] Align with Ohav on next phase commitment and budget

---

## Phase ∞ — Always-on kill criteria

Applicable at any time during the test:

- [ ] Any participant reports harm, unsafe advice, or hurt feelings → pause immediately, fix, review
- [ ] Operator burnout (can't sustain ~60 min/day) → reduce participants or pause new opt-ins
- [ ] Meta account issue (policy flag, payment issue) → pause, fix; if prolonged, switch to landing-page funnel
- [ ] ChatGPT / model issue (sustained bad output) → switch model or prompt variant

---

## Validation ladder position (per lean startup)

| Stage | Ladder level | Evidence type |
|---|---|---|
| Today (pre-launch) | 1–2 | Opinion / stated preference |
| After Phase 0.1 solo dog-food | 2 | Operator stated value |
| After Phase 1–3 smoke test opt-ins | 3 | Low-commitment signup |
| After Phase 4 Day 7 with engagement | **5** | Actively using (revealed preference) |

Target: **Level 5 on at least 5 strangers by Day 7.** That's the real green light.

---

## Pivot criteria (defined upfront)

- **Smoke test CPA > ₪30 across both angles** → demand or positioning is wrong → *value pivot*, do not build further
- **WoZ active-on-day-5 < 40%** → format is wrong → *channel pivot* (Telegram, SMS, voice) or *zoom-in pivot* (drop check-ins, keep meal-logging-only)
- **WoZ Day 7 active ≥ 60% but zero unsolicited messages** → tolerated, not loved → *engine-of-growth pivot* (paid acquisition only, no viral hook — different economics)
- **Winning angle = Friend, not Pain** → messaging pivot for scaled ads
- **Participants consistently ask for specific workout plans** (not accountability) → *zoom-in pivot* on programming side; accountability becomes retention layer not acquisition hook
