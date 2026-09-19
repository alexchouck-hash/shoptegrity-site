# Vote With Your Dollar: Site Implementation Spec

Companion to `01-business-and-site-plan.md`. Written so it can be handed to a dev team or fed to Claude Code as a task queue. Section 12 is the backlog.

## 1. Goals for v1

1. A visitor can pick a category, see where $100 goes at a conventional option vs a better one, and get a concrete swap.
2. A visitor can look up a major brand, see its parent company, its cited scorecard, and better alternatives in the same product category.
3. A visitor in the pilot metro can find local co-ops, farmers markets, and credit unions near them.
4. Every claim on the site links to a source, and the methodology is public.

Non-goals for v1: user accounts, marketplace, browser add-on, MCP server, native apps.

## 2. Sitemap

```
/                          Home: hero flow map, top 5 swaps, brand search
/flow                      Dollar Flow Map index
/flow/[category]           Side-by-side flow for one category
/swaps                     Swap Guide index, ranked by impact
/swaps/[category]          Category page: ladder, swaps, steps, savings
/brands                    Brand search and browse
/brands/[slug]             Brand page: owner, scorecard, evidence, alternatives
/companies/[slug]          Parent company page: everything it owns
/local                     Local Directory, map and list by proximity
/local/[type]/[slug]       Listing page (market, co-op, credit union, service)
/my-dollar                 Calculator: enter monthly spend, see reroutable total
/methodology               Scoring rubric, data sources, firewall policy
/corrections               Submit evidence or dispute a score, public log
/about, /support           Mission, donations
```

## 3. Page templates

### 3.1 Home
- Headline plus one animated flow comparison (grocery: national chain vs co-op).
- Brand search box ("Who really gets your money when you buy ___?").
- "Start here" strip: top five swaps with estimated annual dollars rerouted.
- Location prompt feeding the Local Directory.

### 3.2 Flow page (`/flow/[category]`)
- Two Sankey diagrams side by side, $100 entering on the left.
- Nodes: suppliers and producers, front-line wages, management and executive pay, rent, interest, marketing, taxes, profit. Profit splits to reinvestment, dividends and buybacks. Dividends and buybacks split to beneficial owners by wealth bracket (top 1%, next 9%, bottom 90%), or to members or employees for co-ops, mutuals, and ESOPs.
- Toggle between representative companies in the category.
- Every node is clickable and shows its source and the year of the data.
- Plain-language summary under the chart: "At A, about $X of your $100 ends up with shareholders. At B, that money goes to members as lower fees."
- CTA to the matching swap page.

### 3.3 Swap page (`/swaps/[category]`)
- The universal ladder, customized for the category.
- Difficulty, time required, typical annual spend, and whether the swap saves or costs money.
- Step-by-step instructions (example: moving direct deposit and autopay to a credit union).
- Recommended alternatives pulled from the entity database, local ones first if location is known.
- Honest "limits" box where the swap is weak (gas, wireless).

### 3.4 Brand page (`/brands/[slug]`)
- Header: brand, parent company, ownership type, ultimate owners.
- Scorecard: one bar per dimension, each with a confidence level and a date. "Unknown" rendered explicitly.
- Evidence list: each item is a dated fact with a source link and the dimension it affects.
- Alternatives rail: grouped by product category, since one brand spans several. Each card shows ownership type, score deltas, price band, and where to buy.
- Weight sliders so the user can reorder alternatives by what they care about.
- "Report an error" link.

### 3.5 Local Directory (`/local`)
- Map plus list, filter by type, sort by distance.
- Each listing shows ownership type and a "locally owned" flag with how that was verified.
- v1 types: farmers markets, food co-ops, CSAs, credit unions. v2: local services (electricians, bike shops, dry cleaners, restaurants).

### 3.6 My Dollar calculator (`/my-dollar`)
- User enters or accepts default monthly spend by category.
- Output: a personal flow map, a ranked swap list, and a running "dollars rerouted per year" total.
- State stored in the browser only. No account needed.

## 4. Data model (PostgreSQL)

```
company            id, name, slug, ownership_type, parent_company_id, hq_city,
                   hq_state, hq_country, is_public, ticker, website, notes
brand              id, name, slug, company_id, description
product_category   id, name, slug, parent_id, spend_category_id
brand_category     brand_id, product_category_id, price_band
spend_category     id, name, slug, tier, avg_annual_spend, swap_difficulty,
                   saves_money (bool)
dimension          id, key, name, description, default_weight
evidence           id, company_id, dimension_id, fact_text, source_url,
                   source_name, source_type, event_date, retrieved_at,
                   impact (-2..+2), reviewed_by, status
score              id, company_id, dimension_id, value (0-100 or null),
                   confidence, computed_at, rubric_version
flow_profile       id, company_id or archetype, year, json of node splits,
                   source_notes
beneficial_owner_distribution   year, bracket, share   (Fed data)
alternative        id, from_brand_id, to_brand_id, product_category_id,
                   rationale, editor_approved
listing            id, type, name, slug, company_id (nullable), address,
                   lat, lng, hours, website, locally_owned, verified_how,
                   verified_at
swap_guide         id, spend_category_id, markdown_body, steps json, limits
correction         id, target_type, target_id, submitted_by, body,
                   evidence_url, status, resolution, resolved_at
```

`ownership_type` enum: worker_coop, esop_100, esop_partial, consumer_coop, producer_coop, retailer_coop, mutual, credit_union, nonprofit, purpose_trust, local_private, national_private, public, private_equity, government, unknown.

## 5. Scoring engine

- Pure function: `(evidence[], company financials, rubric_version) -> score per dimension`.
- Rubric lives in a versioned YAML file in the repo. Each rule names its input, thresholds, and points.
- Examples:
  - Ownership: direct lookup from `ownership_type` to points.
  - Capital extraction: (dividends + buybacks) / net income, three-year average, bucketed.
  - Pay equity: CEO pay ratio from proxy filings, bucketed. Null for private companies unless disclosed.
  - Labor and environment: penalty totals and case counts normalized by revenue or headcount, plus positive certifications.
- Confidence is a function of source count, source type, and age of evidence.
- Composite score is computed client-side from dimension scores and the user's weights, so no single "official" grade is stored.
- Alternatives eligible for the rail must beat the source brand on the weighted composite and have no dimension in the bottom band.
- Every rubric change bumps the version and recomputes everything. Old versions stay viewable.

## 6. Data sources and pipeline

| Source | Feeds | Method |
|---|---|---|
| SEC EDGAR (10-K, proxy) | Financials, pay ratio, buybacks, dividends | API, scheduled |
| Good Jobs First Violation Tracker | Labor, environment, legal penalties | Check license and access terms first |
| OSHA and EPA ECHO enforcement data | Labor, environment | Public downloads and APIs |
| NLRB case data | Labor | Public search and downloads |
| OpenSecrets | Political spending amount and disclosure | Check API terms |
| ITEP reports | Tax behavior | Manual entry with citation |
| KnowTheChain, Corporate Human Rights Benchmark, Fashion Transparency Index | Supply chain | Manual entry with citation |
| B Corp directory, NCEO employee ownership lists, co-op directories | Ownership, positive signals | Manual and scripted |
| NCUA credit union data | Local Directory | Public download |
| USDA farmers market and CSA directories | Local Directory | Public download and API |
| Federal Reserve Distributional Financial Accounts | Beneficial owner brackets | Public download |
| BLS Consumer Expenditure Survey | Default spend per category | Public download |

Pipeline:
1. Scheduled Python jobs pull each source into raw tables.
2. Entity resolution matches records to `company` (name, ticker, parent mapping). Ambiguous matches go to a review queue.
3. LLM-assisted research drafts evidence items and parent-company links with citations. Nothing is published without human approval.
4. Scoring engine recomputes on any evidence change.
5. Every published fact stores `source_url`, `retrieved_at`, and an archived snapshot link.

Confirm the terms of use of every third-party dataset before ingesting or redisplaying it.

## 7. Tech stack

- **Frontend:** Next.js (App Router, TypeScript), static generation for brand, flow, and swap pages with on-demand revalidation. Tailwind for styling.
- **Charts:** D3 with d3-sankey for flow maps.
- **Maps:** MapLibre GL with OpenStreetMap tiles.
- **Backend:** Python, FastAPI. Python keeps the data pipeline, scoring engine, and API in one language.
- **Database:** PostgreSQL with PostGIS for proximity queries.
- **Search:** Postgres full-text and trigram at first. Move to Meilisearch or Typesense if needed.
- **Jobs:** scheduled workers (cron plus a simple queue) for ingestion.
- **Admin:** internal review app for the evidence queue, entity matching, alternatives approval, and corrections. Role-based access, full audit log.
- **Hosting:** Vercel or Cloudflare for the frontend, a managed Postgres, a small container host for the API and jobs.
- **Analytics:** privacy-respecting and cookieless (Plausible or similar). No ad trackers.
- **Repo:** monorepo with `/web`, `/api`, `/pipeline`, `/rubric`, `/content`.

## 8. API (public in Phase 3, used internally from day one)

```
GET /v1/brands?q=                 search
GET /v1/brands/{slug}             brand, parent, scores, evidence
GET /v1/brands/{slug}/alternatives?category=&weights=
GET /v1/companies/{slug}          company and all brands it owns
GET /v1/categories                spend categories with tier and difficulty
GET /v1/flows/{category}          flow profiles for comparison
GET /v1/local?lat=&lng=&type=&radius=
GET /v1/methodology               current rubric version
```

Read-only, cached, rate limited. API keys for commercial use.

## 9. MCP server (Phase 3)

Thin wrapper over the API so AI assistants and other apps can use the data.

Tools:
- `lookup_brand(name)` returns owner, scores, top evidence.
- `find_alternatives(brand, product_category, weights?)`
- `who_owns(name)` walks the parent chain.
- `find_local(lat, lng, type, radius)`
- `dollar_flow(category, company?)`
- `suggest_swaps(monthly_spend_by_category)`

All responses include source links and the rubric version.

## 10. Browser add-on (Phase 3)

- On Google Maps and similar: a small badge on business listings showing ownership type and the locally owned flag, from the Local Directory data.
- On shopping sites: a badge on product pages showing the brand's parent and a link to alternatives.
- Reads page content locally and sends only the business or brand name to the API. No browsing history collected.

## 11. Editorial, legal, and trust requirements

These are build requirements, not just policy.

- Evidence `fact_text` is limited to documented facts. The admin tool flags characterizing words for editor review.
- No evidence item can be published without a source URL, a date, and a reviewer.
- Every page with affiliate links shows a disclosure. Affiliate status is never available to the scoring engine (enforced by keeping it in a separate table the engine cannot read).
- `/corrections` writes to a public log with status and resolution.
- Each score shows its "as of" date, and scores older than 18 months show a staleness warning.
- Financial pages (banking, insurance, retirement) carry an "informational, not financial advice" note.
- Media counsel reviews the methodology page, the evidence policy, and the first batch of brand pages before launch.
- Accessibility: WCAG 2.2 AA. Every Sankey has a table view with the same data.
- Performance: brand pages usable on a phone in a store. Target LCP under 2.5s on 4G.

## 12. Build backlog

Ordered so each item is a self-contained task.

### Phase 0: Foundation
1. Scaffold monorepo, CI, linting, preview deploys.
2. Create the Postgres schema and migrations from Section 4.
3. Write rubric v1 as YAML with unit tests for each rule.
4. Build the scoring engine with tests on fixture companies.
5. Build the admin app: company and brand CRUD, evidence queue, approvals, audit log.
6. Write the methodology and firewall pages.

### Phase 1: MVP
7. EDGAR ingestion: financials, pay ratio, dividends, buybacks.
8. OSHA and EPA ingestion plus entity resolution and review queue.
9. Parent-company mapping for the first 50 brands (LLM draft, human approval).
10. Brand page template with scorecard, evidence, and table fallback.
11. Alternatives model, approval flow, and rail with weight sliders.
12. Flow profile data for banking, grocery, clothing (2 to 3 companies or archetypes each).
13. Sankey component with clickable, sourced nodes and side-by-side layout.
14. Swap pages for the three launch categories.
15. Local Directory: ingest NCUA and USDA data for the pilot metro, PostGIS proximity search, map and list UI.
16. Home page, brand search, SEO metadata, sitemap, structured data.
17. Corrections form and public log.
18. Legal review, then launch.

### Phase 2: Breadth
19. Remaining Tier 1 categories (insurance, restaurants, streaming and books, hardware, payment method).
20. My Dollar calculator with browser-only state.
21. Swap checklist and "dollars rerouted" tracker.
22. Expand to 200+ brands. Add NLRB, Violation Tracker, and supply chain benchmark data.
23. Local services in the directory with ownership verification workflow.
24. Donation and membership flow.

### Phase 3: Platform
25. Public API with keys, docs, and rate limits.
26. MCP server.
27. Browser add-on for maps and shopping sites.
28. Embeddable flow map widget for partners and journalists.

## 13. Definition of done for the MVP

- Three categories live end to end: flow map, swap page, brands, alternatives.
- 50 brands published, each with a parent company, at least three scored dimensions, and at least three approved alternatives per product category.
- 100% of published evidence has a source, a date, and a reviewer.
- Local Directory returns results within 25 miles for any address in the pilot metro.
- Methodology, corrections, and disclosure pages live.
- Counsel sign-off recorded.
