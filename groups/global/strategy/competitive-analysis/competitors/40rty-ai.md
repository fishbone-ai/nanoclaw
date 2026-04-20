# 40rty AI (Agent IQ)

Last updated: 2026-03-09

## Links

- **Website:** https://40rty.ai/
- **Shopify app:** https://apps.shopify.com/fourty-ai
- **LinkedIn:** https://www.linkedin.com/company/40rty-ai/

## Overview

Shopify app that audits and optimizes product catalogs for AI agent discovery (ChatGPT, Gemini, Claude). They brand themselves as "Agentic Commerce Management for Shopify."

**Company:** Tuki
**HQ:** Tel Aviv, Israel
**Launched:** October 2025
**Platform:** Shopify only
**Reviews:** 8 reviews, 5.0/5 rating (as of March 2026)
**Key person:** Yoav Avinoam (LinkedIn)

## Pricing

| Plan  | Price     | SKU limit  | Key features                                  |
|-------|-----------|------------|-----------------------------------------------|
| Free  | $0/mo     | 3 queries  | Basic audit, product listings view             |
| Small | $79/mo    | 500 SKUs   | Competitor tracking, intent generation         |
| Pro   | $199/mo   | 2,000 SKUs | AI-powered fixes, real-time scoring            |
| Grow  | $499/mo   | Unlimited  | Dedicated account manager, custom views        |

## What they do

- **Catalog audits** -- analyze product attributes, taxonomy, titles, descriptions, imagery
- **AI optimization** -- generate and apply AI-suggested improvements to product metadata
- **Query testing** -- run real shopper intent queries to test visibility in AI results
- **Competitor tracking** -- monitor how competing brands appear in AI search results
- **Knowledge base** -- create FAQ sections for AI agent policy answers
- **Intent lab** -- generate conversational queries from real search data

Key detail from their website: "recommends what to fix and why, but never edits your listings automatically -- you stay in control." This suggests they're advisory, not hands-on.

## What customers say (Shopify reviews)

**Positive signals:**
- "One click installation", "easy to use" -- low friction onboarding (Dogit, Israel, 3 months using)
- "Actually getting AI sales" after applying recommendations (Yona USA, 13 days using)
- "Mapped catalog for agentic storefronts", now appearing in top recommendations (Dear Perli, 6 days using)
- Concrete, actionable fixes -- not vague SEO advice (Replay Jeans, Israel, 22 days)
- Goes beyond standard SEO practices (Shiree Odiz, 2 days using)

**Notable patterns:**
- Most reviewers are US-based, with a couple of Israeli stores (Dogit, Replay Jeans)
- Usage duration is very short -- most reviews after days or weeks, not months
- Reviews feel somewhat thin -- 8 five-star reviews from early adopters, some after just minutes/days
- No negative reviews yet, but sample size is tiny
- Mix of fashion (Replay Jeans, Knix, Dear Perli) and other verticals

**What's missing from reviews:**
- No mention of measurable ROI numbers (traffic, revenue lift)
- No reviews from merchants with large catalogs (10k+ SKUs)
- No mention of bulk operations or automation at scale
- No discussion of data accuracy or quality issues

## Known customers and partners

Sources: Shopify app reviews + partner logos on 40rty.ai website.

### Website partner logos

These appear in an "Our Partners" section on 40rty.ai. Unclear if partners means customers, integrations, or affiliates.

| Brand | Category | Notes |
|-------|----------|-------|
| True Classic | Men's basics/apparel | Large DTC brand, ~$250M+ revenue |
| Trestique | Beauty/cosmetics | Clean beauty brand, has AI shade quiz |
| PaperWallet | Accessories | Slim wallets, smaller brand |
| Knix | Intimates/apparel | Canadian DTC brand, also left a Shopify review |
| Boa Ideas | Unknown | Could not find more info |
| CQL | Agency | "The Unified Commerce Agency" -- likely an agency partner, not a merchant customer |
| Dataworks | Unknown | Likely a tech/data partner |
| New York & Company | Women's fashion | Major US retail brand -- would be a significant logo if real customer |

### Shopify app reviewers

8 reviews total as of March 2026. All 5 stars.

| Store | Location | Category | Time using | Key quote |
|-------|----------|----------|------------|-----------|
| Dugit (דוגית) | Israel | Diving/water sports | 3 months | "One click installation", "easy to use" |
| Knix Canada | Canada | Intimates/apparel | ~2 months | "Simple" AI audits, wants more features |
| Yona New York | USA | Plus-size fashion | 13 days | "Actually getting AI sales" |
| Dear Perli | USA | Kids' clothing/blankets | 6 days | "Mapped catalog for agentic storefronts" |
| Replay Jeans | Israel | Denim/fashion (global brand) | 22 days | Intent libraries and actionable fixes |
| Shiree Odiz | USA | Luxury diamond jewelry | 2 days | "Clean audit tool", beyond standard SEO |
| Maison Menashe | USA | Unknown | Unknown | "Straightforward" audit, good support |
| Panim | USA | Unknown | 5 minutes | Immediate positive impression |

### Observations

- **Knix** appears both as a website partner and a Shopify reviewer -- likely a real customer
- **True Classic** and **New York & Company** would be significant logos if they're actual customers (both are large brands)
- **CQL** is an agency -- suggests 40rty may have an agency channel strategy
- Customer base skews fashion/apparel, with a couple of Israeli stores
- Most reviewers used the app for days or weeks, not months -- still early
- **Nora Maxim** appears in a testimonial on the website claiming "catalog readiness improved by 85%, AI agent recommendations 3x more" -- almost certainly fake. "נורא מקסים" is a Hebrew expression meaning "terribly lovely" -- likely an inside joke from the founders, not a real brand

## Strengths

- Live and in market with paying customers
- Nailed the Shopify app store distribution channel
- "Agentic commerce" positioning is sharp and timely
- Low-friction onboarding (one-click install, no theme changes)
- Israeli founders with likely local network access

## Weaknesses

- Shopify-only -- no Magento, WooCommerce, custom platforms
- Self-serve SaaS, limited depth per customer
- SKU cap at 2,000 on Pro tier -- mid-market gap
- Advisory model ("recommends but never edits") -- merchant still does the work
- Tiny customer base (8 reviews in 5 months)
- No evidence of deep enrichment (content generation, attribute filling)

## Technical architecture (from hands-on testing 2026-03-09)

### Stack
- **Backend:** Gadget.app (`fourty-ai.gadget.app`) -- a Shopify-focused app development platform
- **Data source:** Shopify Catalog API (`discover.shopifyapps.com/global/v2/search`) -- NOT ChatGPT, Gemini, or any external AI search engine
- **Help center:** Intercom (`intercom.help/40rtyai/en/`)
- **App name in Shopify:** "40RTY: chatGPT catalog audit" -- misleading, since the actual search uses Shopify's index

### How "Agentic Catalog" search works
- Queries hit `fourty-ai.gadget.app/api/catalog/search` which proxies to Shopify's Catalog API
- Results come from Shopify's global product discovery index (same index powering Shop app, Shopify Copilot, and third-party agents via MCP)
- Products from any live Shopify store appear -- not just the merchant's own catalog
- Dev stores don't appear in this index (0% visibility for test store)
- The enriched fields in results (`uniqueSellingPoint`, `topFeatures`, `techSpecs`, `attributes`, `description`) are marked as **"Inferred"** in Shopify's own API docs -- meaning Shopify's AI generates them, not 40rty
- 40rty's "How Agents Choose" panel is essentially a visualization of Shopify's own Catalog API response fields
- API limit is hardcoded to 10 results (Shopify's Catalog API max is also 10)

### Catalog Health Tracker -- how scoring actually works
- Scoring is almost entirely driven by **Shopify taxonomy category specificity**
- A dress categorized as "Camera" gets Excellent because the category is specific -- no validation that the category matches the actual product
- Products without any category are Red
- Products with a generic category (e.g., "Gift Cards") are Poor/Yellow
- Products with a specific leaf-level category get Excellent/Green
- **Description quality, tags, images, SEO fields are NOT meaningfully weighted** -- our degraded CSV products (with stripped descriptions and tags) all scored the same as intact ones
- The responsibility for correct categorization is on the store owner; 40rty doesn't validate

### Product Audit page (now "Products Audit")
- Per-product view shows green/yellow/red/blue (uncategorized) status
- Primary focus is taxonomy -- uncategorized products dominate the view
- "Fix Product" button opens Shopify's native product edit modal -- no AI suggestions at any tier (tested on highest tier). Help docs describe an AI enrichment flow (suggest categories, color, size, material, style, "Accept All" button) that does not exist in the product -- either unshipped or broken
- **Taxonomy depth check is flawed:** checks category depth level (wants 3+ levels) rather than checking if you reached a leaf node. A leaf category like "Electronics > Speed Radars" still gets flagged for being only 2 levels deep. A mid-level category 3 levels deep passes even if more specific children exist
- **No category-product match validation:** "Speed Radars" on a skirt doesn't trigger any mismatch warning
- Filtering by quality tier, product status (published/draft/archived), and name search

### Product Analysis page (docs: "AgentIQ Product Feed")
- Takes a search query and evaluates how well your products match that intent
- Uses **gpt-4o-mini** (cheapest OpenAI model) for real-time analysis (~14s per product)
- Scores four dimensions per product: Tags (0-5), Metadata (0-5), Text (0-5), Images (0-5)
- Overall score is a weighted combination (e.g., 8.9/100 for a near-empty listing)
- Extracts "search query attributes" from the query and checks if product data contains matching terms
- **Recommendations are keyword stuffing:** for query "best selling items," it suggests adding "best seller" tags, putting "best selling items" as product type, including "best seller" in title/description. This is old-school SEO thinking, not real AI optimization
- Image analysis is superficial -- flags "image does not clearly depict a best-selling item" with 50% confidence
- Still no category-product mismatch detection -- Speed Radar skirt passes without any warning
- Analyzed only 4 of 32 products (likely tier/quota limit)
- Marked as BETA in the UI

### Competitor Feed page
- Side-by-side comparison of your store vs up to 3 competitors for a given query
- Competitors can be auto-detected (unclear mechanism -- possibly from Catalog API results for tracked queries) or manually added by domain URL
- Shows per-store: alignment score, confidence score, filter usage, product rankings
- "See AI Audit" button on competitor products -- likely same gpt-4o-mini analysis applied to their listings
- Docs say AI can "use native store filters, simulating smart agent behavior"
- Auto-detected competitors appear to come from Catalog API results for similar products (showed snowboarding stores matching default dev store theme)
- AI Audit modal is a raw data dump: pulls competitor product data via Shopify Storefront/Catalog API, shows all fields (file IDs, image URLs repeated 3x, product GIDs), plus a one-sentence scoring explanation
- Scoring is literal keyword matching -- "gift card" query on a product with type "Gift Card" scores 1.000 with analysis "Title and product type 'Gift Card' perfectly match intent"
- Has "Legacy Rankings" and "Composite Score" visible side by side -- suggests they iterated on scoring but kept old system visible
- "Dynamic Fields from MCP" section confirms they read Shopify MCP/Storefront data (product_type, etc.)
- Modal UX is poor -- unformatted data dump, not a designed experience

### Intent Libraries page
- Generates natural language search prompts that represent how real shoppers might query AI agents
- Auto-generates 20 prompts on onboarding based on store data (again, used dev store defaults -- all snowboard/gift card queries, not apparel)
- Prompts organized by Category (e.g., "Gift Cards", "Snowboard Accessories") and Sub-intent (e.g., "by budget", "by vendor", "by trip/season prep")
- Three external sources for generating more prompts: website scraping, CSV upload (e.g., Google Search Console data), subreddit scraping
- Subreddit source requires context instructions to filter noise
- Generated prompts are meant to be copied into the Agentic Catalog page to test product visibility -- manual copy/paste workflow, no direct integration
- This is the most conceptually interesting feature -- closest to real intent research. But the execution is disconnected from the rest of the app (no auto-testing, no tracking over time from this page)

### Tracked Queries
- Auto-generates 10 queries based on store data (appears to use default Shopify theme data, not imported products)
- Queries did NOT regenerate after importing apparel CSV -- still showed snowboard/ski wax queries from the default dev store theme
- Source icon is Shopify (green bag) -- all queries test against Shopify's Catalog API
- "Mentioned" = how many times your store appeared in results (0/1 for dev store)
- "Alignment" = how well your catalog data matches the query
- Custom query creation broken on dev store ("Shopify API key not found" error)

### Product Leaderboard
- Only shows products that actually appear in Shopify's global index
- Only Gift Card showed up (1 product, 10% of queries)

### Agentic Catalog page
- Browse/search across Shopify's entire global catalog
- Shows competitors' products with enriched data panel
- Brand filter shows percentage breakdown of results by store
- Your store appears as "Test store (You)" at 0%
- GET requests couldn't be replayed outside the app (session-bound or token-protected)

## Weaknesses

- Shopify-only -- no Magento, WooCommerce, custom platforms
- Self-serve SaaS, limited depth per customer
- SKU cap at 2,000 on Pro tier -- mid-market gap
- Advisory model ("recommends but never edits") -- merchant still does the work
- Tiny customer base (8 reviews in 5 months)
- No evidence of deep enrichment (content generation, attribute filling)
- **Health scoring is taxonomy-only** -- doesn't validate category accuracy, doesn't weight description quality, tags, or SEO fields
- **Misleading framing** -- app is called "chatGPT catalog audit" but searches Shopify's own catalog index, not ChatGPT
- **Enriched data shown in "How Agents Choose" comes from Shopify's API**, not 40rty's own AI -- their value-add is the visualization/framing, not the enrichment itself
- Auto-generated queries don't update when catalog changes
- Dev store experience is buggy (custom queries broken, products don't appear in global index)

## Open questions

- [ ] How deep does their "AI-powered fixes" actually go? Is it generating content or just suggesting tweaks?
- [x] What does their actual output look like? Install and test with a demo store. -- **Done, see technical architecture above**
- [ ] Are Dogit and Replay Jeans paying customers or design partners?
- [ ] How is Tuki funded? Team size?
- [ ] Are they building toward a platform play or staying Shopify-native?
- [ ] Do their paid tiers actually edit product data, or just recommend changes?
- [ ] What does the Product Audit page flag beyond taxonomy? (need to test with categorized products)
- [ ] How do Intent Libraries and Competitor Feed pages work? (testing in progress)
