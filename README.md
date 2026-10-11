# Shoptegrity Platform

> **Rerouting Capital to Integrity:** An evidence-backed platform that evaluates corporate integrity, maps food chain health and farmer enrichment, exposes hidden ownership (including disguised private equity rollups), and provides concrete, money-saving swaps.

---

## 🏛️ Ecosystem Overview

Shoptegrity is built as **one data platform powering two distinct partner web experiences, a local proximity engine, and an MCP server**:

```
                                  +-----------------------------+
                                  |    PostgreSQL / SQLite      |
                                  |   (Unified Data Foundation) |
                                  +--------------+--------------+
                                                 |
                                     FastAPI Backend & Engine
                                 (REST API + Pure Scoring Rubric)
                                                 |
         +-----------------------+---------------+-----------------------+
         |                       |                                       |
+--------v---------+    +--------v---------+                    +--------v---------+
|  Partner Site 1: |    |  Partner Site 2: |                    |    MCP Server    |
|   Food Chain     |    | Brand Integrity  |                    |   (AI Assistants |
|   Integrity      |    | & Ethical Swaps  |                    |    & Connectors) |
|     (/food)      |    | (/brands, /swaps)|                    +------------------+
+------------------+    +------------------+
```

---

## 🌾 Partner Site 1: Food Chain Integrity (`/food`)

Designed to **assure your food chain is healthy, environmentally conscious, and enriches the appropriate people**:
- **The Universal Food Sourcing Ladder (Tiers 1–9):**
  Ranks channels from home gardens and CSAs up through regional co-ops and multinational ultra-processed foods. A producer's share of the dollar is shown only with a cited source.
- **USDA ERS Food Dollar Split:**
  A visual ledger of where each cent of a food dollar goes (farm share, processing, packaging, transportation, wholesale, and retail). Each figure is withheld until it is cited to the USDA Economic Research Service Food Dollar Series.
- **Small Maker & Grower Registry (including U.S. Tea Proof):**
  Lists small producers, pasture-raised growers, and U.S. tea farms, each linked to its own website.
- **Equity Access:**
  Flags SNAP, WIC, and EBT acceptance across farmers markets and food co-ops.

---

## 🏢 Partner Site 2: Brand Integrity & Ethical Shopping (`/brands`, `/swaps`)

Designed to **rank major consumer brands on integrity, provide actionable swaps, and list better local alternatives**:
- **Six-Dimension Evidence Scorecards:**
  1. *Ownership & Structure* (Worker Co-op/ESOP = 95–100, Private Equity = 10)
  2. *Capital Extraction* (Buybacks and dividends as % of net earnings)
  3. *Pay Equity* (CEO-to-median-worker ratio from SEC Item 402(u))
  4. *Labor Practices* (OSHA penalties, NLRB violations, living wage status)
  5. *Environmental Impact* (EPA ECHO enforcement, USDA Organic, regenerative)
  6. *Locality & Community Wealth* (Recirculation factor vs multinational leak)
- **Parent Company Mapping:**
  Shows a brand's parent company only when a cited source (a filing or other public record, with its link) ties the brand to that parent.
- **Better Brand Data Sources:**
  Curated direct links to B Corp directories, 100% Employee-Owned (NCEO) registries, and Worker Co-op databases.
- **Step-by-Step Swap Guides (`/swaps`):**
  Prioritizes high-spend, high-impact moves (Banking to Credit Unions, Fast Fashion to Repair/Mission brands).
- **$100 Dollar Flow Maps (`/flows`):**
  Side-by-side spending breakdowns comparing $100 spent at a megacorp vs a member-owned cooperative.

---

## 📍 Local Directory & PE Rollup Detector (`/local`)

Answers one core question for service businesses: **who actually owns this, and does the money stay local?**
- **The Ownership Ladder (Tiers 1–6):**
  From single-location owner-operators up to public corporations.
- **Rollup Warning System:**
  Shows that a local HVAC, plumbing, or veterinary business is owned by a private equity platform only when a cited source documents the acquisition. An acquired business can keep its original name, so the listing names the owner of record.

---

## 🤖 MCP Server (`mcp/`)

Provides Model Context Protocol tools for AI shopping assistants:
- `lookup_brand(name)`: Brand scorecard, parent corporation, cited evidence.
- `find_alternatives(brand_name)`: Approved higher-integrity alternatives with price bands and rationale.
- `find_local_businesses(lat, lon, category, radius_km)`: Proximity search with ownership tiers.
- `dollar_split_summary(category)`: USDA food dollar and spending breakdowns.

---

## 🌐 Deploying the public site (Cloudflare Pages)

The public site at shopteg.com is a static export. Cloudflare Pages builds it from `main`.

Set these in the Pages project (Settings → Builds):

- **Framework preset:** None
- **Production branch:** `main`
- **Root directory:** blank (repository root)
- **Build command:** `pip install -r requirements.txt && python build_static.py --out dist --base-url ""`
- **Build output directory:** `dist`
- **Environment variable:** `PYTHON_VERSION` = `3.12.10`
- **Custom domain:** `shopteg.com`

The build exits non-zero, and nothing is published, if any page fails to render or any internal link points at a file that does not exist. To check locally, run `python build_static.py --out dist` from the repository root.

The build writes `api/v1/*.json`, `data/private/verification_queue.csv`, and `dist/`. The `api/v1/*.json` files are tracked and the build regenerates them.

`data/private/verification_queue.csv` lists every withheld claim with its value, so it is gitignored and must never be committed: this repository is public, and a tracked copy would publish what the site withholds. Run the build, or `python -m pipeline.provenance`, to regenerate it locally.

The build also fails if a file in `dist/static/img` is not referenced by any exported page, stylesheet, script or JSON file, unless `STATIC_IMG_ALLOWLIST` in `build_static.py` lists it with a reason. Every file in `dist` is public whether or not a page links it.

---

## 🚀 Quickstart

### 1. Requirements & Setup
Ensure Python 3.12+ is installed.
```bash
# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Seed Database
```bash
python -m pipeline.seed_data
```

### 3. Run Automated Tests
```bash
python -m pytest
```
*(Runs 12 unit and integration tests across the rubric scoring engine, REST API, web views, and MCP server)*

### 4. Start Development Server
```bash
python run.py
```
Open **http://127.0.0.1:8000** in your browser to explore:
- Main Portal: `http://127.0.0.1:8000/`
- Food Chain Integrity: `http://127.0.0.1:8000/food`
- Brand Integrity & Scorecards: `http://127.0.0.1:8000/brands`
- Local Directory & PE Rollup Check: `http://127.0.0.1:8000/local`
- Swap Guides: `http://127.0.0.1:8000/swaps`
- Dollar Flow Maps: `http://127.0.0.1:8000/flows`
- Public Methodology & Firewall: `http://127.0.0.1:8000/methodology`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`
