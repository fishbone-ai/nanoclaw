# AI Visibility Initiative - Knots Studio

**Document type:** Pilot Brief  
**Date:** April 2, 2026  
**Prepared by:** Fishbone

---

## Overview

We're running a structured test to understand how product data quality affects visibility in AI-powered shopping surfaces.

Shoppers increasingly start their search in AI assistants rather than traditional search. When someone asks "what's a good gift for a home decor lover under £100?", AI systems surface products based on the quality and completeness of their catalog data - attributes like color, material, product type, and structured descriptions.

This initiative is about understanding what moves the needle for Knots Studio specifically, and doing it in a way we can measure clearly.

---

## Baseline (April 1, 2026)

We pulled your full Google Merchant Center catalog on April 1, 2026:

| Field | Status |
|-------|--------|
| Color | Missing on 40 out of 42 products; the 2 that have values contain SKU codes rather than color names |
| Product type | Missing on 28 out of 42 products |
| Structured attributes (material, dimensions, etc.) | Not populated |
| Brand | Inconsistent formatting ("knots studio" vs "Knots Studio") |
| Product highlights | Not set |

These are the fields AI systems use to match products to queries.

---

## What we're doing

We've selected 38 products for this initiative:

- **30 products in 15 matched pairs** - products with similar impression history, paired by category. One from each pair gets enriched; the other stays as-is.
- **8 products in 4 zero-impression pairs** - products live in your GMC feed but with no impressions in the past 28 days. Same split: one enriched, one unchanged.

For the enriched group, we're making the following changes directly in Shopify (which syncs to Google Merchant Center automatically):

1. **Color** - adding the correct color name
2. **Product type** - filling in the category label where missing
3. **Brand** - standardizing to "Knots Studio"
4. **Structured attributes** - filling in Shopify's taxonomy fields (material, dimensions, pattern, etc.)
5. **Description** - rewriting to ~150-300 words covering material, use case, dimensions, and care
6. **Product highlights** - adding 3-5 concrete feature bullets per product

No changes are made beyond the above. Prices, inventory, storefront, and campaign settings are untouched.

---

## Timeline & measurement

| Date | Milestone |
|------|-----------|
| April 1, 2026 | Baseline captured. Changes begin on enriched group. |
| April 8, 2026 | Week 1 check - confirm GMC picked up all changes |
| April 29, 2026 | Week 3 read - compare enriched vs. control impressions |

**What we're measuring:**

- **Paired products:** Did the enriched products gain more impressions than their matched counterparts over the same 28-day window?
- **Zero-impression products:** Did any enriched products begin appearing in the index?

Results will be shared at the week 3 read.

---

*Questions? Reach out to Ohav (ohav@getfishbone.ai) or Avishay (avishay@getfishbone.ai).*
