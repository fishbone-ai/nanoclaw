# MEMORY.md - Long-Term Memory

## Identity
- I am FishboneClaw 🐟, AI co-pilot for Avishay's startup, Fishbone
- Running on a Raspberry Pi (HAOS) via the NanoClaw add-on
- First came online: 2026-03-05

## Setup Notes
- Migrated from OpenClaw to NanoClaw (2026-04-18) — running on NanoClaw (fishbone-ai/nanoclaw)
- Workspace: /workspace/global/
- Business content repo: fishbone-ai/fishbone-claw (fishbone-ops merged in 2026-03-27, archived after)
- Slack is primary channel (SLACK_IS_MAIN=true); Telegram no longer active

## About Avishay
- Founder of Fishbone startup
- GMT+2 timezone
- Technical, direct, no-nonsense
- Night owl (set me up at 3am)

## Team
- **Ohav Peri** — co-founder/team member at Fishbone (NOT "Ohad" — easy to mishear/misread)

## Fishbone Product Clarity — Read Before Advising
- **Current focus: ChatGPT App.** As of 2026-03-30, Fishbone is NOT focused on feed/data optimization. The active product direction is the ChatGPT app. Do not default to feed optimization framing.
- **Feed optimisation ≠ ChatGPT App.** Feed optimisation = improving product data feeds (GMC, etc.) for better visibility. ChatGPT App = the current focus. They *could* be related but are NOT the same thing and should not be conflated.
- **Never mention "ChatGPT operator"** as something Fishbone sells or does. The Operator API is OpenAI's product (letting companies build on ChatGPT). This is NOT what Fishbone offers. Drop it from any sales/pitch framing.

## Bias Corrections — Read Before Advising
- **Fishbone does NOT have proven catalog quality leadership.** This is an unvalidated assumption, not a moat. ReFiBuy and others are doing similar work. Fishbone has some experience from the ChatGPT Apps path but no production-ready enrichment pipeline and no demonstrated superiority. Do NOT use "Fishbone owns catalog quality" as a premise when analyzing strategy or opportunities. Treat catalog expertise as a hypothesis to be validated, same as any other assumption.

## Key Context — Contacts & Partners
- **Nati** — ex-Wix Head of SEO. He does NOT run GTM advisory for founders. Do not describe him that way.
- **Gil Laktush** — 10 years at Fiverr; ran Growth Marketing, then Marketing Technology (SEO, CRO, CRM, Marketing Automation), then led Fiverr Go (AI product initiatives). Now manages Fiverr's full catalog operations (business + technical). Met with Fishbone 2026-04-01. SEO/GEO expert with a strong commercial/ROI lens. NOT the same person as Nati. Do not confuse them.
- **Stor.AI / Morris** — a *tech partner*, not a customer. They provide ecommerce software to groceries companies. Collaborating with them = reach to multiple groceries players. Do NOT treat them as validation of #6 from a retailer perspective.
- **Stor.AI go-to-market model (as of 2026-03-30):** Ohav spoke with Morris. Stor wants to pitch Fishbone as a *separate company that works with them* and provides the ChatGPT app service (with Stor's help). NOT a pure reseller/white-label model -- Fishbone stays visible as a separate vendor.
- **Knots Studio** — Fishbone already has GMC access via Knots Studio. Don't suggest getting GMC access as a blocker.
- **fidarmy (Reddit)** — Ohav did follow up. He just hasn't responded yet. Always check Linear issue status before claiming something wasn't done.

## Fishbone Methodology — Lean Startup in Linear

### The two systems and their roles
- **Google Sheet (`strategy/assumptions/scores.xlsx`)** — source of truth for *what the assumptions are* and their confidence scores. Never edit directly — use the CLI.
- **Linear** — source of truth for *what we're doing to validate each assumption* AND for the status of all weekly goals. Issues are experiments, not features.
- The **assumption number** (e.g. `#3`) is the link between them. Always use the `[Assumption #N]` prefix on Linear issues.
- **GOALS.md** — references Linear issues only. Never track task status there with checkboxes or checked items. Status lives in Linear.

### Linear issue taxonomy
- **Top-level issues** = assumptions. These are the north stars — they represent a belief that needs to be tested.
  - Currently: FB-121 (#1), FB-122 (#2), FB-123 (#3), FB-124 (#4), FB-125 (#5), FB-128 (#6)
- **Sub-issues** = experiments / tasks that validate the parent assumption
- **Enablers** = work that doesn't validate an assumption but is necessary (e.g. FB-116 website). Label or tag as enabler; track but don't confuse with validation work.

### Flow when assumptions change
- **Validated** → Mark Linear issue Done. Update sheet confidence. Log in `learnings/YYYY-MM.md`.
- **Invalidated** → Mark Done (differently). May trigger pivot → new assumption issues.
- **New assumption added** → Add to sheet via CLI. Create Linear issue `[Assumption #N] Title`. Break into sub-issue experiments immediately.
- **Assumption removed** → Cancel Linear issue + sub-issues. Remove from sheet.
- **Assumption modified** → Update both the sheet AND the Linear issue description. Keep them in sync.

### When suggesting tasks (from meetings, standups, etc.)
Every suggested Linear issue must include:
- Which assumption it validates (e.g. "validates #3")
- OR be explicitly flagged as an enabler (not assumption-linked)
- OR be flagged as a sub-issue of an existing task
- If it can't be linked to an assumption and isn't a clear enabler, question whether it's waste.

## News Digest Preferences
- **Skip:** ChatGPT's own stats/metrics/downloads, general AI hype/growth stats, competitor market share numbers, meta-AI infrastructure stories (e.g. OpenClaw acquisitions, AI researcher home automation, AI lab funding/hiring), anything not directly actionable for Fishbone's product/market
- **chatgpt-ecosystem feed:** tracks *third-party apps built on ChatGPT* (operators, SDK integrations, GPT Store apps) — NOT ChatGPT's own growth
- **Focus on:** actionable insights, new apps in ChatGPT ecosystem, technical developments relevant to Fishbone's work (ecommerce, catalog, GMC, merchant tools)
