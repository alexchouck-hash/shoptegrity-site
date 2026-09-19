# Vote With Your Dollar: Site and Business Plan

Working draft, September 2026

## 1. The idea in one paragraph

Most people have no idea where their money ends up after they hand it over. This project shows them. For any everyday purchase, the site draws a map of where each dollar lands (workers, suppliers, landlords, executives, shareholders, and who those shareholders actually are), then shows a better route for the same dollar and makes the swap easy. The map shows the leak. The swap is the patch.

## 2. Problem

- Consumers who want to spend according to their values have no practical tool for it. Existing ratings sites cover one niche (fashion, politics) or tell you a brand is bad and leave you in the aisle with no next move.
- Ownership is hidden. Many "small natural brands" are owned by the same multinationals people think they are avoiding (Annie's is General Mills, Burt's Bees is Clorox, Seventh Generation is Unilever).
- The biggest, easiest swaps are not the ones people think of. Banks and insurance move more money with less effort than agonizing over a T-shirt.
- "Ethical" is assumed to mean "more expensive." Many of the best swaps save money.

## 3. Product: one data platform, four front doors

All four share one backend: a company and brand database with ownership, scores, evidence, and alternatives.

| Front door | Question it answers | Core feature |
|---|---|---|
| Dollar Flow Map | Where does my money go? | Side-by-side flow diagrams: your $100 at option A vs option B |
| Brand Check | What is wrong with what I buy now, and what is the better version? | Brand scorecard, evidence, parent company, alternatives rail |
| Swap Guide | What should I change first? | Category pages ranked by spend, ease, and impact, with step-by-step swaps |
| Local Directory | What is near me and actually local? | Farmers markets, co-ops, credit unions, and local services by proximity, with a "who owns this" flag |

The curated marketplace (good4world) is a fifth, later front door that reuses the same scores to recommend specific products.

Longer term, the same data is exposed through an MCP server and a browser add-on that overlays ownership and score info on Google Maps and shopping sites.

## 4. What "better" means

### 4.1 Default values

Better treatment of people, more equal pay, less labor exploitation, less environmental impact, less waste, more durability, less profit flowing to already wealthy shareholders, more employee and member ownership, and a smaller gap between executives and everyone else.

### 4.2 Scoring dimensions (each one measurable and cited)

1. **Ownership.** Who gets the profit. Default ladder: worker co-op or 100% ESOP, then consumer co-op, mutual, or credit union, then nonprofit or purpose trust, then local private, national private, publicly traded, private equity owned.
2. **Capital extraction.** Dividends plus buybacks as a share of profit, vs wages and reinvestment.
3. **Pay equity.** CEO-to-median-worker pay ratio, median pay, living wage status.
4. **Labor.** OSHA and wage-theft violations, NLRB cases, supply chain audits, fair trade certification.
5. **Environment.** Emissions intensity, EPA violations, packaging, durability, repairability.
6. **Locality.** Where the owners and headquarters sit, and how much of each dollar recirculates locally.
7. **Secondary:** tax behavior, market power, transparency. Political spending is scored on amount and disclosure, not direction, so the site does not read as partisan.

### 4.3 Scoring rules

- No single grade by default. Show each dimension, and let users set their own weights. A default weighting reflects the site's values in 4.1.
- Every score links to its evidence. No evidence, no score.
- "Unknown" is a visible score. Private companies disclose less, and the site must not reward opacity.
- Methodology is public and mechanical. The same rubric applies to everyone, including any company the site earns money from.

### 4.4 The universal ladder

Generalized from the food sourcing ladder. It sits at the top of every category page:

1. Do not buy
2. Borrow, share, or use the library
3. Used, refurbished, or repaired
4. Direct from a local maker or grower
5. Co-op, mutual, or employee-owned
6. Mission-locked (purpose trust, nonprofit, B Corp)
7. Better-scoring conventional
8. Conventional

## 5. Category roadmap

Priority = annual household spend × ease of swap × how different the money's landing spot is.

### Tier 1: launch categories (easy, real impact, several save money)

| Category | Easiest swap |
|---|---|
| Banking | Credit union, community bank, or CDFI. Include loans and mortgages. |
| Insurance | Mutual and member-owned insurers |
| Grocery, stores | Co-ops, farmers markets, CSAs, employee-owned chains |
| Grocery, products | Farmer co-op and employee-owned brands on normal shelves, plus the parent-company map |
| Clothing | Used first, repair, then mission-owned brands |
| Restaurants and delivery | Local independents. Order direct instead of through delivery apps. |
| Streaming, books, music | Library apps, rotating subscriptions, buying direct from artists |
| Hardware | Retailer-owned co-op stores |
| How you pay | Debit or cash at small businesses to cut card network fees |

### Tier 2: second wave (moderate effort or limited availability)

Wireless, internet provider, utilities and community solar, pharmacy, vets, childcare, gyms, coffee and beer, eyewear, electronics and furniture (refurbished and repairable), event tickets, news, search engines, AI tools.

### Tier 3: "understand the flow" pages (hard to swap, still worth mapping)

Housing, healthcare, vehicles, gasoline, taxes, retirement accounts. These are education pages with whatever margin-level levers exist (credit union mortgage, independent mechanic, buying used, proxy voting).

## 6. Users

- **The motivated beginner.** Wants to do better, does not know where to start. Needs the top five swaps and a checklist.
- **The aisle shopper.** Standing in a store, looks up a brand on a phone. Needs a fast brand page and an alternative in the same category.
- **The local-first shopper.** Wants the farmers market, the co-op, the local electrician. Needs proximity search.
- **The skeptic.** Wants to see the receipts. Needs citations and open methodology.
- **Builders.** Other apps and AI assistants that want this data. Needs the MCP and API.

## 7. Competitive landscape

| Player | What it does | Gap |
|---|---|---|
| Good On You | Fashion brand ratings | Fashion only |
| Ethical Consumer | Broad ratings | UK focused, paywalled |
| Goods Unite Us | Political donations | One dimension |
| DoneGood | Marketplace of ethical brands | No critique of incumbents, no flow of money |
| B Corp directory | Certified companies | A list, not a swap tool |
| Buycott and similar apps | Barcode campaigns | Status uncertain, campaign driven |

Differentiators: the money flow visualization, cross-category coverage, the critique paired with the swap, local proximity, user-weighted values, and an open data layer. Verify the current status of each competitor before launch.

## 8. Business model

Default stance: donation supported, mission first. Credibility is the asset, so revenue must never touch scores.

| Stream | Notes |
|---|---|
| Donations and memberships | Primary. Small recurring supporters, "member supported" framing. |
| Grants | Foundations focused on local economies, co-op development, consumer protection. |
| Affiliate links | Only on alternatives, clearly disclosed, never a scoring input. Existing Amazon Associates ID is a last resort channel. |
| API and MCP licensing | Free for personal and nonprofit use, paid tier for commercial apps. |
| Sponsored directory listings | Probably avoid. If ever used, only for entities that already pass the score threshold, and labeled. |

Structure to consider: nonprofit, or a public benefit company with a published firewall policy between revenue and scoring. Get legal and tax advice before choosing.

### Costs (lean)

- Offshore dev team for build and data pipelines
- Hosting and data (low at MVP scale)
- LLM usage for research assistance
- Media lawyer review before launch and on a retainer for disputes
- Part-time editor or researcher for hand review of scores

## 9. Legal and credibility risk

- **Defamation.** The site publishes negative information about companies with large legal teams. Rule: state documented facts with sources ("Fined $X by OSHA in 2024, link"), never characterizations ("exploits workers"). Court records, regulator actions, company filings, and established NGO reports only.
- **Corrections policy.** Public, fast, and logged. Companies can submit evidence through a form.
- **Conflict of interest.** Published firewall between revenue and scoring. Affiliate relationships disclosed on every page where they apply.
- **Trademark.** Brand names used for identification only. No logos without checking fair use with counsel.
- **Accuracy of the flow map.** Asset managers like BlackRock and Vanguard mostly hold shares for other people's retirement accounts. The map must trace through to beneficial owners by wealth bracket, using Federal Reserve distribution data. Being precise here is what makes the site hard to dismiss.
- **Not financial advice.** Banking, insurance, and retirement pages are informational and say so.

## 10. Go-to-market

1. **Launch with a hook.** "Where does $100 go?" comparisons are inherently shareable. One strong graphic per category.
2. **SEO on brand questions.** "Who owns [brand]" and "[brand] alternatives" are high-intent searches. Every brand page targets both.
3. **The weekend swap challenge.** Five swaps, a checklist, a running total of dollars rerouted per year.
4. **Partnerships.** Co-ops, credit union associations, farmers market associations, and employee ownership groups all have an interest in sending traffic.
5. **Local pilot.** Seed the Local Directory in one metro first (Twin Cities) and get it dense before expanding.
6. **Open data.** Let journalists, researchers, and other apps cite and embed the data.

## 11. Roadmap

| Phase | Timeframe | Deliverable |
|---|---|---|
| 0. Foundation | Weeks 1 to 4 | Data model, scoring rubric v1, methodology page, legal review of approach |
| 1. MVP | Months 2 to 4 | 3 categories (banking, grocery, clothing), 50 major brands, 3 to 5 alternatives each, flow maps, Twin Cities directory |
| 2. Breadth | Months 5 to 8 | Remaining Tier 1 categories, 200+ brands, user-weighted scoring, swap checklist with savings tracker |
| 3. Platform | Months 9 to 12 | Public API, MCP server, browser add-on for maps and shopping sites |
| 4. Expansion | Year 2 | Tier 2 and 3 categories, more metros, marketplace front door |

## 12. Success metrics

- Swap click-throughs per brand page view (the core proof the concept works)
- Self-reported swaps completed and estimated dollars rerouted per year
- Brands and categories covered with full evidence
- Share of scores backed by primary sources
- Returning visitors and recurring donors
- Correction requests received and resolution time
- API and MCP calls from third parties

## 13. Key risks

| Risk | Mitigation |
|---|---|
| Legal threat from a rated company | Facts-only policy, citations, counsel review, corrections process |
| Data maintenance burden | Automate pulls from public datasets, date-stamp every score, show staleness |
| Perceived bias | Open methodology, user weighting, political direction excluded from default score |
| "Ethical costs more" objection | Lead with money-saving swaps |
| Thin alternatives in some categories | Be honest: say "no good swap, here is how to spend less" |
| Private company opacity | Visible "unknown" scores, invite disclosure |
| Scope creep across four front doors | One backend, ship one category end to end before widening |

## 14. Open decisions

1. Legal structure: nonprofit vs public benefit company.
2. One domain with sections vs separate sites on shared data.
3. Name and brand for the umbrella.
4. Whether affiliate revenue is allowed at all in v1.
5. How much hand review each score gets before publishing.
