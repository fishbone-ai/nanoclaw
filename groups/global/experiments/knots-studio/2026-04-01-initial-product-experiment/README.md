# Knots Studio -- Initial Product Enrichment Experiment

**Start date:** 2026-04-01
**Check-in (week 1):** 2026-04-08
**Read (week 3):** 2026-04-29
**Linear:** [FB-175](https://linear.app/fishbone/issue/FB-175) / [FB-176](https://linear.app/fishbone/issue/FB-176) / [FB-177](https://linear.app/fishbone/issue/FB-177)

---

## Hypothesis

Enriching a product's catalog data in Shopify (which syncs to GMC via the Google & YouTube app) increases its AI visibility in ChatGPT Shopping and Google AI Mode.

This is a test of Fishbone's core assumption (FB-121): that catalog quality improvements drive measurable AI search visibility gains.

---

## Baseline findings (2026-04-01)

Before any changes, the GMC data dump reveals significant gaps across all products:

| Field | State |
|-------|-------|
| Color | 40/42 products empty; 2 that have values contain SKU codes, not color names |
| Product type | 28/42 rows empty |
| Structured attributes (material, dimensions, etc.) | 100% empty |
| Brand | Inconsistently cased ("knots studio" vs "Knots Studio") |
| SEO titles | Mostly empty |
| Product highlight metafields | Not set on any product |

These gaps exist symmetrically across test and control groups, making the baseline clean for comparison.

---

## Two-part design

### Part A -- Paired test/control (15 pairs, 30 products)

Products selected from 28-day GMC analytics (aggregated across all surfaces/feed labels), matched by category with impression ratio ≤2.0x. Top 5% by impressions excluded as hero products.

| Pair | Test | Control | Category | Imp Ratio |
|------|------|---------|----------|-----------|
| 1 | Citron Knot Pillow (160) | Petrol Knot Pillow (221) | Knot Pillow | 1.4x |
| 2 | Burgundy Knot Pillow (307) | Ivory Knot Pillow (246) | Knot Pillow | 1.2x |
| 3 | Sterling Grey Knot Pillow (824) | Mauve Knot Pillow (762) | Knot Pillow | 1.1x |
| 4 | (M) Hull Basket Graphite (25) | (S) Hull Basket Graphite (25) | Hull Basket | 1.0x |
| 5 | (S) Hull Basket Stone (50) | (L) Hull Basket Stone (38) | Hull Basket | 1.3x |
| 6 | (M) Hull Basket Stone (130) | (M) Hull Basket Red Earth (178) | Hull Basket | 1.4x |
| 7 | (M) Burgundy Knot Ottoman (897) | (M) Mauve Knot Ottoman (751) | Medium Knot Cushion | 1.2x |
| 8 | (M) Ivory Knot Ottoman (943) | (M) Petrol Knot Ottoman (1,082) | Medium Knot Cushion | 1.1x |
| 9 | Mauve Velvet Woven Bench (4,741) | Burgundy Velvet Woven Bench (4,480) | Woven Bench | 1.1x |
| 10 | Petrol Velvet Woven Stool (28) | Mauve Velvet Woven Stool (43) | Woven Stool | 1.5x |
| 11 | Burgundy Woven Stool (276) | Citron Velvet Woven Stool (235) | Woven Stool | 1.2x |
| 12 | (L) Ivory Knot Ottoman (3,859) | (L) Citron Knot Ottoman (3,865) | Large Knot Cushion | 1.0x |
| 13 | (L) Mauve Knot Ottoman (5,530) | (L) Sterling Silver Knot Ottoman (4,621) | Large Knot Cushion | 1.2x |
| 14 | Set of 3 Baskets Stone (1,189) | Set of 3 Baskets Cobalt Blue (1,332) | Set of 3 Baskets | 1.1x |
| 15 | Set of 3 Baskets Graphite (3,213) | Set of 3 Baskets Red Earth (1,863) | Set of 3 Baskets | 1.7x |

Total balance: TEST 22,622 imp vs CONTROL 20,192 imp (1.12x).

Excluded hero products (>95th percentile): Citron Velvet Woven Bench (23,350), (L) Burgundy Knot Ottoman (19,114).

**Question:** Does enrichment improve visibility for products already in the index?

**Measurement:** 28-day impression delta (test vs control), week 3 vs baseline.

Full assignments: `experiment_assignment.csv`

---

### Part B -- Zero-impression bootstrap (3 pairs, 6 products)

Products confirmed active in GMC feed but with 0 **aggregated** impressions across all surfaces over 28 days.

| Pair | Test | Control | Category | Match quality |
|------|------|---------|----------|---------------|
| 1 | (L) Hull Basket Graphite | (L) Hull Basket Cobalt | Hull Basket | Same size (L), color differs only |
| 2 | (S) Hull Basket Cobalt | (S) Hull Basket Red Earth | Hull Basket | Same size (S), color differs only |
| 3 | Truffle Velvet Woven Stool | Ivory Velvet Woven Stool | Woven Stool | Same product type, color differs |

_Redesigned 2026-04-02 (Ohav approval): dropped (M) Hull Basket Cobalt and (L) Truffle Knot Ottoman -- size mismatch and cross-category pairing respectively. Swapped (L) Hull Basket Cobalt from TEST to CONTROL in pair 1 to achieve L vs L matching._

**Question:** Can enrichment bootstrap visibility from zero -- getting products into the index at all?

**Measurement:** Binary -- did any test products get impressions within 3 weeks? Compare to control.

Full assignments: `experiment_zero_imp_assignment.csv`

---

## Changes to apply (test group only, all done manually in Shopify)

All changes applied to the 19 test products (15 from Part A + 4 from Part B). Control group untouched.
Changes sync to GMC automatically via the Google & YouTube Shopify app.

### 1. Color (highest priority)
- Set the correct color name on each product (e.g. "Sterling Grey", "Petrol", "Burgundy")
- Currently blank on almost all products; this is a primary purchase-intent signal for home decor

### 2. Product type
- Fill where empty using the correct category label (e.g. "Woven Bench", "Knot Pillow")
- 28/42 GMC rows currently have no product_type

### 3. Brand
- Standardize to "Knots Studio" (capital K, capital S) across all test products
- Currently mixed between "knots studio" and "Knots Studio"

### 4. Structured attributes (Shopify taxonomy)
- Open each test product in Shopify and fill all suggested attributes for its product category
- Shopify taxonomy is Google-aligned -- use the attributes surfaced per listing (material, dimensions, pattern, etc.)
- None of these are currently set on any product

### 5. Description enrichment
- Rewrite descriptions to ~150-300 words, naturally structured
- Mention material, use case, dimensions, care instructions where relevant
- Current descriptions are short and generic (most are the same boilerplate across the category)

### 6. Product highlight metafields
- Create `mm-google-shopping.product_highlight` metafield on each test product
- Add 3-5 feature-focused bullet points per product (not marketing copy -- concrete features)
- None currently set

---

## Measurement protocol

### Baseline (captured 2026-04-01)
- GMC product dump: `source_data/gmc/products_2026-04-01_06-38-34.tsv`
- 28-day performance: `source_data/gmc/Performance_2026-04-01_06-06-06.csv` (Mar 4 -- Mar 31 2026)
- Experiment baseline (all 38 products + fields): `experiment_gmc_baseline.tsv`

### Week 1 check (2026-04-08)
- Confirm all changes were picked up by GMC (check diagnostics tab per product)
- Flag any sync errors or disapprovals
- Part B: did any zero-impression test products get any impressions at all?

### Week 3 read (2026-04-29)
- Export 28-day GMC performance ending 2026-04-29 (covers Apr 1 -- Apr 29, fully post-change window)
- Compare impressions: test vs control per pair (Part A)
- Part B: count test products with impressions vs control
- Manual spot checks: run standardized queries in ChatGPT and Google AI Mode, screenshot results

### Manual check queries
Define 1-2 queries per category before running checks. Run same account, same day each time.

---

## Source data

- `source_data/shopify/products_export_1.csv` -- full Shopify catalog export (2026-04-01)
- `source_data/gmc/Performance_2026-04-01_06-06-06.csv` -- GMC 28-day performance baseline. **Important:** GMC creates multiple rows per product (different surfaces, feed labels). SUM all rows per product title to get true impression counts.
- `source_data/gmc/products_2026-04-01_06-38-34.tsv` -- full GMC product dump (2026-04-01)
- `experiment_assignment.csv` -- Part A product assignments (impression counts are aggregated)
- `experiment_zero_imp_assignment.csv` -- Part B product assignments (3 pairs, updated 2026-04-02)
- `experiment_gmc_baseline.tsv` -- merged baseline: all 38 experiment products with Shopify (`shopify:`) + GMC (`gmc:`) fields + aggregated impression/click counts

---

## Notes

- **GMC impression aggregation:** The raw GMC performance export has multiple rows per product (Shopping tab, AI Mode, different feed labels). All impression/click counts in the assignment files are summed across all rows matching each product title. Always re-aggregate from the raw performance CSV for the week-3 read.
- **Duplicate Shopify product found:** `ivory-velvet-knot-pillow-new` and `truffle-velvet-knot-pillow-new` have identical titles ("Truffle Velvet Knot Pillow") and SKUs (10010Trf). This is a Shopify data quality issue -- they share the same GMC feed entry. The duplicate was excluded from the experiment (original pair 3 dropped, reducing Knot Pillow from 4 pairs to 3).
- Pair 15 (Part A) has the weakest impression match at 1.7x (Set of 3 Baskets) -- treat results there with extra skepticism
- The color and product_type gaps are more severe than expected; filling those alone may drive measurable change
- 7 products have 200+ impressions but 0 clicks across both groups -- likely organic listing impressions without click-through. Distributed symmetrically across test/control so it doesn't bias the experiment
- Supplemental feed approach was considered but dropped -- all changes go directly through Shopify
