# GOALS.md — Fishbone North Star & Weekly Focus

> **Status lives in Linear.** This file defines goals and maps them to Linear issues.
> To check progress, look at the linked issues — not this file.

## 🌟 North Star (updated 2026-06-27)

Find a cyber/AI agent security direction worth building. Validate by failing to reject. If no thesis survives the full panel, pivot the research angle fast.

---

## 📅 This Week (2026-06-29 → 2026-07-03)

**Theme:** Practitioner validation — two theses, right audiences

Framework: *Theses 1 and 3 are merged. We have two theses. The problem so far: we've been talking to people who couldn't really feel the pain. Fix: for each thesis, identify the specific roles that would feel it, reframe the problem statement in their language, build a question bank, then go find those people.*

---

### Theses (consolidated to 2)

**Thesis A — Agent opacity: ungovernable + unscopable**
Agent behavior isn't a file — it's prompts, tools, permissions, retrieval sources, and model config spread across systems. Security can't answer: what changed, who approved, what new actions are now possible, what new data is reachable. When something goes wrong, there's no way to scope which sessions were affected, what actions were taken under poisoned context, or prove remediation. Result: agents get blocked from high-stakes workflows, and when they aren't, incidents can't be properly disclosed.

**Thesis B — Unprovable agent authorization**
Regulated enterprises can't let agents operate autonomously because no one can prove actions stayed within the scope originally authorized. Behavioral monitoring tells you when it failed — it can't prove it succeeded. What's missing: verifiable proof at every tool call that the agent acted within its delegation.

---

### Methodology

For each thesis:
1. **Target positions** — who specifically would feel this pain (not just "CISOs")
2. **Adapted problem statement** — rewrite the thesis in their language and daily reality
3. **Question bank** — what we'll ask them to test whether the pain is real and what form it takes
4. **Outreach** — LinkedIn direct + relevant subreddits (post as specific questions, not pitches) + create calls

---

### Thesis A — Target positions & outreach plan

| Role | Why they feel it | Problem framing for them |
|------|-----------------|--------------------------|
| Security engineer / AppSec | Owns the controls; agents bypass them silently | "You're approving an agent deployment but you have no visibility into what it will actually do in production vs. what was tested" |
| Platform/DevOps engineer | Deploys agents; has no change management for prompt/config updates | "A prompt change went to prod last Tuesday. You don't know who made it, what it changed semantically, or whether it's why your error rate jumped" |
| GRC / Compliance officer | Needs audit trail for regulators | "Your regulator asks you to demonstrate that the AI decision made on patient X was based on authorized data and approved logic. You can't." |
| Incident responder / SOC | Called in when something goes wrong | "An agent took 400 actions before you noticed something was off. You have no way to tell which of those 400 were safe." |

**Subreddits:** r/netsec, r/AskNetsec, r/devops, r/mlops, r/LangChain
**LinkedIn targets:** Security engineers and AppSec leads at companies with ≥50 engineers and active AI deployments

---

### Thesis B — Target positions & outreach plan

| Role | Why they feel it | Problem framing for them |
|------|-----------------|--------------------------|
| Security architect | Designing agent authorization flows | "You can prove a human was authenticated. You can't prove an agent only did what it was authorized to do — the chain of delegation is unverifiable" |
| CISO at regulated enterprise (fin/health/defense) | Signs off on agent deployments | "Your board asks: can the agent exceed its permissions? You can say 'no by design' but you can't prove it in the event of an incident" |
| Legal / GC | AI liability and disclosure | "If an agent causes a data breach, your disclosure obligation depends on scope. You have no mechanism to establish scope." |
| Platform architect | Building multi-agent systems | "Agent A delegates to Agent B. Agent B delegates to Agent C. At no point in that chain is there a signed, auditable record of what was authorized." |

**Subreddits:** r/netsec, r/AskNetsec, r/cybersecurity, r/fintech (for regulated angle)
**LinkedIn targets:** Security architects and GRC leads at banks, healthtech, defense contractors

---

**Owner:** Both
**Goal by Friday:** Each thesis has been pressure-tested with ≥3 people who actually sit in one of the target roles above. Not CISOs-who-were-available — practitioners who live the specific pain.

---

## 📚 Weekly Archive

| Week | Theme | Outcome |
|------|-------|---------|
| 2026-03-22 | Stor.ai prep + learning kickoff | Stor.ai materials done (FB-145, 147, 152, 153); Stor.ai meeting happened 2026-03-28; learning in progress |
| 2026-03-29 | Run the experiment. Close expert gaps. Keep Stor.ai and Adidas warm. | FB-163, FB-129, FB-164, FB-165 done; business model work (FB-166) still in progress |
| 2026-04-05 | Knots/DAFNI experiments + Stor one-pager + Google/OpenAI insider calls | Pitch deck (FB-185) and one-pager (FB-186) done; Morris materials sent; Dean Greenberg call completed; DAFNI experiment plan sent for approval (FB-184 in progress) |
| 2026-04-12 | Exploration + experimentation week — ChatGPT apps channel, grocer pipeline, Danny eval | FB-185 ✅ FB-186 ✅; app submission hit OpenAI limbo (FB-192 canceled); FB-184 in progress; week framed as rapid idea-to-experiment cycling |
| 2026-04-19 | Pipeline momentum + channel validation + deal clarity | FB-195 in progress; FB-200 in progress; FB-197 (WoZ) launched; FB-198 (chess) done; FB-202 Polonio follow-up in progress |
| 2026-04-27 | Signal generation — parallel experiments, real data by Friday | FitBot WoZ (FB-209), stor.ai grocer pipeline (FB-195), new verticals (FB-210), Polonio/GMC (FB-211), Meta experiment (FB-212) — see Linear for outcomes |
| 2026-05-25 | FitBot monetization sprint — billing, quality gate, go-to-market signal | Polar billing (FB-268), Codex verdict (FB-233), Assaf Nadar coffee (Ohav), validation milestone doc (Both), engaged user baseline (Both) |
| 2026-06-07 | WTP signal + next direction research — FitBot billing go/no-go, pivot shortlist | Billing signal (≥5 non-F&F pay or close FitBot), next direction research (Agentic Commerce / Cyber / B2B AI) |
| 2026-06-27 | Thesis rejection panel — cyber AI agent security | ≥4 theses through full panel (≥5 practitioners + competitive research each); ≥4 new practitioner meetings generated for next week |

---

## How to maintain this file

- **At the start of each week** (Sunday or Monday), Avishay drafts the new week's theme + 3–5 priorities. Move the previous week into the archive table.
- **Mid-week**, only edit if the theme genuinely changes — don't churn.
- **Linear is the source of truth** for whether issues are done. This file is the *narrative*.
- When you (FishboneClaw) see something that should obviously be added to next week, suggest it once. Don't add it unilaterally.
