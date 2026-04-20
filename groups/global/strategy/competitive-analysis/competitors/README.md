# Competitive Landscape

Last updated: 2026-03-15

## How to use this folder

One file per competitor. Each file covers what they do, pricing, strengths, weaknesses, and open questions. Update as we learn more.

## Key conclusions

**The market is real but early.** 40rty AI launched Oct 2025 and has 8 paying customers in 5 months. Retailers are actively looking for AI agent visibility tools. This validates our thesis -- but also means we're not alone.

**Audit vs. enrichment is the central positioning gap.** Current competitors (40rty AI) tell merchants what's wrong with their catalog data. They score, diagnose, and recommend. But the merchant still has to do the actual work. Fishbone's opportunity is to be the one that actually fixes the data -- generate content, fill attributes, structure everything for AI consumption.

**Lily AI is the benchmark.** They already do what Fishbone is building -- attribute enrichment, trend alignment, generative product copy, multi-channel optimization for AI discovery. They explicitly market "For Humans & Machines." They're enterprise-first and expensive, which leaves mid-market open. But they're ahead, and their proprietary training data is a real moat.

**Pixyle.ai has the deepest taxonomy in fashion.** 20,000+ searchable attributes and real enterprise case studies (Depop, Otrium, Thrifted). If Fishbone targets fashion/apparel, Pixyle is a direct threat. But they're fashion-specific and Europe-focused -- other verticals and US market are open.

**Describely is the accessible content generator.** Target Australia does 1,000+ descriptions per week at 98% accuracy. Describely is a useful tool but shallow -- it generates copy, not structured attribute intelligence. If Fishbone's MVP looks like Describely, we'll be benchmarked on price, and we'll lose. We need to go deeper.

**Shopify is served, everything else is open.** 40rty AI is Shopify-native. Merchants on Magento, WooCommerce, BigCommerce, or custom platforms have no equivalent tool. Mid-market merchants with 10k+ SKUs are also underserved (40rty caps at 2,000 SKUs on Pro tier).

**PIM platforms are not the threat today, but watch them.** Salsify and Akeneo are adding AI enrichment features to their governance platforms. If they ship generative AEO content and bundle it free to their existing bases, that's a major distribution problem for standalone enrichment tools. Both move slowly -- monitor quarterly.

**Trustana is a direct catalog enrichment competitor with active go-to-market.** SE Asia-based, targeting mid-market and enterprise retailers globally. Their "5 pillars of AI readiness" (completeness, accuracy, consistency, imagery, governance) is their sales framework. Approach is "ML for speed, human validation for quality" -- not agentic. They're investing in content marketing (gated ebook, LinkedIn campaigns) suggesting active pipeline building. Their ceiling is faster human-supervised enrichment; they're not building toward autonomous catalog management.

**Yotpo is entering the AI discoverability space with a two-sided approach.** A 10-person CEO-level skunkworks unit is building catalog enrichment + review amplification (incentivizing customers to post positive reviews on Reddit and other platforms to seed third-party signals). Launching at Shoptalk Vegas, end of March 2026. With 35,000+ existing customers and a real review moat, they have the distribution to make this dangerous fast. The catalog enrichment side is unproven -- their core muscle is reviews, not data enrichment. Watch what they actually demo.

**No one is doing deep enrichment for agentic commerce yet.** The field splits into: audit tools (40rty AI), content generators (Describely), deep enrichment platforms (Lily AI, Pixyle.ai -- both strong but not explicitly agent-first), and PIM/governance (Salsify, Akeneo). Nobody is building a purpose-built AI agent-readiness layer from scratch with the agentic commerce framing as the core thesis.

**The agentic commerce stack is being built in layers.** Nekuda AI (backed by Visa, Amex, Madrona -- $5M seed) is building the transaction/checkout infrastructure for AI agents. 40rty AI handles audit/diagnostics. Lily AI and Pixyle do enrichment without the agent-specific framing. Nobody owns the "AI agent-ready catalog" position with that as the explicit pitch. This is Fishbone's lane.

**Enterprise is covered, mid-market is not.** Adobe LLM Optimizer starts at ~$115k/year and targets $100M+ revenue brands. Lily AI and Salsify are also enterprise-focused. Mid-market merchants who care about AI visibility but can't afford enterprise tooling are unserved.

## Strategic directives

1. **Don't compete on audit -- compete on enrichment.** Scoring and diagnostics are table stakes. Our wedge is doing the actual work of improving catalog data.
2. **Go deeper than description generation.** Describely generates copy; Fishbone should generate structured, attribute-rich, AI-agent-readable catalog data. Depth is the differentiator.
3. **Own the "AI agent-ready catalog" position.** Lily and Pixyle do enrichment but don't lead with agentic commerce. This framing is ours to take.
4. **Go where Shopify apps can't.** Multi-platform support and large catalog handling (10k+ SKUs) are immediate differentiators.
5. **Target mid-market.** Enterprise is locked up. The $20k-$80k/year segment is underserved across the board.
6. **Watch PIM convergence.** If Salsify or Akeneo ships AEO-specific enrichment features and bundles them, the window for a standalone enrichment tool narrows fast.
7. **Test the competition hands-on.** Install 40rty AI on a demo Shopify store. Get a Describely trial. Understand exactly what they deliver before finalizing positioning.
8. **Watch Yotpo's Shoptalk launch (March 2026).** Their demo will tell us how deep the catalog enrichment goes. If it's shallow, their threat is mainly distribution. If it's deep, they're a direct competitor with a massive head start on distribution.
8. **Explore partnerships with infrastructure players.** Nekuda (checkout) needs merchants with good data. PIM platforms (Akeneo, Salsify) need enrichment that feeds into their systems. We could be the recommended enrichment layer for both.

## Competitors tracked

| Competitor | Type | Platform | Status | Threat Level | File |
|------------|------|----------|--------|--------------|------|
| Lily AI | Catalog enrichment for AI discovery | Platform-agnostic | Live, enterprise | High | [lily-ai.md](lily-ai.md) |
| Pixyle.ai | AI product tagging + attribute enrichment | API + no-code | Live, enterprise | High (fashion) | [pixyle-ai.md](pixyle-ai.md) |
| Describely | AI product description generation | Shopify, WooCommerce, Wix, Akeneo | Live, mid-market | Medium | [describely.md](describely.md) |
| 40rty AI | Catalog audit and AEO | Shopify | Live (Oct 2025) | Medium | [40rty-ai.md](40rty-ai.md) |
| Nekuda AI | Agentic commerce infrastructure | Multi-platform | Live, $5M seed (May 2025) | Low (different layer) | [nekuda-ai.md](nekuda-ai.md) |
| Salsify | Enterprise PIM + AI automation | Any | Live, $200M+ funded | Medium (watch) | [salsify.md](salsify.md) |
| Akeneo | Enterprise PIM + Product Cloud | Any | Live, $120M+ funded | Medium (watch) | [akeneo.md](akeneo.md) |
| DataFeedWatch | Feed management + AI content | 2,000+ channels | Live | Low (adjacent) | [datafeedwatch.md](datafeedwatch.md) |
| ProductRise | Google organic Shopping rank tracker + supplemental feed optimizer | GMC / Google Shopping | Live, free tier | Low (adjacent) | [productrise.md](productrise.md) |
| BizNet AI | Catalog enrichment for AI agents | Unknown | Pre-traction (founded 2026) | Low | [biznet-ai.md](biznet-ai.md) |
| Yotpo | AI discoverability via catalog enrichment + review amplification | Shopify + multi-platform | Stealth (launching March 2026, Shoptalk Vegas) | High | [yotpo.md](yotpo.md) |
| Adobe LLM Optimizer | GEO / AI visibility monitoring | Any website | Live (Oct 2025), $115k+/yr | Low (different layer) | [adobe-llm-optimizer.md](adobe-llm-optimizer.md) |

## Not yet researched

- GoDataFeed (similar to DataFeedWatch -- feed management + AI content)
- Agencies offering AEO or catalog enrichment as a service
- Adobe Commerce Optimizer (separate from LLM Optimizer -- may include catalog enrichment features)
- Lily AI customer case studies (need deeper research into named brands and pricing)
- Pixyle.ai non-fashion verticals and US market presence

| Hypotenuse AI | AI catalog enrichment + content generation | Shopify, WooCommerce, Akeneo, CSV | Live, YC-backed, ~$2.8M ARR | High | [hypotenuse-ai.md](hypotenuse-ai.md) |
| ANGLERA | AI product data enrichment (agentic-first) | API, marketplace integrations | Live (Aug 2025), YC W25 | High | [anglera.md](anglera.md) |
| CommerceClarity | AI OS for catalog operations | API, multi-channel | Pre-seed (€2.7M, Nov 2025) | High | [commerce-clarity.md](commerce-clarity.md) |
| Merchkit | Catalog automation + merchandising + images | Shopify, Amazon, Walmart | Pre-seed ($2M CAD, Mar 2025) | High | [merchkit.md](merchkit.md) |
| Profound | AI brand visibility / GEO analytics | Platform-agnostic | Series C ($96M, $1B valuation) | Medium (adjacent) | [profound.md](profound.md) |
| Bluefish AI | GEO / AI commerce for enterprise | Platform-agnostic | Series A ($24M, NEA) | Medium (adjacent) | [bluefish-ai.md](bluefish-ai.md) |
| Peec AI | AI search marketing / GEO analytics | Platform-agnostic | Series A ($29M, Singular) | Medium (adjacent) | [peec-ai.md](peec-ai.md) |
| Novi | Product data optimization for AI shopping | Platform-agnostic | Seed (Defy.vc) | Medium (adjacent) | [novi.md](novi.md) |
| Algomizer | GEO / catalog optimization for AI search | Platform-agnostic | Unknown (pivot from older co) | Low (adjacent) | [algomizer.md](algomizer.md) |
| Nectar Social | Social commerce / community AI | Instagram, TikTok | Seed ($10.6M, True/GV) | Low | [nectar-social.md](nectar-social.md) |

| channel3 | Universal AI product database / catalog API | API (developer-facing) | Seed ($6M, Matrix, YC, Dec 2025) | High (strategic) | [channel3.md](channel3.md) |
| Envive AI | Agentic commerce platform + ACP catalog enrichment | Multi-platform | Series A ($20M, Fuse/Point72/AI2, Sep 2025) | High | [envive.md](envive.md) |
| Cimulate | AI-native product search + catalog intelligence (acquired) | Salesforce Commerce Cloud | Acquired by Salesforce Feb 2026 | Low (post-acq) | [cimulate.md](cimulate.md) |
| Yext | Knowledge graph + agent-ready product catalog | Platform-agnostic | Public (NYSE: YEXT) | Medium (adjacent) | [yext.md](yext.md) |
| BRIJ | QR-code product experience + first-party data capture | Shopify, Klaviyo | Seed ($8M, Jun 2025) | Low | [brij.md](brij.md) |
| Trendage | AI fashion styling + catalog imagery generation | Fashion retailer APIs | Unknown (est. 2015) | Low | [trendage.md](trendage.md) |
| minivet.ai | GenAI video catalog content (acquired) | Flipkart-native | Acquired by Flipkart Dec 2025 | Low (post-acq) | [minivet.md](minivet.md) |
| Trustana | Catalog enrichment + data governance | Platform-agnostic | Live, SE Asia focus, active content marketing | High | [trustana.md](trustana.md) |
| Velou | Catalog enrichment + product graphs for agentic commerce | Platform-agnostic | Live, enterprise (100M+ products) | High | [velou.md](velou.md) |
| eLLMo | Catalog-to-agent structuring layer / agentic commerce trust layer | Platform-agnostic | Live (free PDP audit tool), funding unknown | High | [ellmo.md](ellmo.md) |
