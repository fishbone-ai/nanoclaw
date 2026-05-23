# Fitbot Kapso Incident -- orphaned waits and conversation context loss

Date: 2026-04-28

## Summary

Two separate issues were present in the live Fitbot Kapso workflow:

1. `fitbot-reply-check` was checking `execution_context.context.agent_last_message`, but the live Kapso decision-function payload did not include that field. The function therefore misclassified some successful replies as `no_reply`.
2. Several old workflow executions were still stuck in legacy `enter_waiting` state from the earlier workflow shape. When those executions were manually ended via the workflow execution API, Kapso also ended their active WhatsApp conversation records. Later inbound messages from those users created new conversation records, so the agent lost old thread history in live conversation context.

## Changes applied

### 1. Fixed `fitbot-reply-check`

Updated deployed function `88dfc487-0f8f-4bde-89b8-b67d84bfbd69` to detect replies from `whatsapp_context.messages` instead of `execution_context.context.agent_last_message`.

New logic:

- Collect `whatsapp_context.messages`
- Treat any message with `direction == "outbound"` as proof that the agent replied
- Return:
  - `replied` + `retry_count: 0` for normal inbound replies
  - `nudge_done` + `retry_count: 0` for nudge executions
  - `no_reply` only when there are no outbound messages in the payload

This was verified against a real invocation payload from Avishay's conversation, where the old function failed even though the bot had sent `עובד! מה קורה?`.

### 2. Closed stale orphaned waiting executions

Ended these stuck executions:

- `7890b020-4e85-4ce2-9e83-4dc11bb9ed52`
- `be890476-6786-475b-bcd2-f870114aa112`
- `73e461cf-c997-4e91-81a7-93b2d3bc352e`
- `5a869291-3317-4086-89b4-891722bef52c`
- `18ec9440-a3aa-4259-be5d-471d4b70f1ec`
- `59272d40-dd36-4aeb-b69a-5259129b5dc6`
- `75c21faf-5791-47e0-84d2-6b8366c90798`
- `b603b028-c498-4c8d-ac81-d3cb19bac8f1`

Pakko's stuck execution `a5370d13-24cb-47ea-8e39-92ff32dd804f` was also ended earlier, and a fresh execution was started manually.

## Side effect discovered

Ending stale waiting executions also ended the active WhatsApp conversation records behind them.

Confirmed examples:

- Ohav old conversation `7638ed6e-04d4-4c93-a21c-f368dcd0077f` was ended
- Ohav later received a new active conversation `652b8562-3480-4149-a106-4bea70522ec0`
- Noga old conversation `80afa717-c156-4bac-a957-0005980e2231` was ended
- Noga later received a new active conversation `72806047-2ca2-4845-84c3-2d2863bb41f9`

This means:

- Durable Fitbot state in Supabase still survives
- Prior WhatsApp thread history does not automatically survive into the agent's new live conversation context

## Current safe state

After cleanup, only healthy waiting executions should remain.

At the time of writing, the new active executions included:

- Pakko recovery execution on new conversation
- Ohav new execution on new conversation
- Noga new execution on new conversation

These are healthy from a workflow-state perspective, but conversation history for Ohav and Noga was split across old and new conversation records.

## What not to do

- Do not bulk-end waiting executions again via `PATCH /workflow_executions/{id}` unless loss of active conversation history is acceptable.
- Do not assume an ended execution is independent of the underlying WhatsApp conversation object.

## What the docs suggest is possible

Documented Kapso capabilities relevant to recovery:

- `PATCH /platform/v1/whatsapp/conversations/{conversation_id}` can update conversation status and is documented as usable to reopen ended conversations for follow-ups.
- `GET /platform/v1/whatsapp/messages` and `GET /meta/whatsapp/v24.0/{phone_number_id}/messages` can retrieve historical messages, including filtering by `conversation_id`.

No documented API was found for:

- merging two conversations
- rebinding a running execution to a different conversation
- forcing a new execution to inherit an old conversation's message history

## Recommended restoration path

### Goal

Restore enough agent context for Ohav and Noga without creating more conversation splits.

### Recommended approach

1. Leave the current new active conversations in place.
2. Fetch the old conversation history for each affected user by `conversation_id`.
3. Summarize the old thread into a compact Fitbot memory note.
4. Write that summary into durable state via `fitbot-state`:
   - `notes`
   - `weekly_plan`
   - any missing structured fields that can be safely recovered
5. Let future turns use:
   - the new active conversation history for recent messages
   - Supabase state for older context

This does not restore the old chat transcript into Kapso's live conversation history, but it restores the practical coaching context the agent needs.

### Optional experiment

Potentially test reopening one ended conversation record via conversation status API in a controlled case to see whether future inbound traffic is attached back to that old conversation. This should be treated as an experiment, not assumed safe behavior.

## Open question

Whether reopening an ended Kapso conversation can cause subsequent inbound messages to reuse that old conversation record instead of the newer one is currently unverified.

## Architecture guidance after this incident

### Core lesson

Workflow execution lifetime should not be treated as durable memory.

FitBot has three different lifecycles:

1. WhatsApp conversation lifecycle
2. Kapso workflow execution lifecycle
3. FitBot memory lifecycle in Supabase

These are related but not equivalent.

The safe design assumption is:

- conversation history is short-term context
- workflow executions are transient runtime containers
- Supabase `user_state` is the durable source of truth

### What should survive execution endings

Execution endings should ideally be operationally irrelevant.

If a workflow ends cleanly and later restarts, FitBot should still know:

- who the user is
- their goal
- their training setup
- injuries / constraints
- current weekly plan
- tone / preference details that matter
- next nudge timing and intent

If those facts are persisted in state, a fresh execution can continue correctly even when the prior execution is gone.

### Nudge design

Nudges should not depend on a prior execution staying alive forever.

Recommended model:

1. On a normal coaching turn, the agent saves:
   - `next_nudge_at`
   - `next_nudge_intent`
   - any meaningful long-term updates to the user profile / plan
2. A scheduler or API trigger starts a nudge execution when due
3. The nudge execution loads state, sends one short message, updates state again, and ends cleanly

This means a nudge must be restartable from state alone.

Healthy nudge rule:

- a nudge should still work even if the previous execution no longer exists

### Waiting behavior

The new workflow shape is still correct:

- inbound message
- `load_state`
- `agent`
- `reply_check`
- `wait_for_response`

This is healthy waiting behavior.

The problem was the old legacy `enter_waiting` path, not waiting itself.

Operational distinction:

- execution waiting on `wait_for_response` = normally healthy
- execution with `current_step: null` and/or `agent_last_message: "[ENTER_WAITING]"` = suspicious legacy wait, likely orphan-prone

### Why not attach raw last-N messages to every run

Attaching raw last-N messages manually to each workflow run is not the preferred architecture.

Problems with that approach:

- duplicates context already carried by Kapso
- increases token usage on every turn
- creates another failure surface during workflow changes
- still does not solve old unresolved media or long-term memory cleanly

Preferred pattern:

- use Kapso conversation history for recent context
- use `user_state` for durable memory
- optionally keep a compact rolling summary in state for high-signal recent context that does not fit structured fields

### Practical rule for future recoveries

Before any destructive recovery action:

1. fetch the old conversation history
2. persist the useful context into state
3. only then end or replace the execution

If recovery is needed and the execution is still resumable, prefer resume over end.

### Media caveat

Old unresolved media is a special case.

Text can usually be summarized into state once.
An unprocessed image from an old conversation is not automatically available as active context in a new conversation.

That means:

- resolved image analyses should be saved into state if they matter long-term
- unresolved image requests may need either manual recovery or a resend from the user
