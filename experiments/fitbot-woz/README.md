# פיט בוט — WhatsApp Fitness Coach WoZ

7-day Wizard-of-Oz test validating whether a WhatsApp-native AI fitness coach is a viable product for the Israeli market. See [SPEC.md](SPEC.md) for the full approved design.

## How it works

Manual simulation: operator + ChatGPT behind the scenes, one dedicated ChatGPT session per participant. Operator reviews every message before sending, pastes every user reply back into ChatGPT. No code, no infrastructure — just WhatsApp Business + ChatGPT.

## Setup checklist (one-time)

- [ ] Dedicated phone number with SMS capability (~₪10/mo virtual line works)
- [ ] [WhatsApp Business](https://business.whatsapp.com/) installed and verified on that number; enable Labels
- [ ] ChatGPT subscription with a vision-capable model (GPT-4o or newer)
- [ ] Pick one prompt variant: [prompt_he.md](prompt_he.md) or [prompt_en.md](prompt_en.md). Use the same one for every participant.
- [ ] Draft [recruitment.md](recruitment.md) personalizations; start inviting
- [ ] Phone calendar reminders for each participant's morning + evening check-in times

## Daily workflow

1. **Morning** (per user's chosen time): in their ChatGPT session, send `[שליחה: צ'ק-אין בוקר]` → review → paste to WhatsApp. If edited: `[נשלח: <actual text> | סיבה: <why>]` back to ChatGPT.
2. **Throughout day**: user message arrives → paste into their ChatGPT session. Photos: paste the image directly (the bot sees it). Review response, send, confirm `[נשלח: ...]` if edited.
3. **Evening** (per user's chosen time): `[שליחה: צ'ק-אין ערב]` → review → send.
4. **24h silence**: one-time `[שליחה: אישור שתיקה]`. No further nudges regardless.
5. **End of day**: update [tracker.md](tracker.md); log anything notable in [notes.md](notes.md).

## Order of operations for a new participant

1. WhatsApp Business: create a Label for this person
2. Open **new** ChatGPT conversation → paste the chosen prompt
3. ChatGPT replies `מוכן` → ready
4. Send M1 from [onboarding.md](onboarding.md) to the participant via WhatsApp
5. When they reply, paste their reply into their ChatGPT session (image messages: paste the image directly)
6. Bot generates the next onboarding question
7. Continue until all user-info fields are filled; at that point bot says "מעולה, הבנתי. מתחילים מחר בבוקר ב-..."
8. Add to [tracker.md](tracker.md) with their details

As user details emerge, feed them to ChatGPT as `[הקשר: הוא/היא <gender>, קוראים לו/לה <name>]` so pronouns switch from plural to singular.

## Weekly arc

| Day | Milestone |
|-----|-----------|
| 1   | Recruit + onboard. Send M1, complete onboarding with each. |
| 2   | First full day. Morning + evening check-ins. |
| 3   | Mid-week tracker review. Engagement trend? |
| 5   | **Kill check.** <40% active-on-day-5 → stop. |
| 7   | Final update. Go / iterate / kill decision. |

## Kill / green-light thresholds

From [SPEC.md §9](SPEC.md):

**Kill immediately if:**
- On Day 5, <40% of participants are active-on-day-5
- Hebrew quality is off and participants comment unprompted
- Any participant reports feeling unsafe or harmed

**Green light (proceed to ₪900 ad test in week 2):**
- Day 7 ≥60% active
- ≥3 participants sent ≥1 unsolicited message during the week
- ≥3 say "this is actually useful" unprompted

**Middle (iterate, don't ship, don't kill):**
- 40–60% active on Day 7 with strong qualitative → adjust prompt/tone and rerun

## Files

| File | Purpose |
|------|---------|
| [SPEC.md](SPEC.md) | Canonical approved design |
| [prompt_he.md](prompt_he.md) | System prompt — Hebrew instructions |
| [prompt_en.md](prompt_en.md) | System prompt — English instructions, Hebrew output |
| [onboarding.md](onboarding.md) | M1 opener, copy-paste ready |
| [recruitment.md](recruitment.md) | Network invite messages |
| [tracker.md](tracker.md) | Participant engagement data |
| [notes.md](notes.md) | Running operator observations |
| library/workouts/ | Curated workouts (populate on demand) |
| library/nutrition/ | Recipes / food info (populate on demand) |
