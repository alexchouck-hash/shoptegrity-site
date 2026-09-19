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
  Ranks channels from home gardens and CSAs up through regional co-ops and multinational ultra-processed foods, tracking producer dollar retention (from 100% down to under 8%).
- **USDA ERS Food Dollar Split:**
  Interactive visual ledger based on federal USDA Economic Research Service data showing where each cent of $1.00 lands (farm share 11.8¢ vs packaging, wholesale, and retail margin).
- **Small Maker & Grower Registry (including U.S. Tea Proof):**
  Aggregates verified small producers, pasture-raised growers, and tea farms (e.g. Table Rock Tea, Camellia Forest) contrasting direct makers with national aggregators.
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
  Shows the ultimate beneficiary of "indie" brands (e.g., Annie's is General Mills, Burt's Bees is Clorox).
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
- **Disguised Rollup Warning System:**
  Surfaces when private equity platforms (e.g. Apex Service Partners) secretly acquire a local HVAC, plumbing, or veterinary business while keeping the legacy family name to deceive consumers.

---

## 🤖 MCP Server (`mcp/`)

Provides Model Context Protocol tools for AI shopping assistants:
- `lookup_brand(name)`: Brand scorecard, parent corporation, cited evidence.
- `find_alternatives(brand_name)`: Approved higher-integrity alternatives with price bands and rationale.
- `find_local_businesses(lat, lon, category, radius_km)`: Proximity search with ownership tiers.
- `dollar_split_summary(category)`: USDA food dollar and spending breakdowns.

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
