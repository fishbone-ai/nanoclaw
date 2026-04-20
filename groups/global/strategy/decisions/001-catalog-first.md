# ADR 001: Catalog enrichment over chat layer

**Date**: 2025-03-05
**Status**: Accepted

## Context

We need to decide where to start. Two obvious entry points into agentic commerce:

1. **Catalog enrichment** -- improve product data quality using AI
2. **Chat/conversational layer** -- AI shopping assistants, conversational search

Both are real opportunities. We can only do one well right now.

## Decision

Start with catalog enrichment.

## Rationale

- **Concrete deliverable**: merchants can see improved product pages immediately. No integration complexity, no behavior change required from shoppers.
- **Measurable ROI**: before/after on conversion, search ranking, return rates. Easy to prove value.
- **Data foundation**: good catalog data is a prerequisite for everything else we want to build (search, recommendations, agents). Starting here means we're building the foundation, not a feature.
- **Lower go-to-market friction**: catalog enrichment is a service merchants understand. "We'll make your product pages better" is a simpler pitch than "we'll add an AI chat widget."
- **Defensibility**: if we accumulate expertise in product data across verticals, that knowledge compounds.

## Risks

- Catalog enrichment can feel like a "service" not a "product." Need to build tooling that scales, not just do it manually.
- Merchants might undervalue data quality until they see results. Need good before/after storytelling.

## Consequences

- First product effort focuses on catalog ingestion, enrichment pipeline, and merchant review UI.
- Chat/conversational features go on the roadmap for later, after we have a data foundation.
