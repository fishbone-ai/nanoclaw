# Venture Evaluation Rubric

A lightweight framework for filtering and scoring new venture ideas. Designed for speed -- not thoroughness. The goal is to kill bad ideas fast, score promising ones consistently, and define the fastest experiment to learn more.

---

## Stage 1: Quick Filter (15 minutes)

Binary pass/fail. If any of these is clearly "no", drop the idea immediately. Don't spend time scoring something that fails a basic gate.

### 1. Is there a behavioral signal?

Not "is this painful right now" -- but **are people already doing some version of this, even crudely?** Look for:
- People duct-taping solutions together
- Manual workarounds that prove demand
- Early adopters doing the thing without a product
- Growing search interest, community threads, complaints

A "no" here means you're inventing demand, not capturing it. Kill it.

### 2. Would someone pay for this?

Is there a buyer with budget and authority? Not just users -- a paying customer. Could be:
- Direct SaaS buyer
- Enterprise contract
- Marketplace transaction fee
- Someone already paying for a bad alternative

If the only model is "get millions of free users then figure it out" -- that's a different game than what we're playing.

### 3. Can we reach 5-10 early design partners?

Not "do we already have relationships in this exact domain" -- but is there a plausible path through our network (1-2 hops) to people who would try this? Consider:
- Direct connections who fit
- Warm intros we could ask for
- Communities we could tap into
- The idea originator's own network

If reaching the first 10 users requires cold enterprise sales with no footholds, that's a red flag.

### 4. Can we generate meaningful signal in < 2 weeks?

Not necessarily building -- any experiment that produces a clear yes/no. Could be:
- 5-10 conversations with the right persona
- A functional prototype that a few people can try
- A landing page + waitlist that measures interest
- A concierge/manual version of the service

If even the cheapest possible experiment requires months before you'd know anything, the iteration speed is too slow for exploration mode.

---

## Stage 2: Scoring (1-2 hours of research)

For ideas that pass the quick filter. Score 1-5 on each dimension. The purpose isn't precision -- it's forcing yourself to think about each dimension honestly and have a comparable score across ideas.

**Scoring process:** Score independently (Avishay and Ohav each), then compare. Disagreements are more valuable than consensus -- they surface different assumptions about the idea.

### Behavioral signal strength (1-5)

How strong is the evidence that people want this?

- **1** -- "We think this is a problem" (pure hypothesis)
- **3** -- Some people are doing this manually; a few competitors exist but haven't nailed it
- **5** -- People are literally asking for this, throwing money at bad alternatives, hacking workarounds

### Timing (1-5)

Are we too early, too late, or riding the wave?

- **1** -- Need to educate the market for years before they're ready
- **3** -- Early adopters are ready, mainstream is 1-2 years out
- **5** -- The behavioral shift is happening now; clear "why now" moment

### Competitive landscape & wedge clarity (1-5)

Not just "are there competitors" but "do we see a clear angle?"

- **1** -- Crowded, no differentiation, incumbents are good enough
- **3** -- Competitors exist but there's a clear gap or underserved segment
- **5** -- New category or obvious wedge that nobody is executing on

### Market size / upside potential (1-5)

How big could this be if the thesis is right?

- **1** -- Niche, maybe a few hundred potential customers worldwide
- **3** -- Meaningful market, could build a $10M+ ARR business
- **5** -- Massive market, clear path to $100M+ if the thesis is right

### Build feasibility (1-5)

Can we build this? Not "is it technically possible" -- but can *our team* build a credible version?

- **1** -- Requires deep domain expertise we don't have, or years of R&D
- **3** -- Challenging but learnable; we'd need to skill up in some areas
- **5** -- Squarely in our technical wheelhouse, could start building tomorrow

### Distribution clarity (1-5)

Beyond the first 10 users, is there a path to 100, 1000?

- **1** -- Every customer requires direct outbound sales, no leverage
- **3** -- Some organic growth channel exists (word of mouth, marketplace, community) but unproven
- **5** -- Built-in virality or clear distribution channel we can access

### Revenue model believability (1-5)

Can you articulate who pays, how much, and why?

- **1** -- No idea who pays or how
- **3** -- Clear buyer, reasonable price point, but unvalidated willingness to pay
- **5** -- Pricing model has precedent, comparable products sell at this price, buyers confirm

### Team-problem fit (1-5)

Not "does this match our current product" -- but are we a credible team to tackle this?

- **1** -- No relevant skills, network, or insight; random pivot
- **3** -- Technical skills transfer; we'd need to build domain knowledge but have a learning edge
- **5** -- Deep relevant experience, unique insight, or unfair advantage for this specific problem

### Founder excitement (1-5)

Honestly -- would you and Ohav grind on this at midnight?

- **1** -- Sounds like a business opportunity but doesn't light a fire
- **3** -- Intellectually interesting, could see getting into it
- **5** -- Can't stop thinking about it, already sketching solutions

### Interpreting the score

Total is out of 45. There's no magic formula, but some rules of thumb:

- **Any dimension at 1** is a serious red flag. Think hard about whether it's a dealbreaker or something that can be overcome.
- **Below 22** -- probably park it. The math doesn't add up yet.
- **22-32** -- interesting but risky. Worth an experiment if the right dimensions are strong.
- **Above 32** -- strong candidate. Move to experiment card immediately.

Not all dimensions are equal. **Behavioral signal, timing, and founder excitement** are more load-bearing than distribution or revenue model at this stage -- distribution and revenue can be figured out later if the core pull is strong.

---

## Stage 3: The Experiment Card

Every idea that scores above threshold gets one of these. This is the bridge between "interesting idea" and "we're actually learning something."

### What we already know
Before designing the experiment, summarize the evidence you already have. What conversations, data, or observations informed the scoring? This prevents re-researching things you already know and focuses the experiment on the actual gap.

### Riskiest assumption
The single belief that, if wrong, kills the idea. Be specific -- not "people want this" but the precise version: "IT managers at 500+ person companies would approve always-on recording in meeting rooms."

### Fastest experiment
The cheapest, fastest way to test that assumption. Two modes:
- **Talk to people** -- 5-10 conversations with the right persona. Best when the risk is "do people actually want this?"
- **Build something** -- quick MVP, landing page, concierge version. Best when the risk is "can we deliver the value?" or "does the product work?"

Pick the one that matches the riskiest assumption. Don't default to building when talking would be faster.

### Timeline
How long until we have a clear signal? Should be days to weeks, not months.

### Kill criteria
What result means "drop it"? Be specific before you start, so you don't rationalize bad results after. Example: "If 4 out of 5 IT managers say 'this is creepy and we'd never allow it', we drop it."

### Promote criteria
What result means "this deserves a dedicated Linear issue and real time investment"? Example: "If 3 out of 5 say 'I'd pilot this tomorrow' and can name a budget owner, we promote."

---

## How to use this

1. Idea comes in (from a conversation, a pitch, a shower thought, whatever)
2. Run the quick filter. Takes 15 minutes. Most ideas die here. That's good.
3. If it passes, spend 1-2 hours researching and scoring. Use the scoring table.
4. If the score is promising, fill out the experiment card.
5. Run the experiment in your next available exploration slot (weekly time block or when blocked on main work).
6. After the experiment: drop, park, or promote to a real Linear issue.

The entire loop for one idea should take less than a week of calendar time (not a week of effort -- a few hours spread across the week).

## Where evaluations live

Completed evaluations go in `strategy/evaluations/<idea-name>.md`. Keep all of them -- including dropped ideas. This prevents re-evaluating something you already killed, and builds a record of your judgment over time.
