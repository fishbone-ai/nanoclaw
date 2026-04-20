# AI Visibility Initiative - DAFNI Hair

**Document type:** Pilot Brief  
**Date:** April 5, 2026  
**Prepared by:** Fishbone

---

## Overview

We're running a structured test to understand how product data quality affects visibility in AI-powered shopping surfaces.

Shoppers increasingly start their search in AI assistants rather than traditional search. When someone asks "best magnetic hair clips" or "hair straightening brush for short hair", AI systems surface products based on the quality and completeness of their catalog data - attributes like color, product type, structured descriptions, and category signals.

This initiative is about understanding what moves the needle for DAFNI specifically, and doing it in a way we can measure clearly.

---

## Baseline (April 5, 2026)

We pulled the current Google Merchant Center baseline for the selected experiment products on April 5, 2026:

| Field | Status |
|-------|--------|
| Color | Missing on 20 out of 22 experiment products |
| Product type | Present, but often broad or inconsistent (for example `BOWS`, `Klix`, `Tools`) |
| Age group / gender | Missing on 20 / 20 products respectively |
| SEO title | Missing on 19 out of 22 products |
| SEO description | Missing on 19 out of 22 products |
| Structured attributes / highlights | Limited coverage; room to enrich product-level signals further |

These are the kinds of fields AI systems use to match products to queries.

---

## What we're doing

We've selected 22 products for this initiative:

- **22 products in 11 matched pairs** - products with roughly similar 28-day GMC impression history, paired primarily within category. One from each pair gets enriched; the other stays as-is.
- **0 zero-impression pairs** - all eligible active products already had GMC impressions in the baseline window, so we are not forcing a zero-impression test where none exists.

For the enriched group, we're making the following changes directly in Shopify / feed-connected fields:

1. **Color normalization** - adding or standardizing the shopper-facing color value
2. **Product type cleanup** - making category labels more specific and consistent
3. **Structured attributes** - filling available taxonomy-aligned fields where missing
4. **Description enrichment** - rewriting copy to better reflect use case, product function, size, and distinguishing features
5. **SEO fields** - improving title / description coverage where relevant
6. **Feed consistency** - standardizing core product signals across the enriched set

No changes are made beyond the above. Prices, inventory, storefront merchandising, and campaign settings are untouched.

---

## Experiment structure

### Matched-pair test/control

- **11 matched pairs / 22 total products**
- **Balance:** Test 32,460 impressions vs Control 37,421 impressions (1.15x control/test ratio)
- **Primary matching approach:** within-category where possible, with limited cross-category matching only when no better same-category match existed
- **Baseline window:** March 7 - April 3, 2026 (28 days)

### Measurement question

Do enriched products gain more visibility than their matched controls over the same post-change window?

### Primary metric

- **Impressions change:** post-period vs baseline, comparing enriched products against control products at the pair level

### Secondary metrics

- Clicks
- CTR
- Purchases / downstream performance where available

---

## Timeline & measurement

| Date | Milestone |
|------|-----------|
| April 5, 2026 | Baseline captured. Brief shared. Enrichment begins on selected products. |
| Week 1 check | Confirm all changes propagated correctly into GMC. |
| Week 4 read | Compare enriched vs. control performance over a full post-change window. |

**What we're measuring:**

- **Paired products:** Did the enriched products gain more impressions than their matched counterparts over the same 28-day window?
- **Directional read:** Do clicks / CTR move in the same direction, or is the effect limited to visibility only?

Results will be shared once the post-change window is complete.

---

*Questions? Reach out to Ohav (ohav@getfishbone.ai) or Avishay (avishay@getfishbone.ai).*
