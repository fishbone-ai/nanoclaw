---
name: venture-evaluation
description: >
  Evaluate a venture idea against the Fishbone rubric in two stages: quick filter (kill/pass)
  then scored research with experiment design. Use when someone pitches an idea, shares a concept,
  or asks to evaluate a venture opportunity. Trigger on: "evaluate this idea", "is this worth pursuing",
  "run the rubric on", "venture evaluation", or when a new idea is shared for assessment.
---

# venture-evaluation

Evaluate venture ideas against the rubric at `strategy/venture-evaluation-rubric.md`. The process has two stages with a human decision point between them.

## Stage 1: Quick Filter

### Step 0 -- Gather context

Before scoring anything, make sure you have enough context to evaluate honestly. Read the rubric first (`strategy/venture-evaluation-rubric.md`), then assess what you know about the idea.

You need at minimum:
- **What the product/service actually is** -- not a vague concept, a concrete description
- **Who it's for** -- specific buyer/user persona
- **Why now** -- what changed that makes this timely
- **How the evaluator encountered this idea** -- pitch from someone? own observation? article?
- **Any existing evidence** -- conversations, data, competitor landscape, user signals

If any of these are missing or vague, **ask clarifying questions before proceeding**. Don't score based on assumptions you're filling in yourself. Be specific about what's missing -- e.g. "You mentioned the product is an AI meeting room, but I don't know who the initial buyer would be -- is this targeting startups, mid-market, or enterprise?"

Check for relevant context in the workspace:
- Meeting transcripts in `calls/meetings/` that might relate to this idea
- Existing competitor research in `strategy/competitors/`
- Learnings in `learnings/` that might be relevant
- Previous evaluations in `strategy/evaluations/`

### Step 1 -- Run the quick filter

Evaluate each of the four filter criteria separately. For each one:
1. State the criterion
2. Present the evidence for and against
3. Give a clear **PASS** or **FAIL** verdict
4. If borderline, explain what would tip it

The four filters:
1. **Behavioral signal** -- are people already doing some version of this?
2. **Someone would pay** -- is there a buyer with budget?
3. **Can reach design partners** -- plausible path to 5-10 early users through our network?
4. **Signal in < 2 weeks** -- can we design an experiment that tells us something fast?

### Step 2 -- Deliver the filter verdict

Present results as a clear summary:

```
## Quick Filter: <idea name>

| # | Criterion | Verdict | Key evidence |
|---|-----------|---------|-------------|
| 1 | Behavioral signal | PASS/FAIL | ... |
| 2 | Would someone pay | PASS/FAIL | ... |
| 3 | Can reach design partners | PASS/FAIL | ... |
| 4 | Signal in < 2 weeks | PASS/FAIL | ... |

**Overall: PASS / FAIL**
<1-2 sentence summary of why>
```

If it **fails**: recommend drop or park, with a note on what would need to change for it to pass in the future.

If it **passes**: recommend moving to Stage 2 and ask the user if they want to proceed. Do NOT automatically start Stage 2 -- it requires research time and the user should opt in.

---

## Stage 2: Research & Scoring

Only start this when the user explicitly says to proceed after a Stage 1 pass.

### Step 3 -- Research

Before scoring, do actual research. This isn't just vibes -- look for evidence:

- **Competitors**: Search for existing players in this space. Check `strategy/competitors/` for any existing research. Look for recent news, funding rounds, product launches.
- **Demand signals**: Search for community discussions (Reddit, HN, forums), search trends, job postings that suggest market movement.
- **Pricing precedent**: Find comparable products and what they charge. This grounds the revenue model score.
- **Technical landscape**: What's the build stack? What exists as off-the-shelf vs needs to be built?

Summarize findings before scoring. The user should see your research before seeing scores.

### Step 4 -- Score

Score each of the 9 dimensions (1-5) from the rubric. For each:
1. State the dimension
2. Present evidence (from research + what we already know)
3. Assign a score with brief justification

Present as a table:

```
## Scoring: <idea name>

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Behavioral signal | X/5 | ... |
| Timing | X/5 | ... |
| Competitive landscape & wedge | X/5 | ... |
| Market size / upside | X/5 | ... |
| Build feasibility | X/5 | ... |
| Distribution clarity | X/5 | ... |
| Revenue model | X/5 | ... |
| Team-problem fit | X/5 | ... |
| Founder excitement | ?/5 | (ask founders) |

**Total: XX/45**
```

**Important:** Always leave founder excitement as "?" and ask the user to fill it in. Don't guess at their excitement level.

Flag any dimension that scores 1 as a potential dealbreaker.

### Step 5 -- Suggest experiment card

Based on the research and scoring, draft an experiment card:

```
## Experiment Card: <idea name>

### What we already know
<summarize existing evidence -- conversations, research, signals>

### Riskiest assumption
<the single belief that kills the idea if wrong -- be specific>

### Fastest experiment
<talk to people OR build something -- explain why this mode, who specifically, what to ask/build>

### Timeline
<days/weeks to signal>

### Kill criteria
<specific result that means drop it>

### Promote criteria
<specific result that means give it real time>
```

### Step 6 -- Save the evaluation

Write the complete evaluation (filter results + research + scores + experiment card) to `strategy/evaluations/<idea-name>.md`. Use kebab-case for the filename. Include the date at the top.

Format:

```markdown
# Evaluation: <Idea Name>

**Date:** YYYY-MM-DD
**Source:** <how the idea came in -- pitch from X, observation, article, etc.>
**Status:** passed-filter / failed-filter / scored / experiment-in-progress / dropped / parked / promoted

---

<full filter results>

---

<full research + scoring>

---

<experiment card>
```

If a Linear issue exists for this evaluation (e.g. FB-188), link to it.

---

## Notes

- Be honest in scoring. The rubric's value comes from forcing hard questions, not from making ideas look good.
- When in doubt about a score, err toward the lower number. Optimism bias is the default -- the rubric should counteract it.
- The user might disagree with your scores. That's fine and expected -- the point is to have a structured conversation, not to produce a definitive verdict.
- If the user provides new information that changes a score, update the evaluation file.
