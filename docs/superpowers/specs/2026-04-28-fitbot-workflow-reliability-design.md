# FitBot Workflow Reliability — Design Spec

**Date:** 2026-04-28  
**Status:** Approved for implementation  
**Context:** FitBot runs on Kapso. The agent node uses `google/gemini-3.1-pro-preview` via OpenRouter. Gemini occasionally produces 0 output tokens — a silent failure where the model is called, generates nothing, and Kapso implicitly calls `enter_waiting`. The user gets no reply and both sides are deadlocked waiting for each other.

**Root cause confirmed via execution events:** execution `59272d40` — `ask_about_file` returned successfully, model received 16,171 input tokens, produced 0 output tokens, `agent_last_message: null`, silent `enter_waiting`.

---

## Goals

1. Detect when the agent fails to reply in a turn
2. Retry the agent up to 2 times automatically
3. Send a Hebrew fallback message after exhausting retries
4. Load user state deterministically (not model-dependent)
5. Reduce per-turn token count to lower failure probability

---

## Architecture

### Current flow

```
Start → [Agent: enter_waiting] ←→ (user replies resume the same execution)
```

Single long-running execution, state loaded by the model calling `state_get` as its first tool action. Fragile: model can skip it (confirmed in the failing turn).

### New flow

```
[Start]
    ↓
[Webhook: load_state]  ← all agent invocations enter here
    ↓  saves {{user_state}}
[Agent: complete_task]
    ↓
[Decide: did agent reply?]
    ↓ yes                         ↓ no
[save retry_count=0]         [save retry_count++]
    ↓                              ↓
[Wait for Response]         [Decide: retry_count ≤ 2?]
    ↓ user responds             ↓ yes           ↓ no
[load_state]              [load_state]     [Send fallback]
    ↓                         ↓                  ↓
  [Agent]                  [Agent]         [save retry_count=0]
                                                  ↓
                                           [Wait for Response]
                                                  ↓ user responds
                                           [load_state]
                                                  ↓
                                               [Agent]
```

`load_state` is the single entry point before every agent invocation. All paths (cold start, retry, post-wait) go through it. State is always fresh before the agent runs, regardless of model behavior.

---

## Workflow node changes

### New node: load_state (Webhook)

Calls the existing `fitbot-state` Supabase function.

```
URL:     https://iejvqtvnrthvhxemonlz.supabase.co/functions/v1/fitbot-state
Method:  POST
Headers:
  x-fitbot-op:      get
  x-fitbot-phone:   {{context.phone_number}}
  x-fitbot-trigger: inbound
Body:    {}
Save result to variable: user_state
```

Placed before every agent invocation. Nudge executions (triggered via API, not inbound) bypass this node and pass `nudge_intent` directly.

### Agent node changes

- Remove `enter_waiting` from `enabled_default_tools`
- Remove `state_get` from `flow_agent_webhooks`
- Agent always ends with `complete_task`
- System prompt updated (see below)

### New node: decide (did agent reply?)

Uses a Kapso function or AI decide to evaluate `context.agent_last_message`:

```
Condition: context.agent_last_message is not null AND context.agent_last_message != ""
Branch "replied":    → save retry_count=0 → Wait for Response
Branch "no_reply":   → save retry_count++ → retry decide
```

`agent_last_message` is set by Kapso infrastructure from the `agent_message_sent` event — it is not model-controlled, making this check reliable.

### New node: retry decide

```
Condition: retry_count <= 2
Branch "retry":    → load_state → Agent
Branch "fallback": → Send fallback text → save retry_count=0 → Wait for Response
```

### New node: fallback text

```
קרתה תקלה, שלח לי הודעה חדשה ואמשיך מכאן
```

Short, natural Hebrew. No over-explanation.

### Variable: retry_count

Workflow variable. Initialised to `0`. Incremented on each silent failure. Reset to `0` on any successful reply.

---

## System prompt changes

### Memory protocol — replace state_get with variable read

**Remove:**
```
- **First action of every execution**: call `state_get`. No exceptions.
- Treat the returned `state` as ground truth. If conversation history
  contradicts it, the state wins.
```

**Replace with:**
```
Your user state is pre-loaded in `{{user_state}}` before you start.
Treat it as ground truth. If conversation history contradicts it, the state wins.
```

Update all downstream references from "returned state" to "`{{user_state}}`".

Remove from `state_save` instructions:
- The `ignored: [...]` paragraph — condense to: "`state_save` silently ignores unknown keys."
- The "Do NOT stringify it" line — move inline: "Pass `patch_json` as a JSON object, not a string."

### Tool / turn discipline — simplify

**Remove:**
```
- **Every turn starts with `state_get` and ends with `state_save`.**
  No exceptions, even for one-shot answers — at minimum bump
  `next_nudge_at` or set it to `null`.
- When you finish an inbound-driven turn that needs a user reply, call
  `enter_waiting` (after `state_save`).
- When you've answered something one-shot, or you ARE the nudge, call
  `complete_task` (after `state_save`).
```

**Replace with:**
```
Every turn ends with `state_save` then `complete_task`. No exceptions —
at minimum bump `next_nudge_at` or set it to `null`.
Never invent products, links, or apps. Coaching is text + photos only.
```

### Proactive nudges — remove enter_waiting references

**Remove:**
- "End with `complete_task`, NOT `enter_waiting`. They may not reply, and `enter_waiting` would tie up an execution indefinitely."
- Change "After you've replied (or before `complete_task`/`enter_waiting`)" → "Before `complete_task`"
- Change nudge section: "Read `state` and `nudge_intent`" → "Read `{{user_state}}` and `{{nudge_intent}}`"

### Onboarding — condense "Explain WHY"

**Remove** the per-question example sentences (~150 words):
```
- At the start (right after they tell you their name): a single line...
- When asking equipment: "זה משנה את התוכנית..."
- When asking injuries/limits: "כדי שלא אבקש ממך..."
- When asking dietary constraints: "זה משפיע על..."
- If they sound impatient or push back...
```

**Replace with (~30 words):**
```
Explain WHY once at the start ("אני שואל כמה דברים קצרים כדי לבנות
תוכנית שמתאימה לך"). Add a brief reason when asking equipment or
injuries — one natural sentence, not a disclaimer. If they push back,
re-explain in one line and continue.
```

**Remove** the trailing note from the closing example:
```
(But remember: no em dashes in your actual reply. Use a comma or a line break.)
```
Already covered in writing style.

### Voice notes — condense

**Remove** (~80 words). **Replace with (~35 words):**
```
Voice notes are auto-transcribed by Kapso — treat them identically to
typed messages. If the transcript is clearly garbled, ask:
"רגע, לא בטוח שתפסתי. תכתוב/תשלח שוב?"
```

### Reading the chat — update reference

"After loading state, scan recent conversation history..." →
"Based on `{{user_state}}`, scan recent conversation history..."

---

## Token impact

| Source | Before | After | Delta |
|--------|--------|-------|-------|
| System prompt words | 1,882 | ~1,550 | -332 |
| state_get tool call (removed from context) | ~150 tokens | 0 | -150 |
| state_get response in history | ~200 tokens | 0 | -200 |
| load_state workflow var (injected) | 0 | ~100 tokens | +100 |
| **Estimated net per turn** | | | **-580 tokens** |

From ~16,100 to ~15,500 input tokens per turn. Not a dramatic reduction but meaningful at the margin — and removes the model's ability to skip state loading entirely.

---

## What this does NOT fix

- The underlying Gemini flakiness. Retries may hit the same 0-token failure back-to-back. The fallback is a safety net, not a cure. If failure rate is high, switching models should be reconsidered.
- The `state_get` removal means the model can no longer access live-updated state mid-turn (e.g., if state changes during a turn). In practice this doesn't happen — the workflow is single-threaded per user.

---

## Resolved decisions

### OQ1 — Reply detection: Kapso function ✅

Function `fitbot-reply-check` created and deployed.

- **ID:** `88dfc487-0f8f-4bde-89b8-b67d84bfbd69`
- **Invoke URL:** `https://api.kapso.ai/platform/v1/functions/88dfc487-0f8f-4bde-89b8-b67d84bfbd69/invoke`
- **Logic:** reads `execution_context.context.agent_last_message`; returns `{ next_edge: "replied" }` or `{ next_edge: "no_reply" }`. Falls back to first available edge if neither is found.
- **Tested:** all three cases (message present, null, key missing) — correct.

Use as the function for the `decide` node after the agent. No LLM call, deterministic.

### OQ2 — Nudge entrypoint: decide after Start ✅

Kapso triggers always start from the `Start` node — no alternative entry point in the API. Solution: add a decide node immediately after `Start` that checks `{{nudge_intent}}`.

**Updated full workflow graph:**

```
[Start]
    ↓
[Decide: nudge_intent set?]
    ↓ yes (nudge)                      ↓ no (inbound)
[load_state trigger=nudge]        [load_state trigger=inbound]
    ↓                                   ↓
[Agent: complete_task]            [Agent: complete_task]
    ↓                                   ↓
  END                         [Decide: fitbot-reply-check]
                                ↓ replied        ↓ no_reply
                          [save retry=0]    [save retry++]
                                ↓                ↓
                          [Wait for      [Decide: retry ≤ 2?]
                           Response]       ↓ yes      ↓ no
                                ↓     [load_state] [Send fallback]
                          [load_state]     ↓        [save retry=0]
                                ↓     [Agent]           ↓
                             [Agent]              [Wait for Response]
                                                        ↓
                                                  [load_state]
                                                        ↓
                                                     [Agent]
```

The nudge path is lean: load state, run agent once, end. No retry loop, no wait.

### OQ3 — retry_count: 2 retries accepted ✅

Maximum 2 retries before fallback. `retry_count` is a workflow variable, reset to `0` on any successful reply. Initialise explicitly to `0` in a node before the first use to avoid undefined behaviour.
