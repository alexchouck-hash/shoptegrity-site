# Local Services Ownership Directory: Development Spec

Part of the "Vote With Your Dollar" project. This document is the working brief for Claude Code. Read it fully before writing code. Sections marked **DECISION** are settled. Sections marked **OPEN** need a human answer before building that piece; do not guess, add a question to `QUESTIONS.md` and move to the next task.

---

## 1. Mission

Help people keep their money in their own community by answering one question for any service business: **who actually owns this, and where does the money go?**

Covers electricians, plumbers, HVAC, bike shops, dry cleaners, restaurants, auto repair, vets, dentists, salons, hardware stores, pharmacies, gyms, and similar. The food side of the project uses a sourcing ladder; this is the equivalent ladder for services.

Non-goals for v1: reviews, quality ratings, booking, pricing, ads. We only answer ownership and locality. Quality is what Google and Yelp are for.

Funding model is donations, so every architecture choice should favor low or zero recurring cost.

---

## 2. The Ownership Ladder

Every business gets exactly one tier. Lower number is more local.

| Tier | Name | Definition | Est. share of revenue staying local* |
|---|---|---|---|
| 1 | Owner-operated local | Single location, owner lives within the metro | highest |
| 2 | Local multi-location | 2+ locations, all in one metro, locally owned | high |
| 3 | Local franchisee | Local owner, national brand. Royalties and marketing fees leave | medium |
| 4 | Regional chain | HQ in-state or adjacent state, not publicly traded, not PE-owned | medium-low |
| 5 | National private chain | National footprint, privately or family held | low |
| 6 | Public or PE-owned | Publicly traded, or owned by private equity, **including rollups that kept the local name** | lowest |
| 0 | Unknown | Not enough evidence yet | n/a |

Special flags (orthogonal to tier, a business can have several):

- `coop`: member- or worker-owned cooperative (display above tier 1)
- `employee_owned`: ESOP
- `nonprofit`
- `rollup_disguised`: tier 6 operating under a legacy local name. This is the single most valuable thing we surface, because no one else shows it.
- `recently_acquired`: ownership changed in the last 24 months
- `self_attested`: owner claimed the listing and confirmed ownership

*The "share staying local" column needs real numbers with citations before it is shown to users (see Open Questions). Until then, display the tier only, no percentages.

### Classification rules

1. Never assign tier 1 or 2 without positive evidence. Absence of a chain match means tier 0, not tier 1. Display tier 0 as "Ownership not verified" with an optional softer hint like "No chain match found."
2. Every tier assignment must store its evidence (source, URL, date retrieved) and a confidence score from 0 to 1.
3. A higher-numbered tier from a reliable source always beats a lower-numbered tier from a weaker source. If a PE portfolio page lists the company, it is tier 6 even if the owner self-attested tier 1.
4. Classifications expire. Re-verify tier 1 to 3 every 12 months and anything in a PE-heavy category (see below) every 6 months.

### PE-heavy categories (extra scrutiny)

HVAC, plumbing, electrical, veterinary, dental, dermatology, physical therapy, car washes, funeral homes, pest control, landscaping, auto repair and collision, dry cleaning, self storage, urgent care, optometry.

---

## 3. Data Sources

Ordered by build priority.

1. **OpenStreetMap** (via Overpass or regional extracts from Geofabrik). Base list of businesses with category, coordinates, and `brand` / `brand:wikidata` tags. License: ODbL, attribution required, share-alike applies to derived databases of OSM data. Keep our ownership data in separate tables that reference OSM IDs so our data stays independently licensable.
2. **Name Suggestion Index** (github.com/osmlab/name-suggestion-index). Open list of chains and franchises with Wikidata IDs. First-pass chain detector.
3. **Wikidata**. For any brand match, walk `parent organization` (P749), `owned by` (P127), `stock exchange` (P414), `headquarters location` (P159) to separate tiers 4, 5 and 6.
4. **State business registries.** Minnesota Secretary of State business search for the pilot. Gives registered agent, principal office address, filing date, and assumed names (DBAs). A principal office address out of state is a strong tier 4+ signal. Check the site's terms and robots.txt before automating; if bulk access is not permitted, do lookups on demand and cache.
5. **Franchise lists.** FTC and state franchise registrations (Minnesota Department of Commerce requires franchise registration, and filings are public). Marks a brand as franchised, so a location is tier 3 when the franchisee is local, tier 5 or 6 when corporate-owned.
6. **PE rollup detection.** Curated table of known platform companies and their acquired brands, built from PE firm portfolio pages, press releases ("X acquires Y"), and trade press. This is a manual plus LLM-assisted pipeline, not a scraper free-for-all. Store every acquisition with a source URL.
7. **Owner self-attestation.** Claim flow with light verification (email at the business domain, or a postcard code later). Sets the `self_attested` flag and bumps confidence, subject to rule 3 above.
8. **Community flags.** "This was bought by..." with a required source link. Goes to a review queue, never auto-applied.

**Do not** scrape Google Maps or Yelp for business data. It violates their terms. Google Place IDs may be stored indefinitely and are the only Google data we persist.

---

## 4. Architecture

**DECISION:** one database, one API, thin clients. The website, the MCP server, and the browser extension all call the same API.

```
                +--------------------+
  ingest jobs → |  Postgres+PostGIS  | ← review queue / admin
                +---------+----------+
                          |
                     REST API (FastAPI)
              /           |             \
        Web map      MCP server     Chrome extension
     (MapLibre+OSM)  (remote, HTTP)  (Google Maps overlay)
```

### Stack

- **Language:** Python 3.12 for backend, ingest, and MCP. TypeScript for the extension and web front end.
- **API:** FastAPI, Pydantic models, OpenAPI generated.
- **DB:** Postgres 16 with PostGIS. Alembic migrations.
- **MCP:** official Python MCP SDK, streamable HTTP transport so it can be added as a remote connector. Also runnable over stdio for local dev.
- **Web map:** MapLibre GL JS with OSM-based tiles (Protomaps PMTiles self-hosted is the cheapest option). No Google Maps JS API in v1 because of per-load cost and caching restrictions.
- **Extension:** Chrome Manifest V3, TypeScript, no framework needed.
- **Tests:** pytest, plus Playwright for the extension.
- **Hosting:** anything cheap. A single small VPS or Fly.io/Railway app plus managed Postgres is enough for the pilot.

### Core schema (starting point, refine as needed)

```
business
  id (uuid, pk)
  name, name_normalized
  category (enum, see taxonomy), subcategory
  address, city, state, postal_code, country
  geom (geography point)
  phone, website
  osm_id, osm_type
  google_place_id            -- nullable, only Google field we store
  status (active|closed|unknown)
  created_at, updated_at

ownership
  id, business_id (fk)
  tier (0..6)
  flags (text[])             -- coop, rollup_disguised, etc.
  confidence (0..1)
  parent_entity_id (fk → entity, nullable)
  owner_locality (metro code or null)
  verified_at, expires_at
  is_current (bool)          -- keep history, never overwrite

entity                        -- brands, parent companies, PE firms, franchisors
  id, name, kind (brand|company|pe_firm|franchisor|public_company)
  wikidata_id, ticker, hq_city, hq_state, hq_country
  parent_entity_id (self fk)

evidence
  id, ownership_id (fk)
  source_type (osm|nsi|wikidata|sos|franchise_reg|pe_portfolio|press|self_attest|community)
  url, retrieved_at, excerpt (short, our own paraphrase), weight

acquisition
  id, acquirer_entity_id, target_entity_id or target_business_id
  announced_on, source_url

claim                         -- owner self-attestation
flag                          -- community reports, with review status
```

### Matching Google places to our records

The extension sees a Google place (name, address, coordinates, sometimes Place ID in the URL). The API needs a `match` endpoint: fuzzy name match (normalized, token-set ratio) within 75 m, with address number as a tiebreaker. Cache successful matches by Place ID. Return `no_match` rather than a weak match; a wrong badge is worse than no badge.

---

## 5. API (v1)

```
GET  /v1/businesses?lat=&lon=&radius_m=&category=&max_tier=&flags=&limit=
GET  /v1/businesses/{id}
GET  /v1/businesses/{id}/ownership        -- tier, flags, parent chain, evidence list
POST /v1/match                            -- {name, address?, lat, lon, google_place_id?} → business or no_match
POST /v1/classify                         -- same input, runs on-demand classification if unknown, returns tier + confidence
GET  /v1/entities/{id}                    -- parent company, everything it owns nearby
GET  /v1/categories
POST /v1/flags                            -- community report, requires source_url
POST /v1/claims                           -- owner claim start
```

Anonymous read access with rate limiting by IP. API keys for higher limits. All responses include `data_as_of` and an attribution block for OSM.

---

## 6. MCP Server

Name: `local-ownership`. Keep the tool surface small and the descriptions precise so models pick the right tool.

| Tool | Input | Returns |
|---|---|---|
| `find_local_businesses` | location (lat/lon or free-text place), category, radius_km (default 10), max_tier (default 3), limit | Ranked list: name, address, distance, tier name, flags, confidence |
| `get_ownership` | business_id or (name + location) | Tier, plain-language explanation, parent chain up to ultimate owner, evidence with URLs, last verified date |
| `compare_businesses` | list of business_ids or names + location | Side-by-side tier and ownership summary |
| `who_owns_brand` | brand name | Parent chain, ownership type, HQ, other brands under the same parent |
| `list_categories` | none | Supported category taxonomy |
| `report_ownership_change` | business, claim text, source_url | Confirmation that it went to the review queue |

Guidelines:

- Every tool result includes a one-sentence `summary` field written for direct quoting, plus structured data.
- Always return confidence and `last_verified`. Tier 0 results must say "not verified," never imply local.
- Free-text locations get geocoded with Nominatim (respect its usage policy, cache results) or a self-hosted Photon instance.
- Provide a `resources` entry describing the ladder so a model can explain tiers without a tool call.
- Write-type tools (`report_ownership_change`) only enqueue. Nothing an LLM sends changes a classification directly.

---

## 7. Browser Extension (Google Maps overlay)

Google offers no add-on system for consumer Maps, so this is a content script on `https://www.google.com/maps/*`.

Behavior:

1. Detect when a place panel opens (URL change to `/maps/place/...` plus a MutationObserver on the panel container).
2. Extract name, address, and coordinates. Prefer parsing the URL (`!3d<lat>!4d<lon>` and the place name segment) over DOM scraping, since URL structure changes less often than class names.
3. Call `POST /v1/match`. On a match, inject a compact badge under the place title: tier label, color, and any flags ("Owned by [Parent], private equity"). Click expands to the evidence list and a link to the full page on our site.
4. On `no_match` or tier 0: show a muted "Ownership not verified" chip with a "Help verify" link. Make this toggleable in settings.
5. Stretch: badge results in the search results list, with batched match calls and debounce.

Constraints:

- Isolate all DOM selectors in one `selectors.ts` file with a fallback chain, and fail silently. When Google changes markup, that file is the only thing to fix.
- Minimal permissions: host permission for google.com/maps and our API domain only. No browsing history, no analytics by default.
- Send only the place being viewed to the API. No user identifiers. State this plainly in the privacy policy.
- Known limitation: desktop Chrome/Edge/Firefox only. Mobile users get the web map and MCP instead.
- Risk to note for the human: Google could object to DOM injection on Maps. Many extensions do this today, but the web map must stand on its own so the project does not depend on the extension.

---

## 8. Web Map

- MapLibre map, category filter chips, tier slider ("show tier 3 and better").
- Pins colored by tier. Tier 6 with `rollup_disguised` gets a distinct marker, since that is the headline feature.
- Business detail page: tier, plain-language explanation, ownership chain diagram (business → parent → ultimate owner), evidence list with links, "last verified," claim and report buttons.
- "Who owns what near me" view: pick a parent company, see every local storefront it owns under different names.
- Shares design system and navigation with the food side of the site. The food ladder and the services ladder should feel like the same idea.

---

## 9. Category Taxonomy (v1)

Map OSM tags to these. Keep it short at first.

`electrician, plumber, hvac, general_contractor, roofing, landscaping, pest_control, auto_repair, auto_body, car_wash, bike_shop, hardware_store, dry_cleaner, laundromat, salon_barber, gym_fitness, veterinary, dental, optometry, pharmacy, restaurant, cafe, bakery, bar_brewery, grocery, bookstore, pet_supply, funeral_home, childcare, bank_credit_union`

Note: trades (electricians, plumbers, HVAC) are thin in OSM because many have no storefront. For those, supplement with state contractor license lookups (Minnesota DLI license search for the pilot). Treat that as its own ingest task.

---

## 10. Milestones and Task Queue

Work top to bottom. Each task should be one PR-sized unit with tests. Mark done in `TASKS.md`.

### M0: Scaffolding
- [ ] Monorepo layout: `/api`, `/ingest`, `/mcp`, `/extension`, `/web`, `/docs`
- [ ] Docker Compose with Postgres+PostGIS, API, and a seed script
- [ ] Alembic migrations for the core schema
- [ ] CI: lint (ruff), type check (mypy, tsc), tests
- [ ] `QUESTIONS.md`, `TASKS.md`, `DECISIONS.md` created

### M1: Chain detection for one metro
- [ ] OSM ingest for the pilot bounding box, mapped to the taxonomy
- [ ] NSI import into `entity`, brand matching on `brand:wikidata` then normalized name
- [ ] Wikidata parent-chain walker, assigns tiers 4 to 6 with evidence
- [ ] Everything unmatched stays tier 0
- [ ] Report: counts by category and tier, plus a sample of 50 for manual spot check

### M2: API
- [ ] Read endpoints with PostGIS radius queries
- [ ] `/v1/match` with fuzzy matching and a labeled test set of at least 100 pairs. Target precision of 0.98 or better, accept lower recall.
- [ ] Rate limiting, API keys, OpenAPI docs

### M3: MCP server
- [ ] Tools from section 6 over stdio, then streamable HTTP
- [ ] Geocoding with cache
- [ ] Eval script: 20 natural-language prompts, check the right tool is called and the summary is accurate

### M4: Positive local evidence
- [ ] State business registry lookup (on demand, cached)
- [ ] Franchise registry import, tier 3 logic
- [ ] Contractor license ingest for trades
- [ ] Rules engine that combines evidence into tier + confidence. Rules live in one readable file with unit tests for each rule.

### M5: Rollup detection
- [ ] `acquisition` table and admin entry form
- [ ] LLM-assisted pipeline: given a PE platform company, find acquisition announcements, extract target names and locations, output to the review queue with source URLs. Human approves every row.
- [ ] Seed with the 10 largest home-services and veterinary platforms active in the pilot metro

### M6: Web map
- [ ] Map, filters, detail pages, ownership chain diagram
- [ ] Claim flow and report flow with review queue admin

### M7: Extension
- [ ] Place panel badge, settings page, privacy policy
- [ ] Playwright smoke test against live Google Maps, run nightly to catch selector breakage
- [ ] Chrome Web Store listing assets

### M8: Expand
- [ ] Second metro using the same pipeline, measure hours of human review required. That number decides how fast this can scale.

---

## 11. Brainstorm Backlog (not scheduled)

- **"Local score" for a whole errand list.** Paste a list of businesses you use, get a breakdown of what share of your spending goes to each tier, with suggested swaps. Ties directly to the pennies-per-dollar concept.
- **Acquisition alerts.** "A business you follow was just acquired by X."
- **Swap suggestions.** On any tier 5 or 6 page, show the nearest tier 1 to 3 alternatives in the same category. Also useful as an MCP tool: `suggest_local_alternative`.
- **Embeddable badge.** Verified local businesses can put a "Locally Owned, Verified" badge on their own site that links back. Free marketing for them, free distribution for us, and an incentive to self-attest.
- **Chamber of commerce and "buy local" alliance partnerships** for seed data and verification volunteers.
- **Ownership chain for restaurants** specifically: restaurant groups are a gray zone (local group with 12 concepts is tier 2, but feels different from a single owner-chef). Consider showing location count explicitly.
- **Bank and credit union layer.** Credit unions and community banks vs national banks is one of the highest-impact local swaps.
- **Open data release.** Publish the ownership dataset under an open license so others can build on it. Fits the donation model and builds trust.
- **Apple Maps and OSM app integrations** (Organic Maps, etc.) as friendlier targets than Google over the long run.
- **Safari and Firefox ports** of the extension. Firefox for Android supports extensions, which gives a partial mobile path.
- **Link to the brand ethics idea.** Same `entity` table can carry ethics ratings for parent companies later, so design `entity` to be shared across both projects.

---

## 12. Risks and Guardrails

- **Defamation and accuracy.** Saying a business is PE-owned when it is not could harm a real local owner. Every tier 4+ claim needs a source link shown to the user. Provide a fast correction path, and log every correction. Have a lawyer review the dispute process before public launch.
- **Stale data.** Ownership changes quietly. Show "last verified" everywhere and decay confidence over time.
- **Gaming.** Owners may falsely self-attest. Self-attestation alone never exceeds 0.7 confidence and never overrides registry or acquisition evidence.
- **Licensing.** Keep OSM-derived tables and our ownership tables separable. Show OSM attribution on the map and in API responses.
- **Terms of service.** No scraping of Google, Yelp, or any site that prohibits it. Respect robots.txt. On-demand lookups with caching are preferred over bulk crawling of government sites.
- **Extension fragility.** Assume it will break a few times a year. Nightly smoke test plus isolated selectors keeps the fix to minutes.
- **Tone.** The product informs, it does not shame. Tier 6 copy should be neutral and factual: "Owned by [Parent], a private equity firm based in [City]." Let the user draw conclusions.

---

## 13. Open Questions (need a human answer)

1. **OPEN:** Pilot metro. Assumed Twin Cities unless told otherwise.
2. **OPEN:** How to define "local" geographically: same metro area (MSA), same county, or a radius from the business? Draft assumes MSA.
3. **OPEN:** Should a locally owned franchise rank above or below a regional chain headquartered in-state? Draft puts franchise at 3, regional chain at 4.
4. **OPEN:** Source for "share of revenue staying local" figures. Candidates are the Civic Economics local multiplier studies and the American Independent Business Alliance summaries. Needs review before any percentage is displayed.
5. **OPEN:** Project and domain name, and whether services live on the same domain as the food site.
6. **OPEN:** Who staffs the review queue at first, and what weekly time budget it gets. M5 and M8 depend on this.
7. **OPEN:** License for the published ownership dataset (CC BY, CC BY-SA, ODbL, or none yet).

---

## 14. Working Agreements for Claude Code

- Small PRs, each with tests. Do not start a milestone until the previous one's checklist is green.
- Record every non-obvious choice in `DECISIONS.md` with a one-line reason.
- If a data source's terms are unclear, stop and add it to `QUESTIONS.md` rather than building the scraper.
- Prefer boring technology. No new service or dependency without a note on why the existing stack cannot do it.
- Never commit API keys or personal data. Seed and test data must be synthetic or from open sources.
- When a classification rule is ambiguous, default to tier 0. Being unsure is fine. Being wrong about someone's business is not.
