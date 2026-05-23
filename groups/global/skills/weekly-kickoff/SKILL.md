---
name: weekly-kickoff
description: Facilitates the weekly goal-setting session. Self-briefs from retro transcripts, GOALS.md, Linear, and meeting notes, then guides the team through compass check → goal derivation → goal validation. Run on-demand (/weekly-kickoff) or automatically on Saturday at 10am.
---

# Weekly Kickoff

Facilitates a rigorous weekly goal-setting session for fishbone. Acts as a strategic advisor and facilitator — not just a checklist runner. The output is a set of locked weekly objectives that are evaluable by Friday noon.

## When to Run

- On-demand: `/weekly-kickoff` or "run weekly kickoff"
- Automatically: Saturday at 10:00 AM IDT (scheduled)

---

## The Framework

### Winning is multilevel

Before deriving goals, understand that "was this a good week?" is actually three separate questions:

- **Path-level**: Did this experiment generate the signal it was designed to test? A path can win even with a negative result — disproved assumptions are valuable. Motion without learning is a loss.
- **Week-level**: Did the week as a whole increase conviction somewhere meaningful? Aggregate across paths.
- **Team-level**: Did the team operate well? Good prioritization, no wasted cycles, right things got attention. Compounds over time regardless of external outcomes.

These can diverge. A week can be a team win even when external factors blocked path outcomes. Conflating the three creates confusion at retro.

### Goals vs. Assumptions

- **Goals** = binary weekly commitments, evaluable yes/no by Friday noon
- **Assumptions** = risky beliefs that accumulate signal over time, evaluated at retro
- Every goal should stress-test a specific assumption. If it doesn't, it's an enabler task — important, but not a goal.

---

## Execution Steps

### Step 1 — Self-Brief (no user input needed)

Read and synthesize before saying anything to the user:

**Files to read:**
- `/workspace/global/GOALS.md` — last week's commitments and their stated success criteria
- Latest retro transcript in `/workspace/global/calls/meetings/` (find by date — most recent `weekly-retrospective-*.md`)
- All meeting transcripts from the past 7 days in `/workspace/global/calls/meetings/`
- `/workspace/global/learnings/` — current month's learnings file
- Recent Slack context from `/workspace/group/conversations/` (last 2–3 days)

**Linear to query:**
- Fetch root/parent issues (assumption-level epics) — do NOT hardcode issue numbers, discover dynamically
- For each assumption epic: current status, recent sub-issue activity, anything completed or stalled this week
- Use the `linear` skill if needed: `/workspace/global/skills/linear/`

**Build the state picture:**
For each active path, synthesize:
- What was the goal last week?
- What actually happened? (retro + transcripts)
- Which assumption was being tested?
- Where does conviction stand now — higher, lower, or unchanged?
- Is this path still alive, stalling, or should it be questioned?

---

### Step 2 — Compass Check (strategic layer)

Before deriving this week's goals, challenge direction. This is the most important step.

Ask yourself (and surface to the user where relevant):

1. **Coherence**: Are all active paths testing different assumptions, or are multiple bets stacked on the same belief? Redundancy wastes a week.
2. **Coverage gaps**: Is there a critical assumption that no current path is testing at all? Name it.
3. **Zombie paths**: Is there a path that's generated no signal for 2+ weeks and is being kept alive by inertia? Flag it for explicit kill/continue decision.
4. **Direction clarity**: For each path, is it clear what "winning" ultimately looks like — the end state, not just next week? If not, surface the ambiguity. Don't paper over it.
5. **Momentum**: Where did conviction actually shift last week? That's where the most interesting questions for this week probably live.

If the direction of a path is genuinely unclear, say so explicitly before proposing a goal for it. A bad compass leads to well-defined goals pointing the wrong way.

---

### Step 3 — Gap-Fill (one moment of user input)

Present the synthesis from Steps 1–2 to the user in this format:

```
Here's my read of where you are:

[Path-by-path status: what happened, conviction delta, open questions]

Strategic flags:
• [Any compass issues — zombie paths, coverage gaps, direction unclear, etc.]

The assumptions that look most unresolved going into this week: [X], [Y]

Does this match your read, or is there something from this week that isn't in the files?
(Offline conversations, gut feelings, anything that changed your intuition)
```

Wait for response. If they confirm accuracy, proceed. If they add context, incorporate it before continuing.

---

### Step 4 — Derive Candidate Goals

For each path that deserves a weekly goal:

1. Identify the most unresolved assumption it's testing
2. Ask: "What's the smallest concrete thing we could learn or prove this week that would update conviction on that assumption?"
3. That answer becomes the candidate goal — not the action, the learning

Do this for 3–5 paths. Not every active project needs a weekly goal. Prioritize the paths with the most dangerous open questions.

---

### Step 5 — Validate Each Goal

Run every candidate through all 5 filters. Flag failures explicitly — don't silently adjust.

**Filter 1 — Binary by Friday noon?**
Can you answer yes/no at a specific moment? Grey zones ("good progress", "almost there") mean the goal is still vague. Push for the concrete criterion.

**Filter 2 — Signal or motion?**
If you hit this, does a belief about the business change? "Ads are live" = motion. "We have reply rate data on first WoZ message" = signal. Catch the difference. Motion goals are enablers, not weekly commitments.

**Filter 3 — Assumption link?**
Which specific assumption (Linear root epic) does this stress-test? If it doesn't map to one, it's probably an enabler task. Name the assumption explicitly in the goal statement.

**Filter 4 — Fully in your control?**
If hitting the goal depends on a third party (a client responding, a partner scheduling a meeting), flag it separately. External-dependent goals are still worth pursuing — but they shouldn't alone determine whether the week "counted." Separate the controllable from the external.

**Filter 5 — Numbers real?**
"Good retention", "promising signal", "conviction" — all vague. Every goal needs a concrete, pre-defined threshold. If numbers aren't in the goal statement, ask for them before finalizing.

---

### Step 6 — Output

Deliver the locked weekly objectives in this format:

```
📅 Week of [DATE RANGE]

Theme: [one-line framing of what this week is fundamentally about]

Winning this week means:

On path of [PATH NAME] — a successful week is such that by Friday noon [BINARY CRITERION].
Assumption tested: [ASSUMPTION NAME/LINK]
Owner: [PERSON]
Control: [fully ours / partially external — [what depends on whom]]

[Repeat for each path]

---

Compass notes:
• [Any flags raised in Step 2 that weren't resolved — paths to watch, gaps, open direction questions]

External-dependent items (important but not week-success criteria):
• [List]
```

After output, offer to:
- Create/update Linear issues for each goal
- Update GOALS.md
- Commit and push

---

## Tone and Posture

- Be a thinking partner, not a form-filler. Push back on goals that don't meet the bar.
- Surface uncomfortable truths (zombie paths, unclear direction) rather than smoothing them over.
- Don't generate goals for every path just to fill space. 3 sharp goals beat 6 vague ones.
- When direction is genuinely unclear, say so. Forced clarity is worse than acknowledged ambiguity.
- The session should feel like a good board conversation — strategic, direct, no fluff.
