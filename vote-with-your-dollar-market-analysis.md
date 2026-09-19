# Vote With Your Dollar: Market Analysis, Data Foundation, and Build Plan

*Draft v0.2, September 19, 2026*

---

## 1. The thesis

Every purchase is a transfer of money to a specific set of hands: a grower or maker, a cashier, a logistics contractor, a marketing agency, an executive comp package, and a pool of shareholders. Consumers have a strong intuition about this and almost zero visibility into it. The gap is the product.

The promise, in one sentence: **for any thing you want to buy, show you who makes it, who owns the people who sell it, where your dollar lands, and the closest option that does better.**

Three layers follow:

1. **A seller and maker graph** with location, ownership, and ethics attributes. This is the asset. Exposed as an MCP server so any assistant or app can call it.
2. **A penny ledger** that estimates the split of a dollar across the chain, with sources and confidence bands.
3. **A substitution engine** that takes an item or a list and returns the better option up the ladder, nearby.

Everything else (directories, swaps like water filtration over bottled water, the site itself) is a view onto those three.

## 2. The sourcing ladder

| Tier | Channel | Why it ranks here |
|---|---|---|
| 1 | Own garden | ~100% of value retained, zero transport |
| 2 | Community garden / gleaning / barter | Retained locally, builds commons |
| 3 | Direct from local farm or maker (stand, CSA, u-pick, farm web store) | Producer captures most of the dollar |
| 4 | Local co-op selling local goods | Producer captures most; margin goes to member-owners |
| 5 | Direct from non-local producer (mail order) | Producer captures most; transport penalty |
| 6 | Large chain selling local goods | Local producer paid, chain margin leaves the region |
| 7 | Co-op selling national goods | Margin stays local, chain is long |
| 8 | National chain, non-local whole goods | Long chain, extractive margin |
| 9 | National chain, processed, non-local | Longest chain, lowest producer share, highest brand/ad/exec load |

Keep three scores separate and never blend them into one number too early:

- **Channel score**: the ladder above. Where in the chain are you buying.
- **Ownership score**: who owns the seller and the maker. Individual, family, co-op, ESOP, B Corp, private equity, public with concentrated institutional holders.
- **Practice score**: certifications and disclosed practices (organic, fair trade, living wage, union, packaging).

A single blended "ethics grade" is what every competitor ships, and it is why none of them are trusted. Show the three, let the user weight them.

## 3. The worked example: tea

The tea example is useful because it shows why ownership has to be its own layer and why "USA grown" is not the same as "small."

- The Charleston Tea Garden on Wadmalaw Island, SC, is the largest working tea farm in the U.S., and American Classic Tea is marketed as the only tea made entirely from U.S.-grown leaves. That checks the "grown here" box hard.
- But the garden has been owned by the Bigelow family since 2003, after a court auction. Bigelow is 100% family-owned, roughly 350 employees, around $189M in annual sales as of 2020, and its main product lines are made from imported leaf, not Charleston leaf.

So the honest classification of a box of American Classic Tea is: **U.S. grown (verified), made on-site (verified), owned by a mid-size private family company (verified), no public shareholders (verified), not a small grower (verified).** That is a good buy on the ownership axis and a middling one on the "small producer" axis. Users deserve exactly that nuance, not a badge.

Meanwhile the actual small U.S. growers are nearly invisible to search: a few dozen farms, mostly organized under the U.S. League of Tea Growers, in the Carolinas, Mississippi, Alabama, Oregon, Washington, and Hawaii. Each needs verification, but candidates include Camellia Forest (NC), Great Mississippi Tea Co. (MS), Table Rock Tea (SC), Minto Island (OR), and several Big Island growers (HI). Nobody aggregates them with location, ownership, and a "made by the grower" flag. **That aggregation, done once and kept fresh, is the product.** Then repeat for honey, maple syrup, coffee roasters, cheese, flour, meat, soap, candles, clothing.

## 4. Market reality (condensed)

- Direct farm sales of food were $9.0 billion in 2020 across 147,000+ farms, with $2.9 billion direct-to-consumer and 78% of those farms selling only within 100 miles. Direct-to-consumer actually *slipped* from 2015 to 2020 while sales to institutions grew. Discovery is a real bottleneck; do not assume a rising tide.
- Boycott energy is cyclical and event-driven. The early-2026 Greenland crisis produced a surge of "boycott U.S. goods" apps in Europe. Those spikes bring traffic and churn hard.
- The attitude-behavior gap is the enemy. People say ethics matters and buy on price. Lead with swaps that *save* money (filter vs bottled water, bulk, secondhand, in-season) so the first thing the tool does is put $200 back in someone's pocket. Then earn the harder trade-offs.
- Realistic revenue pools, in order: donations and membership (Open Food Facts, Wikipedia model); a paid tier funded by users so brands cannot buy influence (Yuka model); data and API licensing to researchers, journalists, municipalities, and food-policy orgs; and affiliate, which is where the integrity conflict lives. Never paid placement.

## 5. Competitive landscape (condensed)

| Player | What it is | Gap |
|---|---|---|
| Buycott, Boycat, Boycott X, Made O'Meter | Barcode boycott scanners | Negative only, data rots, no "buy this instead" |
| Goods Unite Us | Political donation scores | One narrow signal, opaque sources |
| Open Food Facts | Open product database, nonprofit, MCP servers already exist | Dependency, not competitor. No ownership or location layer |
| Yuka | Health scoring, user-funded, refuses brand money | Best business-model analog, different axis |
| LocalHarvest, USDA Local Food Portal | Directories | Stale, no ownership, no routing, no substitution |
| EarthHero, Thrive, Grove, GOODEE | Curated ethical e-commerce | Merchants scoring what they sell |
| Ethical Consumer (UK), Good On You (fashion) | Editorial brand ratings | Paywalled or category-limited, no local layer, no API |
| EcoVadis, Sedex, Open Supply Hub, TrusTrace | B2B supply chain ESG | Enterprise-priced, invisible to consumers, but a data source |

**White space: no one has a seller graph that joins location + ownership + practices, and no one exposes it as infrastructure.** Everyone ships a score. You ship an accounting and an API.

## 6. What exists to build on

This is the core of the refinement. Sorted by what each source gives you, with cost and license, because license decides the architecture.

### 6a. Places (where sellers physically are)

| Source | What you get | Cost | License / catch |
|---|---|---|---|
| **Overture Maps Places** | 50M+ global POIs, monthly GeoParquet on AWS. Name, category, address, coords, phone, website, `brand` field, confidence score, per-field provenance. Sources include Meta, Microsoft, BrightQuery, AllThePlaces, PinMeTo | Free | CDLA-Permissive 2.0. No share-alike. **This is the spine.** The `brand` field is a free first-pass "chain vs independent" signal |
| **OpenPOIs** (Henry Spatial Analysis) | U.S. conflation of OSM + Overture with calibrated "exists and is open" probabilities | Free | ODbL (share-alike). Useful for freshness; keep it in a separate table so it does not contaminate the permissive core |
| **OpenStreetMap** | Shops, farms, markets, tagged `shop=farm`, `amenity=marketplace`, `organic=*`, `craft=*` | Free | ODbL share-alike |
| **USDA Local Food Portal** | Five directories: farmers markets (~7,100 records), CSA, food hub, on-farm market, agritourism. Season, hours, products, SNAP/WIC/FMNP flags | Free with API key, or CSV bulk | Public domain in practice. The SNAP/WIC flags are your equity feature |
| State ag departments, Minnesota Grown, National Co+op Grocers member list, state co-op associations, LocalHarvest | Co-ops, CSAs, markets the federal data misses | Free, scrape or partner | Scrape ToS varies. Partner with NCG and state associations, they want the distribution |
| Google Places, Yelp Fusion | Best coverage and freshness | Paid | **Cannot cache or store results long-term under their terms.** Use only as a live enrichment call, never as a base layer |

### 6b. Products and makers (what is sold, who made it)

| Source | What you get | Cost | License / catch |
|---|---|---|---|
| **Open Food Facts** | 3M+ products by barcode, brand, ingredients, labels, Eco-Score. Bulk parquet download. At least two working MCP servers already (`openfoodfacts-mcp`, `openfoodfacts-mcp-server`) | Free | ODbL. Product identity layer, and a proof that the parquet + DuckDB + MCP pattern works |
| USDA Organic INTEGRITY Database | Every certified organic operation, address, products | Free | Public domain. Excellent for finding small certified producers by ZIP |
| Fair Trade USA, Fairtrade America, Certified Humane, Non-GMO Project, Animal Welfare Approved | Certified brands and operations | Free, scrape | Terms vary; most publish searchable directories |
| B Lab (B Corp) directory | Certified B Corps, scores by impact area | Free, scrape | No public API. Score breakdown is valuable |
| Trade associations: U.S. League of Tea Growers, state honey/maple/cheese guilds, American Cheese Society, roaster guilds | The long tail of small makers | Free, scrape | Membership lists are the single best "small maker" seed per category |
| Open Supply Hub | 100k+ production locations (factories), supplier-claimed data | Free account, 5,000 downloads free; API from $225/mo | Needed when you leave food for clothing and goods |

### 6c. Ownership (who owns the seller and the maker)

| Source | What you get | Cost | License / catch |
|---|---|---|---|
| **SEC EDGAR** (full-text search + XBRL APIs) | 10-K financials, DEF 14A executive comp, Item 402(u) CEO-to-median-worker pay ratio, 13F institutional holdings (this is where BlackRock and Vanguard become numbers), subsidiary lists (Exhibit 21) | Free | Public domain. Public companies only |
| **GLEIF** | Legal Entity Identifiers with parent/child relationships | Free, bulk | CC0. Covers large private companies too |
| **Wikidata** | `owned by` (P127), `parent organization` (P749), `subsidiary`, `founded by`, headquarters, for tens of thousands of brands | Free, SPARQL | CC0. Good for brand → parent resolution |
| **OpenCorporates** | 240M legal entities, officers, registered addresses, relationships | **Free for open-data projects that release under share-alike attribution**; otherwise from ~£225/mo | The free tier is rate-limited (~50/day) and requires you to publish your derived data openly. See §7 |
| Open Ownership (BODS) | Beneficial ownership statements, mostly UK/EU | Free | Thin for U.S., watch for FinCEN BOI changes |
| State Secretary of State registries (MN, WI, etc.) | Registered agents, officers, formation dates for the small independents | Free, per-state scrape or bulk | The only way to confirm "single owner, single location" for a co-op or farm stand |
| Wikipedia / news | Private equity ownership (Publix, Aldi, most regional chains have nothing in EDGAR) | Free | Manual, curated, cite everything |

### 6d. Wages and the ledger

| Source | What you get |
|---|---|
| USDA ERS Food Dollar Series | Farm share (11.8¢ per food dollar in 2024), plus the industry-group bill (retail 14.7¢, advertising 2.6¢ in 2023) across 28 product accounts. **The single most important dataset for the ledger** |
| BLS OES | Wages for cashiers, stockers, farmworkers, roasters, by metro. Lets you say what the register worker in Shakopee actually makes |
| Company 10-K | Gross margin and SG&A for the retail layer |
| Census County Business Patterns, Nonemployer Statistics | Small-business density by ZIP, for scoring "how local is local" |

### 6e. What does not exist and you will have to build

1. **A "made by the maker" flag.** No dataset says whether the entity selling a product also produced it. You will infer it from association membership, organic certification, "our farm" language on the site, and manual review. Start with a curated list of a few hundred and let makers self-claim (with a verification step).
2. **A local-ownership classifier.** Overture's `brand` field and OSM tags get you halfway. The rest is joining a POI to a state registry record to an owner type. Ship it as a probability with a reason string, never a bare label.
3. **The penny ledger itself.** A model on top of ERS + EDGAR + BLS, published as a methodology doc first.
4. **Freshness.** Buycott died of stale data. Budget for market managers and makers editing their own records, and for a monthly Overture refresh.

## 7. The licensing decision that shapes everything

Two options:

- **Open by default.** Publish your seller graph under ODbL (share-alike). This unlocks free OpenCorporates access, lets you freely mix OSM and OpenPOIs, fits a nonprofit and donation model, and makes the MCP server something other people will build on and contribute back to. Cost: competitors can take your data. Benefit: that is the mission anyway, and it is what makes Open Food Facts trusted.
- **Proprietary core.** Keep the permissive Overture/USDA/EDGAR/GLEIF/Wikidata layers in a closed database, pay OpenCorporates, avoid OSM. Cost: real money, less trust, weaker contributor story.

Recommendation: **open by default**, with one carve-out. Keep the *curation* (the ledger methodology, the classifier weights, editorial notes) as your value, and open the *facts*. Facts want to be free; judgment is what people donate for.

## 8. Data architecture

Keep it boring and inspectable.

**Core entities**

```
Place        id, name, geo, address, category, hours, season, payment_flags,
             source[], confidence, last_verified
Entity       legal name, jurisdiction, registry_id, LEI, formed, entity_type
Ownership    child_entity -> parent_entity, share_pct?, source, as_of
OwnerClass   individual | family | cooperative | esop | nonprofit |
             private_other | private_equity | public   (+ inst_top10_pct for public)
Maker        entity, products[], makes_own (bool + evidence), certifications[]
Product      gtin?, name, brand -> Entity, maker -> Maker, category, origin_geo
Practice     entity, scheme (organic, fair_trade, b_corp, union, ...), ref, as_of
Ledger       product|category, retailer_class, split{farm, processing, transport,
             retail_labor, retail_margin, marketing, exec, shareholders}, ci, sources[]
```

Every field carries `source` and `as_of`. If a fact has no source it does not go in.

**Pipeline**

1. Monthly: pull Overture places parquet for the U.S., filter to food and goods categories, load to PostGIS (or DuckDB + spatial extension for the first year).
2. Monthly: USDA Local Food Portal CSVs, Organic INTEGRITY, OFF parquet, GLEIF bulk, Wikidata SPARQL dump of P127/P749 for brands.
3. Weekly: EDGAR delta (new 13F, DEF 14A, 10-K filings) for the ~200 public companies that matter in food and household goods.
4. Quarterly or as-needed: association member lists and certifier directories (scrapers, with polite rate limits and robots.txt respect).
5. Continuous: user and maker submissions, queued for review.
6. Derived: ownership resolution (POI → brand → entity → owner chain → OwnerClass), local-ownership classifier, ledger estimates.

**Stack suggestion**, given a Python background and an offshore team: Python + FastMCP for the server, DuckDB over parquet for the analytical layer (exactly how the existing OFF MCP server works, and it is fast), PostGIS when you need writes and spatial queries at scale, a small Next.js or plain HTML front end. No Kubernetes until there is a reason.

## 9. The MCP server

Ship the graph as a remote MCP server (streamable HTTP) early, because it makes the project infrastructure rather than an app, and because AI shopping assistants are becoming a real purchase channel. Being the sourcing layer they call is a strategic position.

**Tools (v1)**

| Tool | Input | Output |
|---|---|---|
| `find_sellers` | product or category, lat/lon or ZIP, radius, min ladder tier | Ranked places with tier, owner class, distance, hours, payment flags, confidence |
| `find_makers` | product or category, optional region | Small makers with `makes_own` evidence, ownership, certifications, where to buy |
| `ownership_chain` | brand, entity, or GTIN | Parent chain to ultimate owner, owner class, top institutional holders if public, sources |
| `dollar_split` | GTIN, brand, or category + retailer class | Ledger estimate with confidence interval and every source cited |
| `better_alternative` | item + location | Options up the ladder, with distance and estimated ledger delta |
| `seasonal_now` | region | What is in season this month and who has it |
| `swap` | item | Lower-cost, lower-footprint substitution (filter vs bottled, bulk, secondhand, repair) |
| `report_issue` | place or entity id, correction | Queues a correction, returns ticket id |

**Resources**: `methodology/ledger.md`, `methodology/owner_class.md`, `ladder.md`, `changelog`. Assistants can read the methodology, which is how you stay honest at scale.

**Design rules**: every response includes `sources[]` and `as_of`; every classification includes `confidence` and `reason`; "not disclosed" is a first-class value, not null; rate-limit generously and require no key for read access.

## 10. Scraping: what, how, and when not to

You will need scrapers for association member lists, certifier directories, B Corp profiles, co-op and market vendor pages, and state registries. Rules:

- Prefer bulk downloads and official APIs whenever they exist (Overture, USDA, EDGAR, GLEIF, OFF, Organic INTEGRITY all do).
- Scrape only public pages, respect robots.txt, identify your user agent with a contact email, rate-limit to a human pace, cache aggressively.
- Do not scrape Google or Yelp, and do not store their results; their terms are explicit.
- For any small organization (a guild, a co-op), email them first. Most will hand you a CSV and ask to be listed.
- Store the raw page alongside the parsed record so a challenged fact can be re-verified.

## 11. Risks (unchanged, read twice)

1. **The ledger is a model.** Publish uncertainty. "12¢ ± 4¢ to the farm, from USDA ERS category data" is honest and still striking. "11.62¢" is a lawsuit.
2. **Private companies are black holes.** Treat non-disclosure as a reportable fact, shown prominently.
3. **The Amazon Associates ID conflicts with the ladder.** Decide the affiliate policy now, publish it, and either drop affiliate entirely or restrict it to tiers 3 to 5 with inline disclosure.
4. **Defamation exposure.** Stick to filed and published sources, cite inline, keep a correction process and a right-of-reply channel, get media liability coverage before scale.
5. **Retention.** The scanner is not the habit; the weekly local sourcing plan and the money-saving swaps are.
6. **Partisanship.** Frame everything as "where the money goes." A farmer getting 12 cents plays in every county.

## 12. Build plan

**Phase 0 (weeks 1 to 4): foundation and the tea proof.**
Entity structure decided (lean toward nonprofit or PBC). Licensing decision made (§7). Overture + USDA + OFF loaded locally. Hand-curate one category end to end: U.S. tea growers with location, ownership, `makes_own`, and where to buy. Write the ledger methodology doc. Nothing public yet.

**Phase 1 (months 2 to 4): Twin Cities directory + MCP alpha.**
`find_sellers`, `find_makers`, `seasonal_now` live for Minnesota. Every farmers market, co-op, CSA, farm stand in the metro, with SNAP/WIC flags. Ten hand-curated maker categories. Simple web front end. Offshore team builds the pipeline and scrapers; you own the classifier and the methodology.

**Phase 2 (months 4 to 8): ownership and the ledger.**
`ownership_chain` and `dollar_split` for the ~200 public companies and ~50 major private ones in U.S. food. First penny-ledger examples on the site. Maker self-claim flow with verification. Correction queue. Open the dataset.

**Phase 3 (months 8 to 14): substitution and national coverage.**
`better_alternative` and `swap`. List-and-receipt re-sourcing. Expand directory nationally on Overture + USDA. Partnerships with NCG and two or three state ag departments. Donations open.

**Phase 4: beyond food.**
Clothing (Open Supply Hub, secondhand-first), household goods, tools (repair and library-of-things), banking (credit union vs national bank is one of the strongest ledger stories there is). Each category gets its own ladder written the same way.

**Rough cost, first year, excluding your time:** infrastructure under $200/mo; data $0 if open-by-default (else ~$3k to $6k/yr for OpenCorporates and Open Supply Hub API); offshore build effort is the real line item, and scrapers plus pipeline plus MCP is a well-scoped 4 to 6 month project for a small team.

## 13. Immediate next decisions

1. Open-by-default licensing: yes or no. Everything downstream depends on it.
2. Affiliate policy, written and published.
3. Entity structure before any money moves.
4. Ledger methodology doc, written before ledger code.
5. First five hand-curated maker categories after tea (honey, maple, coffee roasters, cheese, soap are natural).

---

*Sources: USDA ERS Food Dollar Series; USDA NASS Local Food Marketing Practices Survey (2020); USDA AMS Local Food Directories and Local Food Portal API docs; Overture Maps Foundation places documentation and AWS registry; OpenPOIs (Henry Spatial Analysis); Open Food Facts and its MCP servers; OpenCorporates API documentation and pricing; Open Supply Hub pricing; SEC Regulation S-K Item 402(u); Charleston Tea Garden and Bigelow Tea company pages and Wikipedia; Fortune/AP reporting on 2026 boycott app growth; app store review summaries for Buycott and Goods Unite Us.*
