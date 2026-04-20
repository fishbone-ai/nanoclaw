# DAFNI Hair — Catalog Enrichment Experiment

**Date:** 2026-04-05
**Client:** DAFNI Hair (dafnihair.com)
**Objective:** Measure whether enriching product catalog data (descriptions, metafields, structured attributes) improves visibility in Google Shopping, AI Mode, and ChatGPT Shopping.

## Design

Matched-pair test/control experiment. Test products receive enriched catalog data; control products remain unchanged.

### 4 Matched Pairs (8 products)

Pairs were validated against three baseline signals (impressions, clicks, Shopify sales). Pairs where historical clicks or sales differed by ~2x+ were excluded as confounded by pre-existing product strength differences.

| Pair | Tier | Category | Test | Control | Imp Ratio | Sales Ratio |
|------|------|----------|------|---------|-----------|-------------|
| 1 | Gold standard | Klix Minimalist Singles | Amber (3,552 imp, $2,420) | Black (3,561 imp, $2,438) | 1.0x | 1.0x |
| 2 | Credible | Bows | Black (6,969 imp, $18,257) | Rose Gold (10,922 imp, $15,001) | 1.6x | 1.2x |
| 3 | Directional only | Chunky Bows | Lavender (589 imp, $3,082) | Pearl White (207 imp, $2,201) | 2.8x | 1.4x |
| 4 | Directional only | Hair Care Kits | Ready to go (95 imp, $0) | Urban Edit (35 imp, $0) | 2.7x | — |

**Balance:** Test 11,205 imp vs Control 14,725 imp (1.31x) | Test $23,759 vs Control $19,640 (1.21x)

**Confidence tiers:**
- **Gold standard** (Pair 1): Nearly identical on all baseline metrics. Primary evidence for causal claims.
- **Credible** (Pair 2): Good match but test product has higher baseline CTR — enrichment lift must exceed this pre-existing advantage.
- **Directional only** (Pairs 3–4): Small absolute numbers. Useful for pattern confirmation, not standalone evidence.

### Excluded Pairs

3 within-category pairs were dropped after sales/clicks analysis revealed pre-existing product strength confounds:

| Dropped Pair | Category | Reason |
|---|---|---|
| Icon Sets (Iconic Edit vs Urban Oasis) | Klix Icon Sets | 5.7x click ratio, 4.2x sales ratio |
| Icon Sets (Sandstone vs Iconic Edit Mini) | Klix Icon Sets | 3x click ratio, 2.4x sales ratio |
| Tools (Power vs Muse) | Tools | 2.8x sales ratio, inverted click pattern |

4 cross-category pairs were also excluded earlier for mixing product types.

### Part B: Zero-Impression Bootstrap

No eligible zero-impression products — all active products have GMC traffic.

## Measurement Plan

- **Primary metric:** Impressions change (28-day post vs 28-day baseline)
- **Secondary metrics:** Clicks, CTR, purchases, Shopify sales
- **Baseline period:** GMC impressions/clicks Mar 7 – Apr 3, 2026 (28 days); Shopify sales Mar 5 – Apr 4, 2026 (30 days)
- **Measurement period:** TBD (recommend 28 days post-enrichment)
- **Success criteria:** Test group shows meaningful lift in impressions vs control group
- **Interpretation guidance:** Only Pair 1 supports causal claims. Pair 2 is supportive with caveats. Pairs 3–4 are directional. If all four pairs show the same direction of effect, that strengthens the overall signal despite individual pair weaknesses.

## Data Sources

| File | Source | Description |
|------|--------|-------------|
| `source_data/shopify/products_export_1.csv` | Shopify Admin | Full product catalog (54 products, 283 variant rows) |
| `source_data/gmc/Performance_2026-04-04_10-50-50.csv` | Google Merchant Center | 28-day performance (Mar 7 – Apr 3, 2026), 34 products |
| `source_data/gmc/products_2026-04-04_10-48-11.zip` | Google Merchant Center | Full product feed dump (36 products) |
| `source_data/shopify/Total sales by product title - 2026-03-05 - 2026-04-04.csv` | Shopify Analytics | 30-day sales by product title |

## Output Files

| File | Description |
|------|-------------|
| `experiment_assignment.csv` | 4 pair assignments with test/control groups, confidence tiers, and baseline sales |
| `experiment_zero_imp_assignment.csv` | Part B (empty — no eligible zero-imp products) |
| `experiment_gmc_baseline.tsv` | Combined baseline: Shopify attributes + GMC feed data + aggregated performance + sales |

## Exclusions

**Product-level (30 excluded):**
- **Draft products** (13): Old versions, out-of-stock items, unpublished products
- **Copy/temp products** (9): Shopify handle ending in `-copy`, titles with `.temp`
- **Gift cards** (2): DAFNI Gift Card Green, Purple
- **Bundles/packs** (4): Multi-product packs (can't measure individually)
- **Duplicate titles** (2): Same title across multiple handles (share one GMC entry)

**Pair-level (7 pairs excluded from original 11):**
- **Cross-category** (4 pairs): Mixing product types weakens causal inference
- **Pre-existing confounds** (3 pairs): Historical clicks or sales differed by ~2x+, indicating intrinsic product strength differences that would confound treatment measurement

## Data Processing Notes

1. **Shopify deduplication:** 283 rows deduplicated to 54 products by Handle (first row per handle)
2. **GMC aggregation:** Performance CSV had 1 row per title (no multi-surface split in this export). Aggregated defensively.
3. **Title matching:** Normalized (lowercase, collapsed whitespace, stripped unicode quotes). Manual match added for "DAFNI Power Hair Straightening Brush" ↔ "DAFNI Power - The Original Hair Straightening Brush"
4. **Product type normalization:** Normalized to title case. Empty types derived from Product Category taxonomy path.

## Column Naming Convention (baseline TSV)

All columns prefixed by source system:
- `shopify:*` — from Shopify product export
- `gmc:*` — from GMC product feed
- `aggregated_*` — derived from GMC performance (summed across all rows per product)
- `experiment_*` — experiment assignment metadata
