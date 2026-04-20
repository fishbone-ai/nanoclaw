# GMC Status Check -- 2026-04-13

Review of TEST products on Google Merchant Center, checking attribute propagation and listing health.

## Critical

### Citron Velvet Knot Pillow -- price showing $0
- **URGENT**: Product price displays as $0 on the live website. Customers can literally buy it for free.
- We did NOT change this -- our Shopify access doesn't include price editing, and it's disabled in our product editing permissions.
- Neta needs to fix this immediately.
- US listing visibility set to "limited" due to missing shipping info (see shipping issue below).
- GMC shows two listings: one for US, one for rest of world.

### Shipping issue (US) -- affects multiple products
- **Citron Velvet Knot Pillow**: "Missing or incorrect shipping costs [shipping] in [Shopping_ads] [US]"
- **Burgundy Velvet Knot Pillow**: Same error
- Shipping IS configured in Shopify, but GMC still flags it as missing for US.
- Other products (e.g. (M) Ivory Knot Ottoman, #3) don't have this problem -- unclear what's different.

## Product Highlights -- inconsistent propagation

We set product highlights on all TEST products (2026-04-06), but they're showing up inconsistently on GMC.

| # | Product | Highlight on GMC? | Notes |
|---|---------|-------------------|-------|
| 3 | (M) Ivory Knot Ottoman | No | Other attributes updated fine. Suspect format issue (see below) |
| 4 | Mauve Velvet Woven Bench | No | Same -- missing highlight |
| 5 | Set Of 3 Baskets - Stone (skipped, out of stock) | -- | -- |
| 6 | (L) Hull Basket in Graphite Ultra suede | **Yes** | Shows: "Medium boat-inspired storage basket in graphite ultra suede, a sculptural organizer for any room." |
| 7 | (M) Hull Basket in Cobalt Ultra suede | No | Looks identical to others on Shopify side, no idea why |
| 8 | (L) Truffle Knot Ottoman | Mixed | US listing (with sale price) has it, rest-of-world listing doesn't |

### Likely cause: wrong format
GMC spec for `product_highlight`:
- **Minimum 2 highlights** (we sent a single string)
- Each highlight: 1-150 characters
- It's a repeated field -- should be multiple entries, not one combined string

We need to reformat highlights as 2+ separate entries per product.

### #8 oddity -- sale price mismatch
- (L) Truffle Knot Ottoman: US listing still shows a sale price, rest-of-world doesn't
- Shopify shows the discount was already removed
- GMC listing didn't sync the removal properly
- The US listing (with stale sale price) has product highlights; the other doesn't

## Reviewed (continued)

### #9 Truffle Velvet Woven Stool
- Product highlight shows on **both** US and non-US listings
- GMC warning: "One or more of the products in your product data has less than the minimum required number of values for attribute [product_highlight]" -- confirms the format issue (we're sending 1 highlight, minimum is 2)
- **Shopify category attributes not syncing**: chair features, upholstery material, seat type are NOT appearing on GMC (not even under "raw data source attributes"). Color DOES appear. All were set in the same Shopify category attributes window. Unclear why color syncs but the others don't.

### #10 Set Of 3 Baskets - Graphite
- US listing shows sale price ($446 vs $595 compare-at) -- but Shopify has no compare-at price set. Stale/phantom sale, same pattern as #8.
- Non-US listing: no sale price (correct)
- Product highlight: only on non-US version, not on US -- opposite of #8's pattern

### #11 (L) Mauve Knot Ottoman
- Stale sale price on **both** US and non-US listings -- Shopify shows no sale. Third product with this issue (#8, #10, #11).
- Color (Mauve) is showing -- our update propagated
- Possible that updates are just lagging; sale removal may sync eventually

## Not yet reviewed

12. (L) Ivory Knot Ottoman
10. Set Of 3 Baskets - Graphite
11. (L) Mauve Knot Ottoman
12. (L) Ivory Knot Ottoman
13. Burgundy Woven Stool
14. Petrol Velvet Woven Stool
15. (M) Hull Basket in Graphite Ultra suede
16. (M) Burgundy Knot Ottoman
17. (M) Hull Basket in Stone Ultra suede
18. (S) Hull Basket in Stone Ultra suede
19. Sterling Grey Velvet Knot Pillow

## Action items

1. **[URGENT] Neta**: Fix Citron Velvet Knot Pillow price ($0 on live site)
2. **Investigate**: Why US shipping is flagged on some products but not others
3. **Fix**: Reformat product highlights to meet GMC minimum of 2 entries per product
4. **Investigate**: Why highlight propagation is inconsistent (6 has it, 7 doesn't, 8 is split)
5. **Investigate**: #8 (L) Truffle Knot Ottoman sale price sync issue -- may need manual GMC update or Shopify re-save
6. **Continue**: Review remaining 11 products (#9-19)
