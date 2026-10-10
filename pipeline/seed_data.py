"""Seed script for Shoptegrity.

Populates spend categories, entities, brands, cited evidence, alternatives,
food makers, local places, and flow profiles.

Sourced or withheld: a claim about a named company, place, or program is seeded
only with a citation (an Evidence row with source_url). Figures, certifications,
verification statuses, savings estimates, and comparative price claims without a
citation are not seeded. Their fields hold "Withheld: no cited source yet" or are
left empty.
"""

from api.app.db.session import SessionLocal, init_db
from api.app.models.core import (
    Entity,
    Brand,
    SpendCategory,
    Evidence,
    Alternative,
    FlowProfile,
    Place,
    Maker,
)

WITHHELD = "Withheld: no cited source yet"


def run_seed():
    init_db()
    db = SessionLocal()

    # Recreate alternatives table to ensure schema matches latest model
    Alternative.__table__.drop(db.bind, checkfirst=True)
    Alternative.__table__.create(db.bind, checkfirst=True)

    # Clear existing data
    db.query(Alternative).delete()
    db.query(Maker).delete()
    db.query(Place).delete()
    db.query(FlowProfile).delete()
    db.query(Evidence).delete()
    db.query(Brand).delete()
    db.query(Entity).delete()
    db.query(SpendCategory).delete()
    db.commit()

    print("Populating Spend Categories...")
    cats = [
        SpendCategory(
            id="cat-banking",
            name="Banking & Finance",
            slug="banking",
            tier=1,
            avg_annual_spend=4200.0,
            swap_difficulty="easy",
            saves_money=True,
            description="Checking, savings, mortgages, and loans. Moving from megabanks to credit unions changes where deposit and loan money goes.",
        ),
        SpendCategory(
            id="cat-grocery",
            name="Grocery & Food",
            slug="grocery",
            tier=1,
            avg_annual_spend=8400.0,
            swap_difficulty="easy",
            saves_money=True,
            description="Pantry, produce, dairy, and meat. Reroutes grocery dollars to farmer co-ops and local growers.",
        ),
        SpendCategory(
            id="cat-clothing",
            name="Clothing & Apparel",
            slug="clothing",
            tier=1,
            avg_annual_spend=2200.0,
            swap_difficulty="moderate",
            saves_money=True,
            description="Garments and footwear. Prioritizes durability, repair, thrift, and fair trade labor.",
        ),
        SpendCategory(
            id="cat-insurance",
            name="Insurance",
            slug="insurance",
            tier=1,
            avg_annual_spend=3100.0,
            swap_difficulty="moderate",
            saves_money=True,
            description="Auto and home insurance. Swapping to mutual and policyholder-owned insurers.",
        ),
        SpendCategory(
            id="cat-hardware",
            name="Hardware & Home Services",
            slug="hardware",
            tier=1,
            avg_annual_spend=1500.0,
            swap_difficulty="easy",
            saves_money=False,
            description="Tools, plumbing, HVAC, and repairs. Supporting local owner-operators and co-ops.",
        ),
    ]
    for c in cats:
        db.add(c)
    db.commit()

    print("Populating Entities...")
    # ownership_type is kept only where a published, cited ownership Evidence row below supports it.
    # Otherwise it is "unknown". locality_tier, the CEO pay ratio, and the capital extraction ratio
    # have no citation, so they are unknown or None.
    entities = [
        # --- Conventional Megacorps ---
        Entity(
            id="ent-genmills",
            name="General Mills, Inc.",
            slug="general-mills",
            kind="company",
            ownership_type="public",
            hq_city=None,
            hq_state=None,
            is_public=True,
            ticker="GIS",
            website="https://www.generalmills.com",
            ceo_pay_ratio=None,
            capital_extraction_ratio=None,
            locality_tier="unknown",
            notes=WITHHELD,
        ),
        Entity(
            id="ent-nestle",
            name="Nestlé S.A.",
            slug="nestle",
            kind="company",
            ownership_type="unknown",
            hq_city=None,
            hq_state=None,
            hq_country="Switzerland",
            is_public=True,
            ticker=None,
            website="https://www.nestle.com",
            ceo_pay_ratio=None,
            capital_extraction_ratio=None,
            locality_tier="unknown",
            notes=WITHHELD,
        ),
        Entity(
            id="ent-wellsfargo",
            name="Wells Fargo & Company",
            slug="wells-fargo",
            kind="company",
            ownership_type="unknown",
            hq_city=None,
            hq_state=None,
            is_public=True,
            ticker=None,
            website="https://www.wellsfargo.com",
            ceo_pay_ratio=None,
            capital_extraction_ratio=None,
            locality_tier="unknown",
            notes=WITHHELD,
        ),
        Entity(
            id="ent-tyson",
            name="Tyson Foods, Inc.",
            slug="tyson-foods",
            kind="company",
            ownership_type="unknown",
            hq_city=None,
            hq_state=None,
            is_public=True,
            ticker=None,
            website="https://www.tysonfoods.com",
            ceo_pay_ratio=None,
            capital_extraction_ratio=None,
            locality_tier="unknown",
            notes=WITHHELD,
        ),
        Entity(
            id="ent-shein",
            name="Roadget Business Pte. Ltd. (Shein)",
            slug="shein",
            kind="company",
            ownership_type="unknown",
            hq_city=None,
            hq_state=None,
            hq_country="Singapore",
            is_public=False,
            website="https://www.shein.com",
            ceo_pay_ratio=None,
            capital_extraction_ratio=None,
            locality_tier="unknown",
            notes=WITHHELD,
        ),
        Entity(
            id="ent-bigelow",
            name="R.C. Bigelow, Inc.",
            slug="bigelow-tea",
            kind="company",
            ownership_type="unknown",
            hq_city=None,
            hq_state=None,
            is_public=False,
            website="https://www.bigelowtea.com",
            ceo_pay_ratio=None,
            capital_extraction_ratio=None,
            locality_tier="unknown",
            notes=WITHHELD,
        ),
        Entity(
            id="ent-apex-pe",
            name="Apex Service Partners",
            slug="apex-service-partners",
            kind="pe_firm",
            ownership_type="private_equity",
            hq_city=None,
            hq_state=None,
            is_public=False,
            website="https://www.apexservicepartners.com",
            ceo_pay_ratio=None,
            capital_extraction_ratio=None,
            locality_tier="unknown",
            notes=WITHHELD,
        ),

        # --- Cooperatives and Alternatives ---
        Entity(
            id="ent-equalexchange",
            name="Equal Exchange",
            slug="equal-exchange",
            kind="cooperative",
            ownership_type="worker_coop",
            hq_city=None,
            hq_state=None,
            is_public=False,
            website="https://equalexchange.coop",
            ceo_pay_ratio=None,
            capital_extraction_ratio=None,
            locality_tier="unknown",
            notes=WITHHELD,
        ),
        Entity(
            id="ent-organicvalley",
            name="CROPP Cooperative (Organic Valley)",
            slug="organic-valley",
            kind="cooperative",
            ownership_type="producer_coop",
            hq_city=None,
            hq_state=None,
            is_public=False,
            website="https://www.organicvalley.coop",
            ceo_pay_ratio=None,
            capital_extraction_ratio=None,
            locality_tier="unknown",
            notes=WITHHELD,
        ),
        Entity(
            id="ent-kingarthur",
            name="King Arthur Baking Company",
            slug="king-arthur-baking",
            kind="company",
            ownership_type="unknown",
            hq_city=None,
            hq_state=None,
            is_public=False,
            website="https://www.kingarthurbaking.com",
            ceo_pay_ratio=None,
            capital_extraction_ratio=None,
            locality_tier="unknown",
            notes=WITHHELD,
        ),
        Entity(
            id="ent-bobsredmill",
            name="Bob's Red Mill Natural Foods",
            slug="bobs-red-mill",
            kind="company",
            ownership_type="unknown",
            hq_city=None,
            hq_state=None,
            is_public=False,
            website="https://www.bobsredmill.com",
            ceo_pay_ratio=None,
            capital_extraction_ratio=None,
            locality_tier="unknown",
            notes=WITHHELD,
        ),
        Entity(
            id="ent-drbronners",
            name="All-One God Faith, Inc. (Dr. Bronner's)",
            slug="dr-bronners",
            kind="company",
            ownership_type="unknown",
            hq_city=None,
            hq_state=None,
            is_public=False,
            website="https://www.drbronner.com",
            ceo_pay_ratio=None,
            capital_extraction_ratio=None,
            locality_tier="unknown",
            notes=WITHHELD,
        ),
        Entity(
            id="ent-affinityplus",
            name="Affinity Plus Federal Credit Union",
            slug="affinity-plus",
            kind="cooperative",
            ownership_type="credit_union",
            hq_city=None,
            hq_state=None,
            is_public=False,
            website="https://www.affinityplus.org",
            ceo_pay_ratio=None,
            capital_extraction_ratio=None,
            locality_tier="unknown",
            notes=WITHHELD,
        ),
        Entity(
            id="ent-patagonia",
            name="Patagonia, Inc.",
            slug="patagonia",
            kind="company",
            ownership_type="unknown",
            hq_city=None,
            hq_state=None,
            is_public=False,
            website="https://www.patagonia.com",
            ceo_pay_ratio=None,
            capital_extraction_ratio=None,
            locality_tier="unknown",
            notes=WITHHELD,
        ),
        Entity(
            id="ent-aldi",
            name="ALDI US",
            slug="aldi-us",
            kind="company",
            ownership_type="unknown",
            hq_city=None,
            hq_state=None,
            is_public=False,
            website="https://www.aldi.us",
            ceo_pay_ratio=None,
            capital_extraction_ratio=None,
            locality_tier="unknown",
            notes=WITHHELD,
        ),
        Entity(
            id="ent-pact",
            name="Pact Organic",
            slug="pact-apparel",
            kind="company",
            ownership_type="unknown",
            hq_city=None,
            hq_state=None,
            is_public=False,
            website="https://wearpact.com",
            ceo_pay_ratio=None,
            capital_extraction_ratio=None,
            locality_tier="unknown",
            notes=WITHHELD,
        ),
        Entity(
            id="ent-alliant",
            name="Alliant Credit Union",
            slug="alliant-credit-union",
            kind="credit_union",
            ownership_type="unknown",
            hq_city=None,
            hq_state=None,
            is_public=False,
            website="https://www.alliantcreditunion.org",
            ceo_pay_ratio=None,
            capital_extraction_ratio=None,
            locality_tier="unknown",
            notes=WITHHELD,
        ),
    ]

    for ent in entities:
        db.add(ent)
    db.commit()

    print("Populating Brands...")
    brands = [
        # Conventional
        Brand(
            id="br-annies",
            name="Annie's Homegrown",
            slug="annies-homegrown",
            entity_id="ent-genmills",
            description="Packaged mac and cheese and snacks.",
            website="https://www.annies.com",
            category_tags=["grocery", "pasta", "snacks"],
        ),
        Brand(
            id="br-cheerios",
            name="Cheerios",
            slug="cheerios",
            entity_id="ent-genmills",
            description="Cereal brand.",
            website="https://www.cheerios.com",
            category_tags=["grocery", "cereal"],
        ),
        Brand(
            id="br-purelife",
            name="Pure Life / Bottled Water",
            slug="pure-life-water",
            entity_id="ent-nestle",
            description="Bottled water. Sourcing details: " + WITHHELD + ".",
            website="https://www.nestlepurelife.com",
            category_tags=["grocery", "water"],
        ),
        Brand(
            id="br-wellsfargo",
            name="Wells Fargo Consumer Banking",
            slug="wells-fargo-banking",
            entity_id="ent-wellsfargo",
            description="Retail banking, credit cards, and mortgage services.",
            website="https://www.wellsfargo.com",
            category_tags=["banking"],
        ),
        Brand(
            id="br-shein",
            name="SHEIN Fast Fashion",
            slug="shein-clothing",
            entity_id="ent-shein",
            description="Online clothing brand.",
            website="https://www.shein.com",
            category_tags=["clothing"],
        ),
        Brand(
            id="br-bigelow",
            name="Bigelow Tea",
            slug="bigelow-tea-brand",
            entity_id="ent-bigelow",
            description="Tea brand.",
            website="https://www.bigelowtea.com",
            category_tags=["grocery", "tea"],
        ),

        # Alternatives
        Brand(
            id="br-organicvalley",
            name="Organic Valley Dairy",
            slug="organic-valley-dairy",
            entity_id="ent-organicvalley",
            description="Farmer-owned milk, cheese, and butter.",
            website="https://www.organicvalley.coop",
            category_tags=["grocery", "dairy"],
        ),
        Brand(
            id="br-equalexchange",
            name="Equal Exchange Organic Tea & Coffee",
            slug="equal-exchange-tea",
            entity_id="ent-equalexchange",
            description="Worker-owned cooperative tea and coffee.",
            website="https://equalexchange.coop",
            category_tags=["grocery", "tea", "coffee"],
        ),
        Brand(
            id="br-kingarthur",
            name="King Arthur Baking",
            slug="king-arthur-flour",
            entity_id="ent-kingarthur",
            description="Flours, baking mixes, and pantry staples.",
            website="https://www.kingarthurbaking.com",
            category_tags=["grocery", "baking"],
        ),
        Brand(
            id="br-bobsredmill",
            name="Bob's Red Mill Grains & Oats",
            slug="bobs-red-mill-brand",
            entity_id="ent-bobsredmill",
            description="Grains, oats, and cereal alternatives.",
            website="https://www.bobsredmill.com",
            category_tags=["grocery", "cereal", "grains"],
        ),
        Brand(
            id="br-affinityplus",
            name="Affinity Plus Credit Union Accounts",
            slug="affinity-plus-banking",
            entity_id="ent-affinityplus",
            description="Member-owned checking, savings, and mortgage accounts.",
            website="https://www.affinityplus.org",
            category_tags=["banking"],
        ),
        Brand(
            id="br-patagonia",
            name="Patagonia Outdoor Apparel",
            slug="patagonia-apparel",
            entity_id="ent-patagonia",
            description="Outdoor apparel.",
            website="https://www.patagonia.com",
            category_tags=["clothing"],
        ),
        Brand(
            id="br-aldi",
            name="ALDI Simply Nature & Staples",
            slug="aldi-groceries",
            entity_id="ent-aldi",
            description="Staple groceries and pantry items.",
            website="https://www.aldi.us",
            category_tags=["grocery"],
        ),
        Brand(
            id="br-pact",
            name="Pact Organic Everyday Basics",
            slug="pact-basics",
            entity_id="ent-pact",
            description="Cotton tees, socks, and loungewear.",
            website="https://wearpact.com",
            category_tags=["clothing"],
        ),
        Brand(
            id="br-alliant",
            name="Alliant High-Yield Checking & Mobile Banking",
            slug="alliant-banking",
            entity_id="ent-alliant",
            description="Digital checking and savings accounts.",
            website="https://www.alliantcreditunion.org",
            category_tags=["banking"],
        ),
    ]

    for b in brands:
        db.add(b)
    db.commit()

    print("Populating Cited Evidence...")
    # Only rows with a source_url are seeded. Status is set to "published" explicitly because
    # these rows carry a citation. New rows default to "pending" in the model.
    evidence_items = [
        Evidence(
            entity_id="ent-genmills",
            dimension="capital_extraction",
            fact_text="General Mills paid about $3.3 billion in dividends and net share repurchases in FY2024, about 134% of its $2.5 billion in net earnings (FY2024 Form 10-K).",
            source_url="https://www.sec.gov/Archives/edgar/data/0000040704/000119312524168943/d764890d10k.htm",
            source_name="General Mills FY2024 Form 10-K (SEC EDGAR), MD&A",
            source_type="sec_edgar",
            retrieved_at="2026-09-01",
            impact=-1,
            status="published",
        ),
        # The General Mills CEO pay row (2024 proxy) was removed. Its figures are for a different
        # fiscal year from the FY2026 filing in the brand database ($14.02M), so the two conflict.
        # Re-add it with a citation to the filing it describes.
        Evidence(
            entity_id="ent-wellsfargo",
            dimension="labor",
            fact_text="CFPB ordered Wells Fargo to pay $3.7B in customer redress and penalties over widespread consumer account abuses.",
            source_url="https://www.consumerfinance.gov/about-us/newsroom/cfpb-orders-wells-fargo-to-pay-37-billion-for-widespread-mismanagement-of-auto-loans-mortgages-and-deposit-accounts/",
            source_name="Consumer Financial Protection Bureau Enforcement Order",
            source_type="cfpb",
            retrieved_at="2026-09-01",
            impact=-2,
            status="published",
        ),
        Evidence(
            entity_id="ent-equalexchange",
            dimension="ownership",
            fact_text="Each worker-owner has one vote, not one vote per share, according to the co-op's website.",
            source_url="https://info.equalexchange.coop/articles/a-worker-owned-cooperative",
            source_name="Equal Exchange website: Our Worker-Owned Cooperative",
            source_type="company_disclosure",
            retrieved_at="2026-09-01",
            impact=2,
            status="published",
        ),
        Evidence(
            entity_id="ent-equalexchange",
            dimension="pay_equity",
            fact_text="Equal Exchange reports a 5:1 pay ratio between its top and bottom full-time employees, according to its website.",
            source_url="https://shop.equalexchange.coop/pages/about",
            source_name="Equal Exchange 'About' page (company website)",
            source_type="company_disclosure",
            retrieved_at="2026-09-01",
            impact=2,
            status="published",
        ),
        Evidence(
            entity_id="ent-organicvalley",
            dimension="ownership",
            fact_text="Owned by its farmer members, according to an Organic Valley statement quoted by GEO.",
            source_url="https://www.geo.coop/gleanings/cooperatives-working-toward-common-goal",
            source_name="GEO article quoting Organic Valley",
            source_type="company_disclosure",
            retrieved_at="2026-09-01",
            impact=2,
            status="published",
        ),
        Evidence(
            entity_id="ent-affinityplus",
            dimension="ownership",
            fact_text="Federally insured by the National Credit Union Administration.",
            source_url="https://www.affinityplus.org/about-us/how-were-insured",
            source_name="Affinity Plus website: How we're insured",
            source_type="ncua",
            retrieved_at="2026-09-01",
            impact=2,
            status="published",
        ),
        Evidence(
            entity_id="ent-apex-pe",
            dimension="ownership",
            fact_text="Alpine Investors is named as an investor in Apex Service Partners.",
            source_url="https://www.apollo.com/insights-news/pressreleases/2026/05/apex-service-partners-and-alpine-investors-announce-strategic-mi",
            source_name="Apollo press release, May 28, 2026",
            source_type="trade_press",
            retrieved_at="2026-09-01",
            impact=-2,
            status="published",
        ),
    ]

    for ev in evidence_items:
        db.add(ev)
    db.commit()

    print("Populating Alternatives...")
    # Price bands and savings estimates are withheld (no citation). Rationales avoid
    # comparative price, savings, certification, and ownership claims that lack a citation.
    alts = [
        # Annie's Homegrown -> Better & Best

        # Cheerios -> Better & Best
        Alternative(
            from_brand_id="br-cheerios",
            to_brand_id="br-bobsredmill",
            spend_category_id="cat-grocery",
            rationale="Whole grain rolled oats as an alternative to packaged cereal. Ownership and packaging comparisons: " + WITHHELD + ".",
            price_band="",
            where_to_buy="Co-ops, bulk food bins, and regional grocers.",
            savings_estimate=None,
            swap_tier="best",
            similarity_notes="Different format: whole rolled oats from bulk bins; requires cooking.",
            editor_approved=True,
        ),

        # Wells Fargo -> Better & Best
        Alternative(
            from_brand_id="br-wellsfargo",
            to_brand_id="br-alliant",
            spend_category_id="cat-banking",
            rationale="Digital checking and savings account as an alternative. Fee and ATM comparisons: " + WITHHELD + ".",
            price_band="",
            where_to_buy="Online and mobile app.",
            savings_estimate=None,
            swap_tier="better",
            similarity_notes=None,
            editor_approved=True,
        ),
        Alternative(
            from_brand_id="br-wellsfargo",
            to_brand_id="br-affinityplus",
            spend_category_id="cat-banking",
            rationale="Checking and savings from a member-owned credit union (see its cited NCUA record). Fee and loan-rate comparisons: " + WITHHELD + ".",
            price_band="",
            where_to_buy="Online and regional branches.",
            savings_estimate=None,
            swap_tier="best",
            similarity_notes="May differ: branch and ATM access.",
            editor_approved=True,
        ),

        # SHEIN -> Better & Best
        Alternative(
            from_brand_id="br-shein",
            to_brand_id="br-pact",
            spend_category_id="cat-clothing",
            rationale="Cotton basics from a clothing brand. Price, certification, and labor comparisons: " + WITHHELD + ".",
            price_band="",
            where_to_buy="Online direct at wearpact.com.",
            savings_estimate=None,
            swap_tier="better",
            similarity_notes="Similar online ordering and doorstep delivery; everyday casual basics.",
            editor_approved=True,
        ),
        Alternative(
            from_brand_id="br-shein",
            to_brand_id="br-patagonia",
            spend_category_id="cat-clothing",
            rationale="Outdoor clothing brand. Price, repair, and lifetime-cost comparisons: " + WITHHELD + ".",
            price_band="",
            where_to_buy="Patagonia stores, Worn Wear (used), or authorized retailers.",
            savings_estimate=None,
            swap_tier="best",
            similarity_notes="May differ in price point and care approach.",
            editor_approved=True,
        ),

        # Bigelow Tea -> Best
        Alternative(
            from_brand_id="br-bigelow",
            to_brand_id="br-equalexchange",
            spend_category_id="cat-grocery",
            rationale="Tea from a worker-owned cooperative (see its cited ownership record). Price and sourcing comparisons: " + WITHHELD + ".",
            price_band="",
            where_to_buy="Natural food co-ops and Equal Exchange online store.",
            savings_estimate=None,
            swap_tier="best",
            similarity_notes="Worker-owned cooperative tea brand.",
            editor_approved=True,
        ),
    ]

    for a in alts:
        db.add(a)
    db.commit()

    print("Populating Dollar Flow Profiles...")
    # Split amounts are withheld: no citation supports them. Each profile keeps its shape
    # (input_spend and an empty splits list) so that existing readers still work.
    flows = [
        FlowProfile(
            id="flow-grocery-conventional",
            spend_category_id="cat-grocery",
            option_type="conventional",
            display_title="Conventional Supermarket Chain",
            year=2024,
            nodes_json={"input_spend": 100.0, "splits": []},
            summary_text=WITHHELD,
            source_notes=WITHHELD,
        ),
        FlowProfile(
            id="flow-grocery-coop",
            spend_category_id="cat-grocery",
            option_type="alternative",
            display_title="Member-Owned Food Cooperative",
            year=2024,
            nodes_json={"input_spend": 100.0, "splits": []},
            summary_text=WITHHELD,
            source_notes=WITHHELD,
        ),
        FlowProfile(
            id="flow-banking-conventional",
            spend_category_id="cat-banking",
            option_type="conventional",
            display_title="Megabank",
            year=2024,
            nodes_json={"input_spend": 100.0, "splits": []},
            summary_text=WITHHELD,
            source_notes=WITHHELD,
        ),
        FlowProfile(
            id="flow-banking-coop",
            spend_category_id="cat-banking",
            option_type="alternative",
            display_title="Community Credit Union",
            year=2024,
            nodes_json={"input_spend": 100.0, "splits": []},
            summary_text=WITHHELD,
            source_notes=WITHHELD,
        ),
    ]

    for f in flows:
        db.add(f)
    db.commit()

    print("Populating Local Places & Food Makers...")
    # Place rows carry no citation of their own, so verified_how is "Unverified", verified_locally
    # is False, and ownership_tier is 0 (unknown) with no ownership flags. The St. Paul credit union
    # branch is linked to its parent credit union, whose NCUA record is cited; that is the only
    # ownership citation in the seed.
    places = [
        # Twin Cities Co-ops & Markets
        Place(
            id="plc-wedge",
            name="Wedge Community Co-op",
            slug="wedge-coop-lyndale",
            category="food_coop",
            address="2105 Lyndale Ave S",
            city="Minneapolis",
            state="MN",
            postal_code="55405",
            lat=44.9625,
            lon=-93.2882,
            phone="(612) 871-3993",
            website=None,
            ownership_tier=0,
            flags=[],
            verified_locally=False,
            verified_how="Unverified",
            hours="8:00 AM - 10:00 PM daily",
        ),
        Place(
            id="plc-seward",
            name="Seward Community Co-op",
            slug="seward-coop-franklin",
            category="food_coop",
            address="2823 E Franklin Ave",
            city="Minneapolis",
            state="MN",
            postal_code="55406",
            lat=44.9631,
            lon=-93.2305,
            phone="(612) 338-2465",
            website="https://seward.coop",
            ownership_tier=0,
            flags=[],
            verified_locally=False,
            verified_how="Unverified",
            hours="8:00 AM - 10:00 PM daily",
        ),
        Place(
            id="plc-millcity",
            name="Mill City Farmers Market",
            slug="mill-city-farmers-market",
            category="farmers_market",
            address="750 S 2nd St",
            city="Minneapolis",
            state="MN",
            postal_code="55401",
            lat=44.9785,
            lon=-93.2568,
            website="https://millcityfarmersmarket.org",
            ownership_tier=0,
            flags=[],
            verified_locally=False,
            verified_how="Unverified",
            hours="Saturdays May-September 8 a.m.-1 p.m.; October 9 a.m.-1 p.m.; first and third Saturdays November-April 9 a.m.-1 p.m. (indoors)",
            season="May through October (indoor winter markets monthly)",
        ),
        Place(
            id="plc-tangletown",
            name="Tangletown Farm Stand & CSA",
            slug="tangletown-farm",
            category="csa",
            address="5353 Nicollet Ave S",
            city="Minneapolis",
            state="MN",
            postal_code="55419",
            lat=44.9056,
            lon=-93.2783,
            website="https://tangletowngardens.com",
            ownership_tier=0,
            flags=[],
            verified_locally=False,
            verified_how="Unverified",
        ),
        Place(
            id="plc-cu-stpaul",
            name="Affinity Plus Credit Union (St. Paul Branch)",
            slug="affinity-plus-stpaul",
            category="credit_union",
            address="175 W Lafayette Frontage Rd",
            city="St. Paul",
            state="MN",
            postal_code="55107",
            lat=44.9421,
            lon=-93.0825,
            phone="(800) 322-7228",
            website="https://www.affinityplus.org",
            entity_id="ent-affinityplus",
            ownership_tier=0,
            flags=["coop"],
            verified_locally=False,
            verified_how="Parent credit union: NCUA Charter #62608, https://mapping.ncua.gov/CreditUnionDetails/62608. Branch address not separately verified.",
            hours="Lobby: Mon-Fri 9 a.m.-5 p.m., Sat 9 a.m.-12 p.m.; drive-up: Mon-Fri 9 a.m.-5 p.m., Sat 9 a.m.-1 p.m.; closed Sunday",
        ),

        # Local trades

        # Tea growers
        Place(
            id="plc-charleston-tea",
            name="Charleston Tea Garden",
            slug="charleston-tea-garden",
            category="farm_stand",
            address="6617 Maybank Hwy",
            city="Wadmalaw Island",
            state="SC",
            postal_code="29487",
            lat=32.6179,
            lon=-80.1989,
            website="https://charlestonteagarden.com",
            entity_id=None,
            ownership_tier=0,
            flags=[],
            verified_locally=False,
            verified_how="Unverified",
        ),
        Place(
            id="plc-tablerock-tea",
            name="Table Rock Tea Company",
            slug="table-rock-tea",
            category="farm_stand",
            address="118 High Hills Lane",
            city="Pickens",
            state="SC",
            postal_code="29671",
            lat=34.9812,
            lon=-82.7214,
            website="https://tablerocktea.com",
            ownership_tier=0,
            flags=[],
            verified_locally=False,
            verified_how="Unverified",
        ),
        Place(
            id="plc-camellia-forest",
            name="Camellia Forest Tea Gardens",
            slug="camellia-forest-tea",
            category="farm_stand",
            address="Street address not verified",
            city="Chapel Hill",
            state="NC",
            postal_code="27516",
            lat=36.0312,
            lon=-79.0815,
            website="https://www.teaflowergardens.com",
            ownership_tier=0,
            flags=[],
            verified_locally=False,
            verified_how="Unverified",
        ),
    ]

    for p in places:
        db.add(p)
    db.commit()

    makers = [
        Maker(
            id="mkr-tablerock",
            name="Table Rock Tea Farm & Artisans",
            place_id="plc-tablerock-tea",
            products=[],
            makes_own=True,
            makes_own_evidence=WITHHELD,
            certifications=[],
            sourcing_ladder_tier=3,
            where_to_buy="Direct from farm web store or on-site visitor center.",
            direct_order_url="https://tablerocktea.com/shop",
        ),
        Maker(
            id="mkr-camellia",
            name="Camellia Forest Tea Maker",
            place_id="plc-camellia-forest",
            products=["Tea plants"],
            makes_own=True,
            makes_own_evidence=WITHHELD,
            certifications=[],
            sourcing_ladder_tier=3,
            where_to_buy="Farm web store and regional seasonal markets.",
            direct_order_url=None,
        ),
        Maker(
            id="mkr-charleston",
            name="American Classic Tea (Charleston Tea Garden)",
            place_id="plc-charleston-tea",
            products=["American Classic Pouch", "American Classic Pyramid", "Peachy Peach Pouch", "Peachy Peach Pyramid"],
            makes_own=True,
            makes_own_evidence=WITHHELD,
            certifications=[],
            sourcing_ladder_tier=5,
            where_to_buy="Charleston gift shop, online, and select grocery stores.",
            direct_order_url="https://charlestonteagarden.com",
        ),
        Maker(
            id="mkr-tangletown",
            name="Tangletown Produce & Heritage Pastures",
            place_id="plc-tangletown",
            products=["CSA membership"],
            makes_own=True,
            makes_own_evidence=WITHHELD,
            certifications=[],
            sourcing_ladder_tier=3,
            where_to_buy="CSA membership and Minneapolis farm store.",
            direct_order_url="https://tangletowngardens.com/csa",
        ),
    ]

    for m in makers:
        db.add(m)
    db.commit()

    # Seed top 2,000 brands database and export JSON
    from pipeline.top2000_brands import seed_top2000_db, export_top2000_json
    seed_top2000_db(db)
    export_top2000_json()

    db.close()
    print("Database successfully seeded with Shoptegrity core data & brand database!")


if __name__ == "__main__":
    run_seed()
