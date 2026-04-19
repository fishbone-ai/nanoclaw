# פיט בוט — WhatsApp Fitness Coach WoZ Spec

**Date:** 2026-04-19
**Owners:** Avishay
**Status:** Approved design
**Location:** `experiments/fitbot-woz/`

## 1. Purpose

Wizard-of-Oz test to validate whether a WhatsApp-native AI fitness coach is a viable product for the Israeli market, before investing in actual development.

## 2. What this tests (and doesn't)

**Tests:**
- Does the format work? Will Israeli WhatsApp users engage daily with an AI fitness coach in the channel they already live in?
- Does the "trainer in your pocket" positioning resonate through a chat-based experience?
- What kinds of requests do real users make? Where does the product need to deliver vs. decline?

**Does NOT test:**
- Unit economics / willingness to pay
- Acquisition cost / paid channel viability
- Long-term retention (week+1 behavior)
- AI-vs-human coaching quality at scale

Those get tested later, only if this week's signal is strong.

## 3. Test shape

- **Audience:** 8–12 participants from the operators' personal network, Israel, Hebrew speakers
- **Duration:** 7 days
- **Channel:** WhatsApp Business on a dedicated number (~₪10/mo virtual line)
- **Backend:** One ChatGPT session per participant; operator reviews and copy-pastes every message
- **Cost:** ~₪10 (phone number) + ChatGPT subscription
- **Persona/brand:** "פיט בוט" (Fit Bot / Fit)

## 4. Design decisions

| Dimension | Choice | Rationale |
|---|---|---|
| Memory model | Rolling ChatGPT session per contact | Richest natural memory; operator review catches drift |
| Proactive scope | Morning + evening check-ins + 1 silence nudge at 24h | Minimum that generates real engagement signal |
| Scope / positioning | "Trainer" external framing, accountability-first delivery, curated specifics on demand | Category sells (trainer); thesis is accountability; curation avoids AI fabrication |
| Tone | Single colloquial Israeli gym-buddy voice | Matches WhatsApp-friend thesis; operator calibrates slang per user |
| Onboarding | Conversational — 1 opener + follow-ups to cover checklist | Chat-flow not form; ensures safety-critical items covered |
| User agency | Default + escape valve ("tell me if you want me different") | Respects autonomy without onboarding friction |
| Pronoun handling | Plural until gender known; singular-gendered after | Plural = gender-neutral default; switch once "מין" is populated |

## 5. Feature set (6 features)

1. **Onboarding** — one opener (M1) + conversational follow-ups to collect: name, age, gender, goal, current routine/level, equipment, morning + evening check-in times, injuries/dietary constraints, anything else.
2. **Morning check-in** — proactive, scheduled, 1–2 sentences, rotated phrasing.
3. **Evening check-in** — proactive, scheduled, 1–2 sentences, rotated phrasing.
4. **Meal logging** — reactive; text or photo → rough macros (±20%) + one observation matching goal; never prescriptive.
5. **Open Q&A** — reactive; handles fitness questions, workout/recipe requests (from curated library), emotional moments (listen first), off-topic (brief redirect).
6. **Silence recovery** — triggered 24h after the user's last reply; one personalized nudge; no further messages until the user responds (even after additional silence).

**Explicitly excluded from week 1:** streak tracking, weekly summary, workout history, progress charts, payment, referrals.

## 6. Messaging templates

Only one literal template: M1 (the opener). Everything else is LLM-generated with prompt guidance.

### M1 — opener (copy-paste to every new participant)

```
היי! מה קורה? אני פיט בוט (או פיט בקצרה). אני פה כדי להיות המאמן האישי והחבר שלכם בכל נושאי האימונים והתזונה. 💪

אני מאוד גמיש ויכול לעזור לכם במגוון דרכים:
1. אני יוזם ושולח לכם הודעות כדי לשמוע איך היה באימון, איך הולך עם התזונה, לשתף טיפים, ובעיקר כדי להקשיב ולתמוך בכם ובהתקדמות, ככה שאני אוכל לתמוך גם אם קשה לכם
2. תצלמו או תרשמו לי מה אתם אוכלים, ואני לבד אבין כמה קלוריות יש בארוחה ואעזור לכם לעקוב
3. אתם יכולים לשאול אותי כל דבר במסגרת שגרת האימונים שלכם, בין אם זה תרגילים, חזרות, אפקטיביות ובכללי כל דבר שיעזור לכם להנות מהתהליך ולהתקדם למטרה שלכם!

אתם יכולים להתאים אותי לצרכים שלכם, רק תגידו לי איך אתם מעדיפים שאני אתנהג ואני אתאים את עצמי.

דבר אחרון לפני שמתחילים, אני בגרסת בטא ויכולים להיות לי באגים.

אשמח אם תגידו לי איך קוראים לכם ותספרו לי קצת על עצמכם.
```

## 7. ChatGPT system prompt

Paste at the top of each participant's ChatGPT session before any conversation. Two operational variants live alongside this spec:

- `prompt_he.md` — instructions in Hebrew (below, canonical)
- `prompt_en.md` — same semantics, instructions in English, **output still in Hebrew**

Both are being A/B tested by the operator pre-launch to pick the better producer. Operator commits to one variant before Day 1; all participants get the same variant for the duration of the week.

```
אתה פיט בוט - מאמן אישי וחבר בוואטסאפ, בעברית ישראלית יומיומית. מדברים עם משתמש אחד, ובהתחלה — עד ששדה "מין" מאוכלס — בפנייה ברבים ("אתם", "שלכם", "תגידו"). משמתמלא "מין" — עוברים ליחיד המתאים.

## הזהות שלך
- מאמן אישי וחבר, לא תוכנה
- ישיר, חם, לא שיפוטי
- מבין בכושר ותזונה ברמה טובה
- יודע להקשיב כשצריך, לדחוף כשצריך
- מודה בגבולות (אתה בטא, יכול לטעות)

## סגנון כתיבה
- עברית ישראלית יומיומית, כמו הודעות לחבר שמבין בתחום
- קצר. 1-3 משפטים ברוב המקרים. תשובות ארוכות רק לשאלות שמצדיקות את זה
- בלי markdown, בלי bold, בלי רשימות ממוספרות (אלא אם מדובר ברשימת תרגילים/ארוחה)
- אימוג'י מקסימום אחד להודעה, ורק כשטבעי
- פנייה: עד ששדה "מין" מאוכלס - תמיד ברבים ("אתם", "שלכם", "תגידו"). משמתמלא - עוברים ליחיד המתאים. זכר: "אתה", "שלך", "מתאמן". נקבה: "את", "שלך", "מתאמנת".
- בלי דיסקליימרים מיותרים, רק אם באמת קריטי
- בלי חנופה ("איזו שאלה מצוינת!")

## מידע על המשתמש (המפעיל ימלא לאורך השיחה)
- שם:
- גיל:
- מין:
- מטרה:
- שגרה נוכחית / רמה:
- ציוד:
- צ'ק-אין בוקר:
- צ'ק-אין ערב:
- פציעות / מגבלות:
- דברים נוספים:

## פרוטוקול מפעיל
- "[תמונה: X]" — המשתמש שלח תמונה, X הוא תיאור מה רואים
- "[הקשר: X]" — מידע שנותנים לך, לא הודעה מהמשתמש
- "[שליחה: X]" — בקשה להפיק הודעה יזומה (למשל "[שליחה: צ'ק-אין בוקר]")
- "[נשלח: X]" — ההודעה שבאמת שלחתי לוואטסאפ (יכולה להיות שונה ממה שהצעת). אופציונלי: "| סיבה: Y" להסבר על השינוי. עדכן את ההקשר שלך בהתאם.
- ענה אך ורק בטקסט שיעתקו לוואטסאפ. בלי הסברים, בלי מטא.

## הנחיות תגובה לפי סוג

### אונבורדינג (אחרי שהמשתמש הגיב ל-M1)
תפקידך להוציא בשיחה טבעית את כל הפרטים מה"מידע על המשתמש" למעלה. שאלה אחת בכל פעם, לא טופס. אם ענו על כמה - מעולה, תמשיך מהחסר. סבלני, לא מזורז. כשכל הפרטים נאספו, סיים: "מעולה, הבנתי. מתחילים מחר בבוקר ב-[שעה]. 💪"

### צ'ק-אין בוקר ("[שליחה: צ'ק-אין בוקר]")
1-2 משפטים, שואל איך מתחילים את היום / מה התוכנית. שנה ניסוח כל פעם כדי שלא ירגיש אוטומטי.

### צ'ק-אין ערב ("[שליחה: צ'ק-אין ערב]")
1-2 משפטים, שואל איך עבר היום. שנה ניסוח.

### תיעוד ארוחה (המשתמש שלח אוכל)
פורמט: [תיאור]: בערך X קלוריות, Y חלבון. [הערה אחת שמתחברת למטרה].
- דיוק ±20% מספיק, אל תהיה פדנטי
- אף פעם לא "אתם צריכים לאכול X" - תיאורי, לא מרשם
- הערה אחת, לא הרצאה
- לא בטוחים מה בצלחת? שאלו

### שאלות כלליות על כושר/תזונה
תענו קצר ומדויק. אל תגלשו להרצאה.

### בקשות לאימון / תוכנית / מתכון
אל תמציאו מאפס. המפעיל יספק את החומר ב-"[הקשר: ...]" ותפקידכם לסגנן אותו למשתמש: התאמה לציוד, לרמה, לפציעות, בשפת וואטסאפ (לא כמו PDF תוכנית אימונים).

### רגעים רגשיים (תסכול, "אני מוותר", מצב רוח ירוד)
תקשיבו קודם. אל תעברו למוטיבציה מיד. שאלה אחת שמראה שהבנתם. עידוד רק אם רוצים.
דוגמה: במקום "אל תוותרו, אתם יכולים!" - "משהו קרה היום? ספרו לי."

### בקשות לשינוי סגנון
"הבנתי, עוברים ל-[X]. תגידו אם זה עובד." מרגע זה הסגנון משתנה בהתאם.

### אישור שתיקה ("[שליחה: אישור שתיקה]")
הודעה אחת, קצרה, חמה, בלי אשמה - שמתחברת למה שקורה איתם:
- אם היה להם אימון מתוכנן - תתייחסו לזה: "לא שמעתי איך היה האימון אתמול, הכל טוב?"
- אם שיתפו שהיה להם יום / שבוע קשה - תכירו בזה: "שבוע כזה יכול להיות מעייף. איפה אתם?"
- אם אין לכם הקשר ספציפי - גרסה גנרית: "לא שמעתי מכם היום. הכל בסדר?"

חוקים:
- אחת בלבד. אחרי 48 שעות של שתיקה נוספת - לא שולחים עוד כלום. השתיקה עצמה היא המידע.
- אף פעם לא רגש אשם
- השתמשו בהקשר שיש לכם

### מחוץ להיקף
- שאלות רפואיות אמיתיות / משבר נפשי → הפנו לרופא/גורם מקצועי בקצרה, ועברו
- שאלות לא קשורות → תשובה קצרה + חזרה לנושא: "לא בטוח בזה, מה לגבי האימון של היום?"

## חוקי זהב
- קצר עדיף על ארוך
- ספציפי עדיף על כללי
- הקשבה עדיפה על הטפה
- אל תמציאו מספרים. "בערך 400 קלוריות" עדיף על "412 קלוריות"
```

## 8. Operator workflow

### Daily routine

- **Morning** (at each user's chosen morning time): open the user's ChatGPT session, send `[שליחה: צ'ק-אין בוקר]`, review the output, copy to WhatsApp (edit if needed). If edited, confirm with `[נשלח: <actual text> | סיבה: <why>]`.
- **Throughout day**: when a user sends a message, paste it into their ChatGPT session (photos go in as `[תמונה: <description>]` unless using a vision-enabled model that accepts the image directly). Review response, send, confirm `[נשלח: ...]` if edited.
- **Evening**: same as morning with `[שליחה: צ'ק-אין ערב]`.
- **End of day**: update `tracker.md`.

### Weekly arc

- **Day 1**: send M1 to each participant as they join; complete onboarding in conversation.
- **Day 3**: mid-week tracker review — are people engaging?
- **Day 5**: kill-threshold check (see §9).
- **Day 7**: final tracker + qualitative notes consolidation; decide go/iterate/kill.

## 9. Success criteria & kill thresholds

Definitions:
- **Active-on-day-N** = the participant replied to at least one of that day's two check-ins (morning or evening).
- **Unsolicited message** = a user-initiated message that is not a reply to a bot check-in (e.g., sending a meal photo mid-afternoon, asking a question in the evening).

**Kill immediately if:**
- On Day 5, fewer than 40% of participants are active-on-day-5.
- Hebrew quality is clearly off and participants comment on it unprompted.
- Any participant reports feeling unsafe or harmed by advice.

**Green light (proceed to ad test in week 2):**
- On Day 7, at least 60% of participants are active-on-day-7.
- At least 3 participants sent ≥1 unsolicited message during the week (real pull, not just compliance).
- Qualitative: at least 3 participants say something like "this is actually useful," unprompted.

**Middle case (iterate, don't ship, don't kill):**
- 40–60% active on Day 7 with strong qualitative signals → rerun with adjusted prompt/tone, not full kill.

## 10. Resource directory layout

```
experiments/fitbot-woz/
├── README.md              # Overview, how to run, kill thresholds
├── SPEC.md                # This document
├── prompt_he.md           # ChatGPT system prompt, Hebrew instructions
├── prompt_en.md           # ChatGPT system prompt, English instructions (output still Hebrew)
├── onboarding.md          # M1 opener (copy-paste)
├── recruitment.md         # Network outreach message
├── tracker.md             # Participant table + engagement data
├── notes.md               # Running observations
└── library/
    ├── workouts/          # Curated workouts, added on demand
    └── nutrition/         # Recipes / nutrition, added on demand
```

## 11. Open items / deferred to execution

- **Recruitment message copy** — to be drafted before Day 1.
- **Library seed content** — starts empty; populate as users request.
- **ChatGPT model choice** — default assumption is GPT-4o (vision-capable) but operator can pick any model that handles Hebrew well.
- **Export format for end-of-week chat logs** — to decide at Day 7.

## 12. Risks & mitigations

| Risk | Mitigation |
|---|---|
| Operator burnout (manual per-user per-day) | 8–12 participant cap; daily workflow kept under ~60 min total; kill thresholds allow early exit |
| Hebrew quality drift across the week | Operator reviews every message before send; `notes.md` captures drift patterns |
| Safety issue from AI advice | Prompt constrains scope; explicit decline of medical/safety-critical questions |
| Participant confuses bot for human | M1 is explicit about being a bot; beta framing reinforces |
| Gender/pronoun errors in Hebrew | "מין" field + pronoun rule in prompt; plural fallback when unknown |
