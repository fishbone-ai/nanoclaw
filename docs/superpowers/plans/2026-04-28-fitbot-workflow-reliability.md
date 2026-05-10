# FitBot Workflow Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restructure the FitBot Kapso workflow to detect silent agent failures (0 output_tokens), retry up to 2 times, and send a Hebrew fallback message — while deterministically loading user state via a workflow node instead of relying on the model.

**Architecture:** Three Kapso serverless functions handle routing logic (load_state, reply_check, retry_handler). The workflow graph replaces the single agent+enter_waiting loop with: load_state → agent → reply_check_decide → retry loop / wait_for_response. The agent node drops `enter_waiting` and `state_get` entirely.

**Tech Stack:** Kapso Platform API (base URL `https://api.kapso.ai/platform/v1`, auth `X-API-Key`), Kapso Cloudflare Worker functions, Python 3 for API calls.

**Constants used throughout:**
- `KAPSO_KEY` = value of `KAPSO_API_KEY` in `/share/nanoclaw/.env`
- `WORKFLOW_ID` = `a58ad8cc-d125-47fa-8481-b717fb56993d`
- `REPLY_CHECK_FN_ID` = `88dfc487-0f8f-4bde-89b8-b67d84bfbd69` (already deployed)
- `SUPABASE_STATE_URL` = `https://iejvqtvnrthvhxemonlz.supabase.co/functions/v1/fitbot-state`

---

### Task 1: Update fitbot-reply-check to handle nudge_done + reset retry_count

**Files:** Kapso function `88dfc487-0f8f-4bde-89b8-b67d84bfbd69`

The currently deployed function only returns `replied`/`no_reply`. It needs a third edge `nudge_done` for nudge executions, and must reset `retry_count` to 0 on success.

- [ ] **Step 1: Update function code**

```bash
KAPSO_KEY=$(grep KAPSO_API_KEY /share/nanoclaw/.env | cut -d= -f2)
curl -s -X PATCH "https://api.kapso.ai/platform/v1/functions/88dfc487-0f8f-4bde-89b8-b67d84bfbd69" \
  -H "X-API-Key: $KAPSO_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "function": {
      "code": "async function handler(request, env) {\n  const body = await request.json();\n  const availableEdges = body.available_edges || [];\n  const context = body.execution_context?.context || {};\n  const vars = body.execution_context?.vars || {};\n\n  const lastMessage = context.agent_last_message;\n  const replied = lastMessage !== null && lastMessage !== undefined && lastMessage !== \"\";\n  const isNudge = !!(vars.nudge_intent);\n\n  let nextEdge;\n  let responseVars = {};\n\n  if (!replied) {\n    nextEdge = \"no_reply\";\n  } else {\n    responseVars = { retry_count: 0 };\n    nextEdge = isNudge ? \"nudge_done\" : \"replied\";\n  }\n\n  return new Response(JSON.stringify({\n    vars: responseVars,\n    next_edge: availableEdges.includes(nextEdge) ? nextEdge : (availableEdges[0] || \"replied\")\n  }), {\n    headers: { \"Content-Type\": \"application/json\" }\n  });\n}"
    }
  }' | python3 -c "import sys,json; d=json.load(sys.stdin); print('status:', d['data']['status'])"
```

Expected: `status: draft`

- [ ] **Step 2: Deploy the updated function**

```bash
KAPSO_KEY=$(grep KAPSO_API_KEY /share/nanoclaw/.env | cut -d= -f2)
curl -s -X POST "https://api.kapso.ai/platform/v1/functions/88dfc487-0f8f-4bde-89b8-b67d84bfbd69/deploy" \
  -H "X-API-Key: $KAPSO_KEY" \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['data']['status'])"
```

Expected: `deploying`

- [ ] **Step 3: Wait for deployment, then verify**

```bash
KAPSO_KEY=$(grep KAPSO_API_KEY /share/nanoclaw/.env | cut -d= -f2)
sleep 8
curl -s "https://api.kapso.ai/platform/v1/functions/88dfc487-0f8f-4bde-89b8-b67d84bfbd69" \
  -H "X-API-Key: $KAPSO_KEY" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print('status:', d['status'])"
```

Expected: `status: deployed`

- [ ] **Step 4: Test all four cases**

```bash
KAPSO_KEY=$(grep KAPSO_API_KEY /share/nanoclaw/.env | cut -d= -f2)
BASE="https://api.kapso.ai/platform/v1/functions/88dfc487-0f8f-4bde-89b8-b67d84bfbd69/invoke"
EDGES='["replied","no_reply","nudge_done"]'

echo "=== inbound replied → replied + retry_count=0 ==="
curl -s -X POST "$BASE" -H "X-API-Key: $KAPSO_KEY" -H "Content-Type: application/json" \
  -d "{\"available_edges\":$EDGES,\"execution_context\":{\"context\":{\"agent_last_message\":\"היי\"},\"vars\":{}}}"

echo ""
echo "=== silent failure → no_reply ==="
curl -s -X POST "$BASE" -H "X-API-Key: $KAPSO_KEY" -H "Content-Type: application/json" \
  -d "{\"available_edges\":$EDGES,\"execution_context\":{\"context\":{\"agent_last_message\":null},\"vars\":{}}}"

echo ""
echo "=== nudge replied → nudge_done + retry_count=0 ==="
curl -s -X POST "$BASE" -H "X-API-Key: $KAPSO_KEY" -H "Content-Type: application/json" \
  -d "{\"available_edges\":$EDGES,\"execution_context\":{\"context\":{\"agent_last_message\":\"בוקר טוב\"},\"vars\":{\"nudge_intent\":\"check morning workout\"}}}"

echo ""
echo "=== nudge silent → no_reply ==="
curl -s -X POST "$BASE" -H "X-API-Key: $KAPSO_KEY" -H "Content-Type: application/json" \
  -d "{\"available_edges\":$EDGES,\"execution_context\":{\"context\":{\"agent_last_message\":null},\"vars\":{\"nudge_intent\":\"check morning workout\"}}}"
```

Expected output (one per line):
```
{"vars":{"retry_count":0},"next_edge":"replied"}
{"next_edge":"no_reply"}
{"vars":{"retry_count":0},"next_edge":"nudge_done"}
{"next_edge":"no_reply"}
```

- [ ] **Step 5: Commit**

```bash
git commit --allow-empty -m "feat(fitbot): update fitbot-reply-check with nudge_done edge and retry_count reset"
```

---

### Task 2: Create and deploy fitbot-load-state function

**Files:** New Kapso function

Calls the Supabase `fitbot-state` function from a Kapso Cloudflare Worker. Detects nudge vs inbound by checking `vars.nudge_intent`. Saves result to `vars.user_state`.

- [ ] **Step 1: Create the function**

```bash
KAPSO_KEY=$(grep KAPSO_API_KEY /share/nanoclaw/.env | cut -d= -f2)
curl -s -X POST "https://api.kapso.ai/platform/v1/functions" \
  -H "X-API-Key: $KAPSO_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "function": {
      "name": "fitbot-load-state",
      "description": "Loads user state from Supabase fitbot-state before each agent turn. Auto-detects nudge vs inbound from nudge_intent variable.",
      "code": "async function handler(request, env) {\n  const body = await request.json();\n  const context = body.execution_context?.context || {};\n  const vars = body.execution_context?.vars || {};\n\n  const phone = context.phone_number;\n  const trigger = vars.nudge_intent ? \"nudge\" : \"inbound\";\n\n  const response = await fetch(\"https://iejvqtvnrthvhxemonlz.supabase.co/functions/v1/fitbot-state\", {\n    method: \"POST\",\n    headers: {\n      \"Content-Type\": \"application/json\",\n      \"x-fitbot-op\": \"get\",\n      \"x-fitbot-phone\": phone,\n      \"x-fitbot-trigger\": trigger\n    },\n    body: JSON.stringify({})\n  });\n\n  const data = await response.json();\n\n  return new Response(JSON.stringify({\n    vars: { user_state: data }\n  }), {\n    headers: { \"Content-Type\": \"application/json\" }\n  });\n}"
    }
  }' | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print('id:', d['id'])"
```

Expected: prints the new function UUID — **save this as `LOAD_STATE_FN_ID`**.

- [ ] **Step 2: Deploy**

```bash
KAPSO_KEY=$(grep KAPSO_API_KEY /share/nanoclaw/.env | cut -d= -f2)
LOAD_STATE_FN_ID=<paste-id-from-step-1>
curl -s -X POST "https://api.kapso.ai/platform/v1/functions/$LOAD_STATE_FN_ID/deploy" \
  -H "X-API-Key: $KAPSO_KEY" \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['status'])"
```

Expected: `deploying`

- [ ] **Step 3: Wait and verify deployed**

```bash
KAPSO_KEY=$(grep KAPSO_API_KEY /share/nanoclaw/.env | cut -d= -f2)
sleep 8
curl -s "https://api.kapso.ai/platform/v1/functions/$LOAD_STATE_FN_ID" \
  -H "X-API-Key: $KAPSO_KEY" | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print('status:', d['status'])"
```

Expected: `status: deployed`

- [ ] **Step 4: Smoke-test with Ohav's phone number**

```bash
KAPSO_KEY=$(grep KAPSO_API_KEY /share/nanoclaw/.env | cut -d= -f2)
curl -s -X POST "https://api.kapso.ai/platform/v1/functions/$LOAD_STATE_FN_ID/invoke" \
  -H "X-API-Key: $KAPSO_KEY" \
  -H "Content-Type: application/json" \
  -d '{"execution_context":{"context":{"phone_number":"972544696057"},"vars":{}}}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('vars',{}).get('user_state',{}); print('onboarded:', s.get('state',{}).get('onboarded'))"
```

Expected: `onboarded: False` (Ohav's onboarded field)

- [ ] **Step 5: Commit**

```bash
git commit --allow-empty -m "feat(fitbot): create fitbot-load-state Kapso function"
```

---

### Task 3: Create and deploy fitbot-retry-handler function

**Files:** New Kapso function

Increments `retry_count` and routes to `retry` (≤ 2) or `fallback` (> 2). Returns updated `retry_count` in vars so Kapso persists it.

- [ ] **Step 1: Create the function**

```bash
KAPSO_KEY=$(grep KAPSO_API_KEY /share/nanoclaw/.env | cut -d= -f2)
curl -s -X POST "https://api.kapso.ai/platform/v1/functions" \
  -H "X-API-Key: $KAPSO_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "function": {
      "name": "fitbot-retry-handler",
      "description": "Increments retry_count on silent agent failure. Routes to retry edge if count <= 2, fallback edge otherwise.",
      "code": "async function handler(request, env) {\n  const body = await request.json();\n  const availableEdges = body.available_edges || [];\n  const vars = body.execution_context?.vars || {};\n\n  const currentCount = parseInt(vars.retry_count || \"0\", 10);\n  const newCount = currentCount + 1;\n  const nextEdge = newCount <= 2 ? \"retry\" : \"fallback\";\n\n  return new Response(JSON.stringify({\n    vars: { retry_count: newCount },\n    next_edge: availableEdges.includes(nextEdge) ? nextEdge : (availableEdges[0] || \"fallback\")\n  }), {\n    headers: { \"Content-Type\": \"application/json\" }\n  });\n}"
    }
  }' | python3 -c "import sys,json; d=json.load(sys.stdin)['data']; print('id:', d['id'])"
```

Expected: prints the new function UUID — **save this as `RETRY_HANDLER_FN_ID`**.

- [ ] **Step 2: Deploy**

```bash
KAPSO_KEY=$(grep KAPSO_API_KEY /share/nanoclaw/.env | cut -d= -f2)
RETRY_HANDLER_FN_ID=<paste-id-from-step-1>
curl -s -X POST "https://api.kapso.ai/platform/v1/functions/$RETRY_HANDLER_FN_ID/deploy" \
  -H "X-API-Key: $KAPSO_KEY" \
  -H "Content-Type: application/json" \
  -d '{}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['status'])"
```

Expected: `deploying`

- [ ] **Step 3: Wait and verify**

```bash
sleep 8
KAPSO_KEY=$(grep KAPSO_API_KEY /share/nanoclaw/.env | cut -d= -f2)
curl -s "https://api.kapso.ai/platform/v1/functions/$RETRY_HANDLER_FN_ID" \
  -H "X-API-Key: $KAPSO_KEY" | python3 -c "import sys,json; print('status:', json.load(sys.stdin)['data']['status'])"
```

Expected: `status: deployed`

- [ ] **Step 4: Test retry escalation**

```bash
KAPSO_KEY=$(grep KAPSO_API_KEY /share/nanoclaw/.env | cut -d= -f2)
BASE="https://api.kapso.ai/platform/v1/functions/$RETRY_HANDLER_FN_ID/invoke"
EDGES='["retry","fallback"]'

echo "=== first failure (count=0→1) → retry ==="
curl -s -X POST "$BASE" -H "X-API-Key: $KAPSO_KEY" -H "Content-Type: application/json" \
  -d "{\"available_edges\":$EDGES,\"execution_context\":{\"vars\":{\"retry_count\":0}}}"

echo ""
echo "=== second failure (count=1→2) → retry ==="
curl -s -X POST "$BASE" -H "X-API-Key: $KAPSO_KEY" -H "Content-Type: application/json" \
  -d "{\"available_edges\":$EDGES,\"execution_context\":{\"vars\":{\"retry_count\":1}}}"

echo ""
echo "=== third failure (count=2→3) → fallback ==="
curl -s -X POST "$BASE" -H "X-API-Key: $KAPSO_KEY" -H "Content-Type: application/json" \
  -d "{\"available_edges\":$EDGES,\"execution_context\":{\"vars\":{\"retry_count\":2}}}"
```

Expected:
```
{"vars":{"retry_count":1},"next_edge":"retry"}
{"vars":{"retry_count":2},"next_edge":"retry"}
{"vars":{"retry_count":3},"next_edge":"fallback"}
```

- [ ] **Step 5: Commit**

```bash
git commit --allow-empty -m "feat(fitbot): create fitbot-retry-handler Kapso function"
```

---

### Task 4: Apply new workflow definition

**Files:** Kapso workflow `a58ad8cc-d125-47fa-8481-b717fb56993d`

Replaces the entire workflow graph. New graph: `start → load_state → agent → decide_reply_check → [replied: wait_for_response → load_state loop | no_reply: decide_retry → [retry: load_state | fallback: send_fallback → wait_for_response] | nudge_done: END]`.

The agent node is updated: `enter_waiting` removed from `enabled_default_tools`, `state_get` removed from `flow_agent_webhooks`, system prompt updated.

- [ ] **Step 1: Fetch current lock_version**

```bash
KAPSO_KEY=$(grep KAPSO_API_KEY /share/nanoclaw/.env | cut -d= -f2)
curl -s "https://api.kapso.ai/platform/v1/workflows/a58ad8cc-d125-47fa-8481-b717fb56993d/definition" \
  -H "X-API-Key: $KAPSO_KEY" | python3 -c "import sys,json; print('lock_version:', json.load(sys.stdin)['data']['lock_version'])"
```

Note the `lock_version` — use it in the next step.

- [ ] **Step 2: Write the PATCH script to a file**

Create `/tmp/patch_fitbot_workflow.py` with the following content. Replace `LOAD_STATE_FN_ID` and `RETRY_HANDLER_FN_ID` with the UUIDs from Tasks 2 and 3, and `LOCK_VERSION` with the value from Step 1.

```python
#!/usr/bin/env python3
import json, subprocess, sys

KAPSO_KEY = subprocess.check_output(
    "grep KAPSO_API_KEY /share/nanoclaw/.env | cut -d= -f2", shell=True
).decode().strip()

WORKFLOW_ID = "a58ad8cc-d125-47fa-8481-b717fb56993d"
LOCK_VERSION = <REPLACE_WITH_LOCK_VERSION>
LOAD_STATE_FN_ID = "<REPLACE_WITH_LOAD_STATE_FN_ID>"
RETRY_HANDLER_FN_ID = "<REPLACE_WITH_RETRY_HANDLER_FN_ID>"
REPLY_CHECK_FN_ID = "88dfc487-0f8f-4bde-89b8-b67d84bfbd69"

SYSTEM_PROMPT = """You are פיט בוט (Fit Bot) — a personal trainer and friend chatting on
WhatsApp, conversing in colloquial everyday Israeli Hebrew. You talk with
one user at a time. **All your output to the user is in Hebrew.** These
instructions are in English for your own benefit; every message you send
must be natural Israeli Hebrew.

# Identity
- A personal trainer and friend, not software.
- Direct, warm, non-judgmental.
- Knowledgeable in fitness and nutrition.
- Listens when needed, pushes when needed.
- Acknowledges limits — you're in beta, you can be wrong.

# Memory protocol
Your user state is pre-loaded in `{{user_state}}` before you start.
Treat it as ground truth. If conversation history contradicts it, the state wins.
- If `{{user_state}}.state.onboarded === true`, skip the intake greeting entirely.
  Behave as a returning-user session, even if this looks like a fresh thread to you.
- **Before `complete_task`**, call `state_save` with a patch of anything that changed this turn:
  - New onboarding fields (name → `notes`, age, sex, goal, equipment,
    constraints, dietary_constraints, weekly_days)
  - `onboarded: true` the moment intake is complete
  - Updated `weekly_plan` whenever you propose or adjust a program
  - `last_checkin_iso` (ISO timestamp) on any check-in or workout report
  - Bumped `streak_days` on consecutive check-ins
  - `next_nudge_at` and `next_nudge_intent` (see Proactive nudges below)
- Pass `patch_json` as a plain JSON object — e.g. `{"goal": "לרדת 5 קג", "onboarded": true}`. Not a string.
- The `notes` field is your free-form scratchpad. Keep it short.
- `state_save` silently ignores unknown keys.

# Reading the chat
Based on `{{user_state}}`, scan recent conversation history for what's new
since `last_user_message_at` or what's relevant to the user's most recent message.
- The opening message on this number may have been sent **manually by the
  founder from the WhatsApp Business app** to start the conversation. Treat such outbound messages as
  yours — do NOT re-introduce yourself, do NOT repeat the opener.
- Don't re-ask anything that's already filled in `{{user_state}}`.
- Your replies are continuations of the same chat, not fresh sessions.

# Match the user's energy
This is non-negotiable. Read the user's last message before replying:
- **Length:** if they wrote two words, you write two words. If they wrote
  a paragraph, a short paragraph back is fine. Don't reply to "יו" with three sentences.
- **Register:** chill/slangy → reply chill. Formal → slightly more formal. They set the tone, not you.
- **Punctuation/emoji:** if they don't use them, you don't. If they drop one emoji, one is fine.
- **Pace:** if they're warming up slowly, don't drag them into a form.
  If they're moving fast and direct, don't slow them down with pleasantries.
A friend who responds in your register feels real. A bot that always replies the same length and tone feels exactly like a bot.

# Writing style
- Everyday Israeli Hebrew, like messages to a friend who knows the field.
- Short. 1–3 sentences most of the time. Longer only when warranted.
- No markdown. No bold. No headings. No numbered lists (unless it's a list of exercises or a meal).
- At most one emoji per message, only when natural.
- Short replies like "סבבה" / "אחלה" / "סגור" / "מעולה" — **no period at the end.** Periods on short WhatsApp replies feel cold.
- **No em dashes (—)** in messages to the user. Classic AI tell. Use commas, short separate sentences, or a line break instead.
- A touch of warmth/enthusiasm only when it genuinely fits ("יאללה!", "זה בדיוק זה", "רואים שאתה רציני"). Don't fake it.
- Address the user in Hebrew **plural** ("אתם", "שלכם", "תגידו") UNTIL you know their gender.
  Once you know it, switch to the matching singular for every subsequent message and never revert.
  Male: "אתה / שלך / לך / תגיד / מתאמן". Female: "את / שלך / לך / תגידי / מתאמנת".
  Common slip-ups to avoid: "נוח לכם" (should be "נוח לך"), using "אתם"/"תגידו" after gender is known.
- No flattery ("איזו שאלה מצוינת!"). No unnecessary disclaimers. Brief redirect to a doctor only when actually critical.

# Onboarding
On the user's first real reply, your job is to gather their basic info
through natural conversation. **Don't fire a form at them.** If they
opened with a casual "יו" / "שלום" / "מה קורה" — match the energy. One
warm sentence back, then ask their **name** (combine warmly: "מה השם?" not "מה המטרה שלך?").

Fields to collect, in roughly this order:
1. שם (name)
2. גיל (age)
3. מטרה (goal)
4. שגרה נוכחית / רמה (current routine / level — what they do now, how often)
5. ציוד (equipment — gym / home with weights / bodyweight only / other)
6. פציעות / מגבלות (injuries or limits)
7. דברים נוספים — before closing onboarding always ask: "משהו נוסף שחשוב שאדע על המסע שלך בכושר?"

Onboarding rules:
- One question at a time. Combining two short related questions is fine (e.g., name + age). Not a form.
- If they answer multiple things at once, continue with what's missing.
- Explain WHY once at the start ("אני שואל כמה דברים קצרים כדי לבנות
  תוכנית שמתאימה לך, לא תבנית מהאינטרנט"). Add a brief reason when asking
  equipment or injuries — one natural sentence, not a disclaimer. If they push back,
  re-explain in one line and continue.
- **Inferring gender from the name:** when the user gives their name,
  set gender silently and switch pronouns starting from the next reply:
  - Clearly gendered Hebrew name (ירון, דני, אבישי, יוסי, מיכל, שירה, יעל, עידן…) → infer and switch.
  - Ambiguous name (גל, טל, יובל, אורי, עדן, שחר, נועם…) → ask gently:
    "סליחה שאני שואל, את/ה זכר או נקבה? זה רק כדי לפנות אליך נכון."
  - When in doubt, ask rather than guess.

When all fields are collected, close with a short summary + warm invitation to open dialogue.
**Don't announce a schedule** like "אני אכתוב לך כל בוקר בשמונה" — it reads like a doctor's appointment.
Example (adapt to gender and details):
"סגור לינה, אני איתך. תכתבי לי סביב האימונים והארוחות — לשאול, לשתף, להתייעץ. מתחילים 💪"

# Coaching mode (after onboarding)
- Build a personalized program from the intake. Adapt over time based on adherence and feedback.
- **Meal photos / food logs:** when you receive an image, call `ask_about_file` with a question like
  "Estimate calories, protein, carbs, fat for this meal. Be specific about portion assumptions."
  Reply format: `[description]: בערך X קלוריות, Y חלבון. [one observation tied to their goal].`
  Rules: ±20% accuracy is fine. Never "אתה צריך לאכול X" — descriptive, not prescriptive.
  One observation, not a lecture. Not sure what's on the plate? Ask.
- **General fitness/nutrition questions:** answer short and specific. Don't drift into lectures.
- **Workout / program / recipe requests:** adapt to their equipment, level, and injuries.
  Render in WhatsApp language, not like a PDF training program.
- **Emotional moments** (frustration, "I give up", low mood): listen first.
  Don't jump into motivation. One question that shows you understood. Encouragement only if they want it.
  Instead of "אל תוותר, אתה יכול!" — "משהו קרה היום? ספר לי."
- **Style change requests:** "הבנתי, עוברים ל-[X]. תגיד אם זה עובד." Adapt from that point.
- **Out of scope:** real medical / mental-health crisis → briefly redirect, then move on.
  Unrelated questions → short answer + pivot back to fitness/nutrition.

# Voice notes
Voice notes are auto-transcribed by Kapso — treat them identically to typed messages.
If the transcript is clearly garbled, ask: "רגע, לא בטוח שתפסתי. תכתוב/תשלח שוב?"

# Bot self-disclosure
If the user asks "אתה בוט?" — be honest, briefly:
"כן, אני AI שעוזר לך עם כושר ותזונה. בן אדם עוקב אחרי השיחה בבטא הזו."
Don't open a philosophical thread. Pivot back.

# Proactive nudges (the 24h window strategy)
WhatsApp gives us 24 hours after a user's message to send any free-form reply.
Outside that window we'd need paid template messages. Stay inside it: **you decide when to ping next, every turn.**

Before `complete_task`, set two fields on `state_save`:
- `next_nudge_at`: ISO-8601 UTC timestamp for when the ping should fire, or `null` to cancel.
- `next_nudge_intent`: one short line describing what to say at that time.

Pick the time from what the user just told you, in their voice:
- "אעשה את האימון מחר בבוקר" → tomorrow ~11:00 user-local (convert to UTC), intent: "check if morning workout happened"
- "מתאמן ב-7" → today 19:30 user-local, intent: "mid-workout encouragement / form check"
- "תודה, יום נעים" → `next_nudge_at: null` (don't push, let them come back)
- Mid-onboarding pause: short ping ~2-4h later, intent: "gentle nudge to finish onboarding"
- No specific signal but engaged: next morning ~10:00 or evening ~20:00. Don't ping more than once per ~12h.

User timezone: Israel (Asia/Jerusalem) unless you've learned otherwise. The server stores UTC; convert.

**When you ARE the nudge** (your execution started with `{{nudge_intent}}` set, no inbound user message):
- Read `{{user_state}}` and `{{nudge_intent}}`.
- Send ONE short Hebrew message that fits the intent and the user's voice. Don't open a 3-message monologue.
- Set the next `next_nudge_at` based on whether you expect a reply.
- End with `complete_task`.

# Tool / turn discipline
Every turn ends with `state_save` then `complete_task`. No exceptions —
at minimum bump `next_nudge_at` or set it to `null`.
Never invent products, links, or apps. Coaching is text + photos only.

# Golden rules
- Short beats long.
- Specific beats general.
- Listening beats preaching.
- Don't invent numbers. "בערך 400 קלוריות" beats "412 קלוריות"."""

# Condition UUIDs for decide nodes (stable identifiers)
COND_REPLIED    = "f1a00001-0001-0001-0001-000000000001"
COND_NO_REPLY   = "f1a00002-0002-0002-0002-000000000002"
COND_NUDGE_DONE = "f1a00003-0003-0003-0003-000000000003"
COND_RETRY      = "f1a00004-0004-0004-0004-000000000004"
COND_FALLBACK   = "f1a00005-0005-0005-0005-000000000005"

# Edge UUIDs
E_START_LOAD         = "e0000001-0000-0000-0000-000000000001"
E_LOAD_AGENT         = "e0000002-0000-0000-0000-000000000002"
E_AGENT_REPLY_CHECK  = "e0000003-0000-0000-0000-000000000003"
E_REPLIED_WAIT       = "e0000004-0000-0000-0000-000000000004"
E_NOREPLY_RETRY_D    = "e0000005-0000-0000-0000-000000000005"
E_WAIT_LOAD          = "e0000006-0000-0000-0000-000000000006"
E_RETRY_LOAD         = "e0000007-0000-0000-0000-000000000007"
E_FALLBACK_SEND      = "e0000008-0000-0000-0000-000000000008"
E_SEND_WAIT          = "e0000009-0000-0000-0000-000000000009"

definition = {
    "nodes": [
        {
            "id": "start",
            "type": "flow-node",
            "position": {"x": 100, "y": 300},
            "data": {"node_type": "start", "config": {}, "display_name": "Start"}
        },
        {
            "id": "load_state",
            "type": "flow-node",
            "position": {"x": 320, "y": 300},
            "data": {
                "node_type": "function",
                "config": {
                    "function_id": LOAD_STATE_FN_ID,
                    "save_response_to": None
                },
                "display_name": "Load State"
            }
        },
        {
            "id": "agent_1777297133407",
            "type": "flow-node",
            "position": {"x": 540, "y": 300},
            "data": {
                "node_type": "agent",
                "config": {
                    "system_prompt": SYSTEM_PROMPT,
                    "provider_model_id": "229158bf-bef0-44cc-9242-80a55edae691",
                    "provider_model_name": "google/gemini-3.1-pro-preview",
                    "temperature": "0.3",
                    "max_iterations": 40,
                    "max_tokens": 8192,
                    "reasoning_effort": None,
                    "observer_prompt_mode": "analysis_only",
                    "enabled_default_tools": [
                        "send_notification_to_user",
                        "send_media",
                        "get_execution_metadata",
                        "get_whatsapp_context",
                        "get_current_datetime",
                        "save_variable",
                        "get_variable",
                        "ask_about_file",
                        "complete_task",
                        "handoff_to_human"
                    ],
                    "sandbox_enabled": False,
                    "sandbox_network_mode": "allow_all",
                    "sandbox_allowed_outbound_hosts": [],
                    "flow_agent_function_tools": [],
                    "flow_agent_app_integration_tools": [],
                    "flow_agent_webhooks": [
                        {
                            "name": "state_save",
                            "description": "Persist a partial update to this user's FitBot state. Call this BEFORE complete_task on every turn. Pass patch_json as a plain JSON object (not a string). Allowed keys: onboarded, goal, current_weight, target_weight, height_cm, age, sex, weekly_days, equipment, constraints, dietary_constraints, weekly_plan, last_checkin_iso, streak_days, notes, next_nudge_at (ISO-8601 UTC or null), next_nudge_intent (short string or null). Unknown keys are silently ignored.",
                            "url": "https://iejvqtvnrthvhxemonlz.supabase.co/functions/v1/fitbot-state",
                            "http_method": "POST",
                            "headers": {
                                "x-fitbot-op": "save",
                                "Content-Type": "application/json",
                                "x-fitbot-phone": "{{context.phone_number}}"
                            },
                            "body": {},
                            "body_schema": {
                                "type": "object",
                                "required": ["patch_json"],
                                "properties": {
                                    "patch_json": {
                                        "type": "object",
                                        "description": "Fields to merge into the user state row."
                                    }
                                }
                            },
                            "jmespath_query": None,
                            "ai_field_config": {}
                        }
                    ],
                    "flow_agent_knowledge_bases": [],
                    "flow_agent_mcp_servers": [],
                    "flow_agent_resources": []
                },
                "display_name": "FitBot Agent"
            }
        },
        {
            "id": "decide_reply_check",
            "type": "flow-node",
            "position": {"x": 760, "y": 300},
            "data": {
                "node_type": "decide",
                "config": {
                    "decision_type": "function",
                    "function_id": REPLY_CHECK_FN_ID,
                    "function_name": "fitbot-reply-check",
                    "conditions": [
                        {"id": COND_REPLIED,    "label": "replied",    "description": "Agent sent a message this turn"},
                        {"id": COND_NO_REPLY,   "label": "no_reply",   "description": "Agent produced no output (0 tokens)"},
                        {"id": COND_NUDGE_DONE, "label": "nudge_done", "description": "Nudge execution completed successfully"}
                    ],
                    "llm_configuration": {}
                },
                "display_name": "Did Agent Reply?"
            }
        },
        {
            "id": "wait_for_response",
            "type": "flow-node",
            "position": {"x": 980, "y": 160},
            "data": {
                "node_type": "wait_for_response",
                "config": {
                    "has_timeout": False,
                    "timeout_seconds": None,
                    "save_response_to": None
                },
                "display_name": "Wait for User"
            }
        },
        {
            "id": "decide_retry",
            "type": "flow-node",
            "position": {"x": 980, "y": 440},
            "data": {
                "node_type": "decide",
                "config": {
                    "decision_type": "function",
                    "function_id": RETRY_HANDLER_FN_ID,
                    "function_name": "fitbot-retry-handler",
                    "conditions": [
                        {"id": COND_RETRY,    "label": "retry",    "description": "retry_count <= 2, retry the agent"},
                        {"id": COND_FALLBACK, "label": "fallback", "description": "retry_count > 2, send fallback message"}
                    ],
                    "llm_configuration": {}
                },
                "display_name": "Retry or Fallback?"
            }
        },
        {
            "id": "send_fallback",
            "type": "flow-node",
            "position": {"x": 1200, "y": 560},
            "data": {
                "node_type": "send_text",
                "config": {
                    "message": "קרתה תקלה, שלח לי הודעה חדשה ואמשיך מכאן"
                },
                "display_name": "Send Fallback"
            }
        }
    ],
    "edges": [
        {"id": E_START_LOAD,        "source": "start",              "target": "load_state",          "label": "next",       "type": "default", "flow_condition_id": None},
        {"id": E_LOAD_AGENT,        "source": "load_state",         "target": "agent_1777297133407", "label": "next",       "type": "default", "flow_condition_id": None},
        {"id": E_AGENT_REPLY_CHECK, "source": "agent_1777297133407","target": "decide_reply_check",  "label": "next",       "type": "default", "flow_condition_id": None},
        {"id": E_REPLIED_WAIT,      "source": "decide_reply_check", "target": "wait_for_response",   "label": "replied",    "type": "default", "flow_condition_id": COND_REPLIED},
        {"id": E_NOREPLY_RETRY_D,   "source": "decide_reply_check", "target": "decide_retry",        "label": "no_reply",   "type": "default", "flow_condition_id": COND_NO_REPLY},
        {"id": E_WAIT_LOAD,         "source": "wait_for_response",  "target": "load_state",          "label": "next",       "type": "default", "flow_condition_id": None},
        {"id": E_RETRY_LOAD,        "source": "decide_retry",       "target": "load_state",          "label": "retry",      "type": "default", "flow_condition_id": COND_RETRY},
        {"id": E_FALLBACK_SEND,     "source": "decide_retry",       "target": "send_fallback",       "label": "fallback",   "type": "default", "flow_condition_id": COND_FALLBACK},
        {"id": E_SEND_WAIT,         "source": "send_fallback",      "target": "wait_for_response",   "label": "next",       "type": "default", "flow_condition_id": None}
    ]
}

payload = {
    "workflow": {
        "lock_version": LOCK_VERSION,
        "definition": definition
    }
}

import urllib.request
req = urllib.request.Request(
    f"https://api.kapso.ai/platform/v1/workflows/{WORKFLOW_ID}",
    data=json.dumps(payload).encode(),
    headers={
        "X-API-Key": KAPSO_KEY,
        "Content-Type": "application/json"
    },
    method="PATCH"
)
with urllib.request.urlopen(req) as resp:
    result = json.loads(resp.read())
    print("lock_version after:", result["data"]["lock_version"])
    print("node count:", len(result["data"]["definition"]["nodes"]))
    print("edge count:", len(result["data"]["definition"]["edges"]))
```

- [ ] **Step 3: Run the PATCH script**

```bash
python3 /tmp/patch_fitbot_workflow.py
```

Expected:
```
lock_version after: <previous+1>
node count: 7
edge count: 9
```

If you get a 409 conflict, re-fetch the lock_version (Step 1) and update the script.

- [ ] **Step 4: Commit**

```bash
git commit --allow-empty -m "feat(fitbot): apply new workflow graph with load_state + retry loop"
```

---

### Task 5: Verify workflow definition and smoke-test

**Files:** Kapso workflow definition (read-only verification)

- [ ] **Step 1: Verify all nodes are present with correct types**

```bash
KAPSO_KEY=$(grep KAPSO_API_KEY /share/nanoclaw/.env | cut -d= -f2)
curl -s "https://api.kapso.ai/platform/v1/workflows/a58ad8cc-d125-47fa-8481-b717fb56993d/definition" \
  -H "X-API-Key: $KAPSO_KEY" | python3 -c "
import sys, json
d = json.load(sys.stdin)['data']
print('lock_version:', d['lock_version'])
for n in d['definition']['nodes']:
    print(f\"  node {n['id']}: {n['data']['node_type']}\")
print('edges:')
for e in d['definition']['edges']:
    print(f\"  {e['source']} --[{e['label']}]--> {e['target']}\")
"
```

Expected output:
```
lock_version: <N>
  node start: start
  node load_state: function
  node agent_1777297133407: agent
  node decide_reply_check: decide
  node wait_for_response: wait_for_response
  node decide_retry: decide
  node send_fallback: send_text
edges:
  start --[next]--> load_state
  load_state --[next]--> agent_1777297133407
  agent_1777297133407 --[next]--> decide_reply_check
  decide_reply_check --[replied]--> wait_for_response
  decide_reply_check --[no_reply]--> decide_retry
  wait_for_response --[next]--> load_state
  decide_retry --[retry]--> load_state
  decide_retry --[fallback]--> send_fallback
  send_fallback --[next]--> wait_for_response
```

- [ ] **Step 2: Verify agent tools — enter_waiting is absent, state_get is absent**

```bash
KAPSO_KEY=$(grep KAPSO_API_KEY /share/nanoclaw/.env | cut -d= -f2)
curl -s "https://api.kapso.ai/platform/v1/workflows/a58ad8cc-d125-47fa-8481-b717fb56993d/definition" \
  -H "X-API-Key: $KAPSO_KEY" | python3 -c "
import sys, json
d = json.load(sys.stdin)['data']
agent = next(n for n in d['definition']['nodes'] if n['id'] == 'agent_1777297133407')
cfg = agent['data']['config']
tools = cfg['enabled_default_tools']
webhooks = [w['name'] for w in cfg['flow_agent_webhooks']]
print('tools:', tools)
print('webhooks:', webhooks)
assert 'enter_waiting' not in tools, 'FAIL: enter_waiting still in tools'
assert 'state_get' not in webhooks, 'FAIL: state_get still in webhooks'
assert 'complete_task' in tools, 'FAIL: complete_task missing from tools'
assert 'state_save' in webhooks, 'FAIL: state_save missing from webhooks'
print('OK: all checks passed')
"
```

Expected:
```
tools: ['send_notification_to_user', 'send_media', 'get_execution_metadata', 'get_whatsapp_context', 'get_current_datetime', 'save_variable', 'get_variable', 'ask_about_file', 'complete_task', 'handoff_to_human']
webhooks: ['state_save']
OK: all checks passed
```

- [ ] **Step 3: Verify system prompt contains new protocol, not old**

```bash
KAPSO_KEY=$(grep KAPSO_API_KEY /share/nanoclaw/.env | cut -d= -f2)
curl -s "https://api.kapso.ai/platform/v1/workflows/a58ad8cc-d125-47fa-8481-b717fb56993d/definition" \
  -H "X-API-Key: $KAPSO_KEY" | python3 -c "
import sys, json
d = json.load(sys.stdin)['data']
agent = next(n for n in d['definition']['nodes'] if n['id'] == 'agent_1777297133407')
prompt = agent['data']['config']['system_prompt']
assert 'state_get' not in prompt, 'FAIL: state_get still in prompt'
assert 'enter_waiting' not in prompt, 'FAIL: enter_waiting still in prompt'
assert '{{user_state}}' in prompt, 'FAIL: {{user_state}} missing from prompt'
assert 'complete_task' in prompt, 'FAIL: complete_task missing from prompt'
print('OK: prompt verified')
print('Word count:', len(prompt.split()))
"
```

Expected:
```
OK: prompt verified
Word count: ~1450
```

- [ ] **Step 4: Start a test execution and check events show load_state firing**

```bash
KAPSO_KEY=$(grep KAPSO_API_KEY /share/nanoclaw/.env | cut -d= -f2)
# Start a test execution on a non-real number to trigger the flow without messaging a user
EXEC=$(curl -s -X POST "https://api.kapso.ai/platform/v1/workflows/a58ad8cc-d125-47fa-8481-b717fb56993d/executions" \
  -H "X-API-Key: $KAPSO_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_execution": {
      "phone_number": "+972500000001",
      "phone_number_id": "1013290868544034",
      "variables": {}
    }
  }')
EXEC_ID=$(echo $EXEC | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['id'])")
echo "Execution ID: $EXEC_ID"
sleep 10
curl -s "https://api.kapso.ai/platform/v1/workflow_executions/$EXEC_ID/events" \
  -H "X-API-Key: $KAPSO_KEY" | python3 -c "
import sys, json
events = json.load(sys.stdin)['data']
for e in reversed(events):
    step = (e.get('step') or {}).get('identifier', '-')
    print(f\"{e['event_type']:40s} step={step}\")
"
```

Expected: events showing `step_entered` for `load_state`, then `agent_step_started` for the agent. The execution should end up in `waiting` status at `wait_for_response` (after the agent calls `complete_task` and the reply check routes to `replied`).

- [ ] **Step 5: Final commit**

```bash
git add docs/superpowers/specs/2026-04-28-fitbot-workflow-reliability-design.md \
        docs/superpowers/plans/2026-04-28-fitbot-workflow-reliability.md
git commit -m "feat(fitbot): implement workflow reliability — load_state node, retry loop, updated system prompt

- fitbot-reply-check updated with nudge_done edge + retry_count reset
- fitbot-load-state function created and deployed
- fitbot-retry-handler function created and deployed
- workflow graph rebuilt: start→load_state→agent→reply_check→retry/wait loop
- agent node: enter_waiting + state_get removed, complete_task only
- system prompt: state_get removed, {{user_state}} pattern, ~330 words trimmed"
```

---

## Self-review checklist

**Spec coverage:**
- ✅ OQ1 — reply detection via Kapso function: Tasks 1, 4 (decide_reply_check node)
- ✅ OQ2 — nudge entrypoint: handled by fitbot-reply-check returning `nudge_done` → no outgoing edge → execution ends
- ✅ OQ3 — 2 retries: fitbot-retry-handler allows count ≤ 2 → retry, count > 2 → fallback
- ✅ load_state node: Task 2 + Task 4 (load_state function node before agent)
- ✅ remove enter_waiting: Task 4 agent config (`enabled_default_tools`)
- ✅ remove state_get: Task 4 agent config (`flow_agent_webhooks`)
- ✅ system prompt update: Task 4 (SYSTEM_PROMPT in patch script)
- ✅ fallback message: Task 4 (`send_fallback` node with Hebrew text)
- ✅ retry_count reset on success: Task 1 (fitbot-reply-check returns `vars.retry_count=0`)

**Placeholder scan:** None found. All steps include actual code/commands/expected output.

**Type consistency:** `LOAD_STATE_FN_ID` and `RETRY_HANDLER_FN_ID` are introduced in Tasks 2/3 and used in Task 4 — implementer must substitute actual UUIDs. This is intentional, not a placeholder gap.
