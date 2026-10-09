# The Circular B2B Protocol: Plugging Commercial Leakage in the Peer Economy

*Specification Draft v1.0 — Shoptegrity Foundation*

---

## 1. The Second-Hop Vulnerability

Consumer boycotts and "buy local" campaigns consistently fail to dismantle corporate monopolies for one overlooked reason: **The Second-Hop Leakage.**

Consider this realistic scenario:
1. A conscious consumer spends **$100** at an authentic, independent, family-owned local restaurant.
2. The consumer walks away believing they kept $100 in the local 90% economy.
3. The restaurant owner pays:
   * **$32** to Sysco or US Foods (multinational food distribution cartels).
   * **$18** to an out-of-state Commercial Real Estate Investment Trust (REIT) for rent.
   * **$12** to Toast/Stripe/Chase for payment processing, terminal lease, and banking fees.
   * **$8** to Amazon Business and Uline for packaging, paper towels, and cleaning supplies.
   * **$5** to Intuit/QuickBooks, Google Workspace, and Meta for digital subscriptions and ads.
   * **$5** to an industrial linen/uniform service owned by a private equity roll-up.
4. Only **$20** remains for local labor and the owner's household draw.

**Result:** Despite an independent storefront, **80% of the customer's spend leaked directly into Wall Street holding companies on the second hop.**

If we want working-class and middle-class businesses to break the monopoly stranglehold, **businesses must buy from businesses (B2B) horizontally.**

---

## 2. The Six Critical B2B Leakage Arteries & Their Peer Swaps

| Artery | Default Extractive Monopoly | Circular Peer Alternative | Impact on Community Retention |
|---|---|---|---|
| **1. Food & Supplies Wholesale** | Sysco, US Foods, Performance Food Group | Regional grower cooperatives, direct-farm aggregators, local miller/baker networks | +30–45% captured by local farmers |
| **2. Merchant Services & Banking** | Chase, Wells Fargo, Toast, Stripe (2.9% + 30¢ + float) | Credit unions, member-owned clearinghouses, low-fee open debit rails | Eliminates $3,000–$15,000/yr in extraction per merchant |
| **3. Packaging & Consumables** | Uline, Amazon Business, WebstaurantStore | Regional compostable packaging co-ops, local paper distributors, glass return networks | Replaces out-of-state mega-warehouses with local distributors |
| **4. Maintenance & Facilities** | PE-rolled-up HVAC, national pest control (Rentokil/Rollins), corporate uniform services | Independent trade contractors, worker-owned facilities co-ops, local repair specialists | Retains 70%+ of repair/capex spending in town |
| **5. Software & Marketing** | Meta/Google ads, Yelp extortion, corporate franchise POS | Open-source POS, local directory federations (Shoptegrity MCP), word-of-mouth referral clubs | Drastically lowers customer-acquisition overhead |
| **6. Commercial Space** | Out-of-state REITs, corporate strip-mall developers | Community Land Trusts (CLTs), merchant-owned commercial condominiums, cooperative purchase | Permanently caps rent inflation and preserves Main St equity |

---

## 3. The B2B Sourcing Ladder

Just as Shoptegrity defines a sourcing ladder for retail consumers, businesses must be evaluated and assisted using a **Commercial Procurement Ladder**:

```
LEVEL 1: 100% Peer-to-Peer & Co-op (Worker co-ops, direct growers, credit unions)
  ▲
LEVEL 2: Independent Local Suppliers (Locally owned B2B wholesalers, local trades)
  ▲
LEVEL 3: Regional Independent Networks (Multi-state family/independent distributors)
  ▲
LEVEL 4: Transparent Mid-Market (Private non-PE corporations with verified labor standards)
  ▲
LEVEL 5: Extractive Monopolies & PE Rollups (Sysco, Amazon Business, REITs, Megabanks) [REJECT / PHASE OUT]
```

---

## 4. The Data Model: B2B Peer Directory & Supply Graph

To make horizontal B2B trade frictionless, the Shoptegrity backend will extend its schema to track **upstream vendors and downstream clients**.

```json
{
  "entity_id": "ent_maple_cafe_102",
  "name": "Maple Street Bakery & Cafe",
  "ownership_type": "independent_family",
  "local_spend_index": 0.74,
  "upstream_vendors": [
    {
      "category": "flour_grains",
      "vendor_name": "Valley Grain Growers Co-op",
      "vendor_id": "ent_valley_grain_01",
      "tier": 1,
      "estimated_share_of_cogs": 0.28,
      "verified_peer": true
    },
    {
      "category": "dairy",
      "vendor_name": "Hillside Dairy Farms",
      "vendor_id": "ent_hillside_dairy_04",
      "tier": 2,
      "estimated_share_of_cogs": 0.22,
      "verified_peer": true
    },
    {
      "category": "pos_banking",
      "vendor_name": "Community First Credit Union",
      "vendor_id": "ent_comm_first_cu",
      "tier": 1,
      "verified_peer": true
    },
    {
      "category": "packaging",
      "vendor_name": "Amazon Business",
      "tier": 5,
      "estimated_share_of_cogs": 0.08,
      "verified_peer": false,
      "swap_recommendation": {
        "candidate_id": "ent_midwest_compost_pkg",
        "name": "Midwest Bio-Packaging Co-op",
        "savings_potential": "Parity at 5-case volume"
      }
    }
  ]
}
```

---

## 5. Independent Group Purchasing Organizations (GPOs)

The primary reason small businesses default to corporate distributors like Sysco or Amazon Business is **purchasing volume**. A single cafe buying 5 cases of oat milk pays wholesale retail; a corporate chain buying 50,000 cases gets a 45% discount.

### The Fix: Cooperative Purchasing Alliances
Independent businesses must pool purchasing power without surrendering independence:
1. **The Regional Buying Syndicate:** 20 independent restaurants in one metro area combine their orders for olive oil, flour, compostable containers, and cleaning supplies.
2. **Direct-from-Mill Contracts:** By ordering a full pallet or truckload together, they bypass corporate middlemen and purchase directly from farmer co-ops and regional mills at parity with chain pricing.
3. **Drop-Hub Logistics:** A single member's warehouse, a local food hub, or a local brewer with excess cooler space acts as the central delivery dock.

---

## 6. Mutual Credit & Liquidity: The Sardex / WIR Model

Small businesses face recurring cash-flow crunches. When revenues dip, they turn to merchant cash advances (paying 30–60% effective APR to fintech predatory lenders) or high-interest credit lines from megabanks.

### The Fix: A Peer Mutual-Credit Clearing Ring
Modeled after Switzerland's **WIR Economic Circle** (operational since 1934, supporting 60,000+ businesses) and Italy's **Sardex** (which kept thousands of Sardinian SMEs solvent during the 2008 financial crisis):
* **How It Works:**
  * Member businesses are extended a zero-interest line of electronic credit denominated in 1:1 dollar parity.
  * An electrician does $2,000 of wiring for a local bakery. The electrician is credited 2,000 trade credits.
  * The electrician uses those 2,000 credits to buy fleet maintenance from an independent mechanic or dental services from a local dentist.
  * The bakery settles its negative balance by accepting credits from local customers or fellow business members.
* **Why This Is Revolutionary:**
  * It creates **instant B2B working capital without paying 18% interest to commercial banks**.
  * It forces capital to stay inside the network: credits can *only* be spent with other member independent businesses.

---

## 7. The "Circular Certified" Standard for Businesses

Shoptegrity will award a distinct tier of verification to businesses that close the loop upstream:

1. **Circular Gold:** $\ge 70\%$ of Cost of Goods Sold (COGS) and operational overhead sourced from Tier 1–3 independent/co-op entities; banks exclusively with a credit union or CDFI.
2. **Circular Silver:** $\ge 50\%$ peer-sourced; active transition plan to replace Tier 5 corporate suppliers.
3. **Circular Bronze:** Independent ownership verified, currently auditing supply chain for local peer alternatives.

This certification creates a **B2B Trust Network**. When a conscious consumer walks in, they know they are not just supporting the person at the front counter—they are supporting an entire hidden ecosystem of growers, mechanics, truckers, and artisans who own their work.
