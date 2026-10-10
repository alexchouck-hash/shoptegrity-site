"""Brand and Product Feed Generator.

Compiles a list of consumer brands and products with their categories and search aliases.

Ownership is withheld. The parent-company, ultimate-parent, ownership-type and ticker fields
are written as null, and each record carries ownership_status = "Withheld: no cited source yet",
until every ownership claim has a cited source in the repo (sourced-or-withheld policy).
This generator does not emit subterfuge flags, subterfuge text, enrichment percentages, or
ethical swap names.

Outputs:
- data/brand_parent_feed.json
- data/brand_parent_feed.csv
"""

import csv
import json
import re
from pathlib import Path
from typing import List, Dict, Any


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[\s_-]+", "-", text).strip("-")


WITHHELD_TEXT = "Withheld: no cited source yet"


# Handcrafted brand & product entries: names, categories and search aliases
CORE_BRAND_ENTRIES = [
    # Healthcare & Insurance
    {
        "name": "UnitedHealthcare",
        "type": "brand",
        "category": "Healthcare & Insurance",
        "aliases": ["united healthcare", "unitedhealthcare", "uhc", "united health care", "optum", "medexpress", "optumrx"],
        "products": [
            "UnitedHealthcare Choice Plus",
            "UnitedHealthcare Medicare Advantage",
            "UnitedHealthcare Community Plan",
            "Optum Health Clinic Network",
            "OptumRx Pharmacy Benefit Manager",
            "MedExpress Urgent Care",
        ]
    },
    {
        "name": "HealthPartners",
        "type": "brand",
        "category": "Healthcare & Insurance",
        "aliases": ["healthpartners", "health partners", "park nicollet", "healthpartners clinics"],
        "products": [
            "HealthPartners Consumer Health Plan",
            "HealthPartners Primary Care Clinics",
            "Park Nicollet Medical Clinics",
            "HealthPartners Dental Clinics",
        ]
    },
    {
        "name": "Annie's Homegrown",
        "type": "brand",
        "category": "Food & Grocery Staples",
        "aliases": ["annies", "annies mac and cheese", "annies organic", "annies shells"],
        "products": [
            "Annie's Organic Shells & Real Aged Cheddar Macaroni & Cheese",
            "Annie's Organic Bunny Graham Friends Cookies",
            "Annie's Organic Fruit Snacks Variety Pack",
            "Annie's Homegrown Cheddar Bunnies Baked Snack Crackers",
            "Annie's Organic Cinnamon Rolls with Icing",
            "Annie's Organic Goddess Salad Dressing",
        ]
    },
    {
        "name": "Cascadian Farm",
        "type": "brand",
        "category": "Food & Grocery Staples",
        "aliases": ["cascadian farm", "cascadian farms", "cascadian organic"],
        "products": [
            "Cascadian Farm Organic Purely O's Cereal",
            "Cascadian Farm Organic Frozen Blueberries",
            "Cascadian Farm Organic Dark Chocolate Almond Granola",
            "Cascadian Farm Organic Chewy Chocolate Chip Granola Bars",
            "Cascadian Farm Organic Frozen Sweet Peas",
        ]
    },
    {
        "name": "Muir Glen Organic",
        "type": "brand",
        "category": "Food & Grocery Staples",
        "aliases": ["muir glen", "muir glen tomatoes", "muir glen organic canned"],
        "products": [
            "Muir Glen Organic Diced Canned Tomatoes",
            "Muir Glen Organic Crushed Fire Roasted Tomatoes",
            "Muir Glen Organic Tomato Paste",
            "Muir Glen Organic Traditional Pasta Sauce",
        ]
    },
    {
        "name": "Epic Provisions",
        "type": "brand",
        "category": "Food & Grocery Staples",
        "aliases": ["epic provisions", "epic bar", "epic meat snack"],
        "products": [
            "Epic Provisions Bison Bacon Cranberry Bar",
            "Epic Provisions Beef Apple Bacon Bar",
            "Epic Provisions Traditional Artisanal Pork Rinds",
            "Epic Provisions Grass Fed Beef Tallow",
        ]
    },
    {
        "name": "Larabar",
        "type": "brand",
        "category": "Food & Grocery Staples",
        "aliases": ["larabar", "lara bar", "larabar fruit and nut"],
        "products": [
            "Larabar Peanut Butter Chocolate Chip Gluten Free Bar",
            "Larabar Apple Pie Fruit & Nut Bar",
            "Larabar Cashew Cookie Bar",
            "Larabar Lemon Bar Gluten Free",
        ]
    },
    {
        "name": "Blue Buffalo",
        "type": "brand",
        "category": "Pet Food & Veterinary Care",
        "aliases": ["blue buffalo", "blue wilderness", "blue basics dog food"],
        "products": [
            "Blue Buffalo Life Protection Formula Adult Chicken & Brown Rice Dog Food",
            "Blue Buffalo Wilderness High Protein Grain Free Salmon Dog Food",
            "Blue Buffalo Tastefuls Chicken Pate Wet Cat Food",
            "Blue Buffalo Health Bars Baked with Apples & Yogurt Dog Treats",
        ]
    },

    {
        "name": "Burt's Bees",
        "type": "brand",
        "category": "Personal Care & Cosmetics",
        "aliases": ["burts bees", "burt's bees", "burt bees lip balm"],
        "products": [
            "Burt's Bees 100% Natural Moisturizing Beeswax Lip Balm",
            "Burt's Bees Coconut Foot Cream with Vitamin E",
            "Burt's Bees Hand Salve Herbal Treatment",
            "Burt's Bees Lemon Butter Cuticle Cream",
            "Burt's Bees Sensitive Facial Cleanser with Cotton Extract",
            "Burt's Bees Tinted Lip Balm Red Dahlia",
        ]
    },
    {
        "name": "Natural Vitality (Calm)",
        "type": "brand",
        "category": "Personal Care & Cosmetics",
        "aliases": ["natural vitality", "calm magnesium", "natural vitality calm"],
        "products": [
            "Natural Vitality Calm Magnesium Anti-Stress Drink Mix Sweet Lemon",
            "Natural Vitality Calm Gummies Magnesium Supplement Raspberry Lemon",
            "Natural Vitality Calm Sleep Magnesium Powder with Melatonin",
        ]
    },
    {
        "name": "Renew Life Probiotics",
        "type": "brand",
        "category": "Personal Care & Cosmetics",
        "aliases": ["renew life", "renewlife", "renew life extra care probiotic"],
        "products": [
            "Renew Life Extra Care Probiotic 50 Billion CFU Capsules",
            "Renew Life Women's Care Probiotic Capsules",
            "Renew Life Cleanse More Herbal Detox Tablets",
        ]
    },
    {
        "name": "Rainbow Light Vitamins",
        "type": "brand",
        "category": "Personal Care & Cosmetics",
        "aliases": ["rainbow light", "rainbow light prenatal", "rainbow light mens one"],
        "products": [
            "Rainbow Light Men's One Multivitamin High Potency",
            "Rainbow Light Women's One Daily Multivitamin",
            "Rainbow Light Prenatal One Multivitamin Tablets",
        ]
    },

    {
        "name": "Tom's of Maine",
        "type": "brand",
        "category": "Personal Care & Cosmetics",
        "aliases": ["toms of maine", "tom's of maine", "toms toothpaste"],
        "products": [
            "Tom's of Maine Whole Care Natural Fluoride Toothpaste Spearmint",
            "Tom's of Maine Long Lasting Natural Deodorant Wild Lavender",
            "Tom's of Maine Antiplaque and Whitening Peppermint Toothpaste",
            "Tom's of Maine Children's Natural Silly Strawberry Toothpaste",
        ]
    },
    {
        "name": "Hello Products",
        "type": "brand",
        "category": "Personal Care & Cosmetics",
        "aliases": ["hello toothpaste", "hello products", "hello charcoal toothpaste"],
        "products": [
            "Hello Activated Charcoal with Fresh Mint Whitening Toothpaste",
            "Hello Naturally Whitening Fluoride Toothpaste Farm Grown Mint",
            "Hello Kids Fluoride Free Natural Watermelon Toothpaste",
        ]
    },

    {
        "name": "Native Deodorant",
        "type": "brand",
        "category": "Personal Care & Cosmetics",
        "aliases": ["native deodorant", "native body wash", "native shampoo"],
        "products": [
            "Native Aluminum Free Deodorant Coconut & Vanilla",
            "Native Aluminum Free Deodorant Cucumber & Mint",
            "Native Moisturizing Body Wash Coconut & Vanilla",
            "Native Daily Clean Shampoo Eucalyptus & Mint",
        ]
    },
    {
        "name": "This Is L. (L. Organic)",
        "type": "brand",
        "category": "Personal Care & Cosmetics",
        "aliases": ["this is l", "l organic tampons", "l feminine care"],
        "products": [
            "L. Organic Cotton Regular & Super Tampons Duo Pack",
            "L. Organic Cotton Ultra Thin Regular Pads with Wings",
            "L. 100% Pure Cotton Chlorine Free Liners",
        ]
    },
    {
        "name": "First Aid Beauty",
        "type": "brand",
        "category": "Personal Care & Cosmetics",
        "aliases": ["first aid beauty", "fab ultra repair cream"],
        "products": [
            "First Aid Beauty Ultra Repair Cream Intense Hydration",
            "First Aid Beauty Pure Skin Face Cleanser",
            "First Aid Beauty KP Bump Eraser Body Scrub with 10% AHA",
        ]
    },

    {
        "name": "Ben & Jerry's",
        "type": "brand",
        "category": "Food & Grocery Staples",
        "aliases": ["ben and jerrys", "ben & jerrys", "ben and jerrys ice cream"],
        "products": [
            "Ben & Jerry's Half Baked Ice Cream",
            "Ben & Jerry's Cherry Garcia Ice Cream",
            "Ben & Jerry's Phish Food Chocolate Marshmallow Ice Cream",
            "Ben & Jerry's Chocolate Chip Cookie Dough Ice Cream",
            "Ben & Jerry's Non-Dairy Dairy-Free Phish Food Pint",
        ]
    },
    {
        "name": "Seventh Generation",
        "type": "brand",
        "category": "Household & Cleaning",
        "aliases": ["seventh generation", "seventh generation detergent", "seventh generation dish soap"],
        "products": [
            "Seventh Generation Free & Clear Concentrated Laundry Detergent",
            "Seventh Generation Dish Liquid Free & Clear",
            "Seventh Generation Disinfecting Multi-Surface Cleaner Lemongrass Citrus",
            "Seventh Generation 100% Recycled Bath Tissue",
            "Seventh Generation Chlorine-Free Bleach Alternative",
        ]
    },
    {
        "name": "Sir Kensington's",
        "type": "brand",
        "category": "Food & Grocery Staples",
        "aliases": ["sir kensingtons", "sir kensington", "sir kensingtons mayo"],
        "products": [
            "Sir Kensington's Classic Mayonnaise with Non-GMO Sunflower Oil",
            "Sir Kensington's Classic Ketchup with Whole Vine-Ripened Tomatoes",
            "Sir Kensington's Chipotle Mayonnaise",
            "Sir Kensington's Spicy Brown Mustard",
        ]
    },
    {
        "name": "Liquid I.V.",
        "type": "brand",
        "category": "Personal Care & Cosmetics",
        "aliases": ["liquid iv", "liquid i.v.", "liquid iv hydration"],
        "products": [
            "Liquid I.V. Hydration Multiplier Electrolyte Powder Mix Lemon Lime",
            "Liquid I.V. Hydration Multiplier Passion Fruit",
            "Liquid I.V. Energy Multiplier Yuzu Pineapple",
            "Liquid I.V. Sleep Multiplier Blueberry Lavender",
        ]
    },
    {
        "name": "Schmidt's Deodorant",
        "type": "brand",
        "category": "Personal Care & Cosmetics",
        "aliases": ["schmidts", "schmidt's", "schmidts deodorant"],
        "products": [
            "Schmidt's Natural Deodorant Rose & Vanilla",
            "Schmidt's Bergamot & Lime Natural Mineral Enriched Deodorant",
            "Schmidt's Charcoal & Magnesium Natural Deodorant",
        ]
    },
    {
        "name": "SheaMoisture",
        "type": "brand",
        "category": "Personal Care & Cosmetics",
        "aliases": ["sheamoisture", "shea moisture", "sheamoisture curl smoothie"],
        "products": [
            "SheaMoisture Coconut & Hibiscus Curl & Style Milk",
            "SheaMoisture Jamaican Black Castor Oil Strengthen & Restore Treatment Masque",
            "SheaMoisture Raw Shea Butter Moisture Retention Shampoo",
            "SheaMoisture African Black Soap Bar",
        ]
    },
    {
        "name": "Talenti Gelato",
        "type": "brand",
        "category": "Food & Grocery Staples",
        "aliases": ["talenti", "talenti gelato", "talenti sea salt caramel"],
        "products": [
            "Talenti Sea Salt Caramel Gelato",
            "Talenti Roman Raspberry Sorbetto",
            "Talenti Mediterranean Mint Gelato",
            "Talenti Madagascan Vanilla Bean Gelato",
        ]
    },

    {
        "name": "Rao's Homemade",
        "type": "brand",
        "category": "Food & Grocery Staples",
        "aliases": ["raos", "rao's", "raos marinara", "raos homemade"],
        "products": [
            "Rao's Homemade All Natural Marinara Sauce",
            "Rao's Homemade Arrabiata Spicy Pasta Sauce",
            "Rao's Homemade Vodka Sauce",
            "Rao's Homemade Penne Rigate Bronze Cut Pasta",
            "Rao's Homemade Meatballs in Marinara Sauce Frozen Entree",
        ]
    },
    {
        "name": "Pacific Foods",
        "type": "brand",
        "category": "Food & Grocery Staples",
        "aliases": ["pacific foods", "pacific organic broth", "pacific creamy tomato"],
        "products": [
            "Pacific Foods Organic Free Range Chicken Broth",
            "Pacific Foods Organic Creamy Tomato Soup",
            "Pacific Foods Organic Vegetable Broth",
            "Pacific Foods Organic Bone Broth Chicken with Lemongrass",
            "Pacific Foods Barista Series Oat Milk",
        ]
    },
    {
        "name": "Noosa Yoghurt",
        "type": "brand",
        "category": "Food & Grocery Staples",
        "aliases": ["noosa", "noosa yoghurt", "noosa blueberry"],
        "products": [
            "Noosa Yoghurt Tart Cherry Finest Yoghurt Tub",
            "Noosa Yoghurt Blueberry Whole Milk Yoghurt",
            "Noosa Yoghurt Lemon Australian Style Yoghurt",
        ]
    },

    {
        "name": "Horizon Organic",
        "type": "brand",
        "category": "Food & Grocery Staples",
        "aliases": ["horizon organic", "horizon milk", "horizon organic whole milk"],
        "products": [
            "Horizon Organic Whole Milk with DHA Omega-3",
            "Horizon Organic Lowfat Chocolate Milk Boxes",
            "Horizon Organic Organic Mozzarella String Cheese",
            "Horizon Organic Heavy Whipping Cream",
        ]
    },
    {
        "name": "Silk",
        "type": "brand",
        "category": "Food & Grocery Staples",
        "aliases": ["silk milk", "silk almond milk", "silk soymilk"],
        "products": [
            "Silk Pure Almond Original Almondmilk",
            "Silk Organic Unsweetened Soymilk",
            "Silk Dairy Free Vanilla Almond Creamer",
            "Silk Original Coconutmilk",
        ]
    },
    {
        "name": "SToK Cold Brew",
        "type": "brand",
        "category": "Food & Grocery Staples",
        "aliases": ["stok cold brew", "stok coffee", "stok unsweetened black"],
        "products": [
            "SToK Cold Brew Black Unsweetened Coffee",
            "SToK Cold Brew Not Too Sweet Coffee",
            "SToK Cold Brew Extra Bold Espresso Coffee",
        ]
    },

    {
        "name": "Kind Snacks",
        "type": "brand",
        "category": "Food & Grocery Staples",
        "aliases": ["kind bar", "kind snacks", "kind healthy grains"],
        "products": [
            "Kind Bar Dark Chocolate Nuts & Sea Salt",
            "Kind Bar Caramel Almond & Sea Salt",
            "Kind Healthy Grains Oats & Honey with Toasted Coconut Granola",
            "Kind Minis Variety Pack Snack Bars",
        ]
    },
    {
        "name": "Nature's Bakery",
        "type": "brand",
        "category": "Food & Grocery Staples",
        "aliases": ["natures bakery", "nature's bakery", "natures bakery fig bars"],
        "products": [
            "Nature's Bakery Whole Wheat Fig Bars Real Blueberry",
            "Nature's Bakery Whole Wheat Fig Bars Raspberry",
            "Nature's Bakery Gluten Free Fig Bars Pomegranate",
        ]
    },
    {
        "name": "Banfield Pet Hospital",
        "type": "brand",
        "category": "Pet Food & Veterinary Care",
        "aliases": ["banfield", "banfield pet hospital", "banfield vet", "banfield petsmart"],
        "products": [
            "Banfield Optimum Wellness Plan Monthly Dog Subscription",
            "Banfield Comprehensive Physical Exam & Vaccine Protocol",
            "Banfield Canine Dental Cleaning Package",
        ]
    },
    {
        "name": "VCA Animal Hospitals",
        "type": "brand",
        "category": "Pet Food & Veterinary Care",
        "aliases": ["vca animal hospital", "vca vet", "vca emergency pet"],
        "products": [
            "VCA CareClub Comprehensive Wellness Plan",
            "VCA Veterinary Emergency Consultation & Triage",
            "VCA Specialty Surgical & Ultrasound Diagnostics",
        ]
    },
    {
        "name": "BluePearl Pet Hospital",
        "type": "brand",
        "category": "Pet Food & Veterinary Care",
        "aliases": ["bluepearl", "blue pearl vet", "bluepearl specialty pet hospital"],
        "products": [
            "BluePearl 24/7 Specialty Veterinary Emergency Care",
            "BluePearl Oncology & Chemotherapy Consultation",
        ]
    },

    {
        "name": "Clif Bar",
        "type": "brand",
        "category": "Food & Grocery Staples",
        "aliases": ["clif bar", "clif bars", "clif energy bar"],
        "products": [
            "Clif Bar Energy Bar Chocolate Chip",
            "Clif Bar Crunchy Peanut Butter Energy Bar",
            "Clif Bar White Chocolate Macadamia Nut",
            "Clif Builders Protein Bar Chocolate Mint",
        ]
    },
    {
        "name": "Tate's Bake Shop",
        "type": "brand",
        "category": "Food & Grocery Staples",
        "aliases": ["tates bake shop", "tate's", "tates cookies"],
        "products": [
            "Tate's Bake Shop Crispy Chocolate Chip Cookies",
            "Tate's Bake Shop Gluten Free Chocolate Chip Cookies",
            "Tate's Bake Shop Butter Crunch Cookies",
        ]
    },
    {
        "name": "Perfect Snacks (Perfect Bar)",
        "type": "brand",
        "category": "Food & Grocery Staples",
        "aliases": ["perfect bar", "perfect snacks", "perfect bar peanut butter"],
        "products": [
            "Perfect Bar Original Refrigerated Protein Bar Dark Chocolate Chip Peanut Butter",
            "Perfect Bar Coconut Peanut Butter",
            "Perfect Bar Snack Size Minis Peanut Butter",
        ]
    },

    {
        "name": "Goose Island Brewing",
        "type": "brand",
        "category": "Beer, Wine & Spirits",
        "aliases": ["goose island", "goose island ipa", "goose island bourbon county"],
        "products": [
            "Goose Island IPA India Pale Ale 6-Pack",
            "Goose Island 312 Urban Wheat Ale",
            "Goose Island Bourbon County Stout Vintage",
        ]
    },
    {
        "name": "Elysian Brewing",
        "type": "brand",
        "category": "Beer, Wine & Spirits",
        "aliases": ["elysian", "elysian brewing", "elysian space dust"],
        "products": [
            "Elysian Space Dust IPA 6-Pack Cans",
            "Elysian Contact Haze Hazy IPA",
            "Elysian Night Owl Pumpkin Ale",
        ]
    },
    {
        "name": "Wicked Weed Brewing",
        "type": "brand",
        "category": "Beer, Wine & Spirits",
        "aliases": ["wicked weed", "wicked weed brewing", "wicked weed pernacious"],
        "products": [
            "Wicked Weed Pernicious IPA 6-Pack Cans",
            "Wicked Weed Freak of Nature Double IPA",
            "Wicked Weed Medora Blackberry Sour Ale",
        ]
    },
    {
        "name": "Golden Road Brewing",
        "type": "brand",
        "category": "Beer, Wine & Spirits",
        "aliases": ["golden road", "golden road brewing", "golden road mango cart"],
        "products": [
            "Golden Road Mango Cart Wheat Ale 6-Pack Cans",
            "Golden Road Wolf Pup Session IPA",
        ]
    },
    {
        "name": "Blue Moon Brewing",
        "type": "brand",
        "category": "Beer, Wine & Spirits",
        "aliases": ["blue moon", "blue moon beer", "blue moon belgian white"],
        "products": [
            "Blue Moon Belgian White Wheat Ale 6-Pack Bottles",
            "Blue Moon LightSky Citrus Wheat Cans",
            "Blue Moon Moon Haze Hazy IPA",
        ]
    },
    {
        "name": "Terrapin Beer Co.",
        "type": "brand",
        "category": "Beer, Wine & Spirits",
        "aliases": ["terrapin", "terrapin beer", "terrapin hopsecutioner"],
        "products": [
            "Terrapin Hopsecutioner IPA 6-Pack Cans",
            "Terrapin Luau Krunkles Passion Orange Guava IPA",
        ]
    },
    {
        "name": "Lagunitas Brewing Company",
        "type": "brand",
        "category": "Beer, Wine & Spirits",
        "aliases": ["lagunitas", "lagunitas ipa", "lagunitas little sumpin"],
        "products": [
            "Lagunitas IPA India Pale Ale 6-Pack Bottles",
            "Lagunitas A Little Sumpin' Sumpin' Ale",
            "Lagunitas Daytime Low Calorie IPA Cans",
            "Lagunitas IPNA Non-Alcoholic IPA",
        ]
    },

    {
        "name": "Ray-Ban",
        "type": "brand",
        "category": "Apparel, Footwear & Accessories",
        "aliases": ["ray ban", "ray-ban", "rayban aviator", "rayban wayfarer"],
        "products": [
            "Ray-Ban Classic Wayfarer Polarized Sunglasses",
            "Ray-Ban Classic Aviator Large Metal Gold Frame Sunglasses",
            "Ray-Ban Clubmaster Classic Browline Sunglasses",
            "Ray-Ban Round Metal G-15 Green Lens Sunglasses",
        ]
    },
    {
        "name": "Oakley",
        "type": "brand",
        "category": "Apparel, Footwear & Accessories",
        "aliases": ["oakley", "oakley sunglasses", "oakley holbrook"],
        "products": [
            "Oakley Holbrook Square Sunglasses Matte Black Prizm",
            "Oakley Gascan Rectangular Sunglasses",
            "Oakley Radar EV Path Sport Sunglasses",
            "Oakley Flak 2.0 XL Sunglasses Prizm Golf",
        ]
    },
    {
        "name": "LensCrafters",
        "type": "brand",
        "category": "Retail & Local Services",
        "aliases": ["lenscrafters", "lens crafters", "lenscrafters glasses"],
        "products": [
            "LensCrafters Comprehensive Eye Exam & Prescription Fitting",
            "LensCrafters Digital Progressive Lenses with Anti-Reflective Coating",
        ]
    },
    {
        "name": "Pearle Vision",
        "type": "brand",
        "category": "Retail & Local Services",
        "aliases": ["pearle vision", "pearl vision", "pearle vision optical"],
        "products": [
            "Pearle Vision Annual Eye Exam & Contact Lens Fitting",
            "Pearle Vision Single Vision Prescription Eyeglasses",
        ]
    },

    {
        "name": "Subway",
        "type": "brand",
        "category": "Fast Food & Dining Chains",
        "aliases": ["subway", "subway sandwich", "subway footlong"],
        "products": [
            "Subway The Monster Footlong Sub",
            "Subway Italian B.M.T. Sub",
            "Subway Oven Roasted Turkey Footlong Sandwich",
        ]
    },
    {
        "name": "Dunkin'",
        "type": "brand",
        "category": "Fast Food & Dining Chains",
        "aliases": ["dunkin", "dunkin donuts", "dunkin iced coffee"],
        "products": [
            "Dunkin' Original Blend Iced Coffee Medium",
            "Dunkin' Boston Kreme Glazed Donut",
            "Dunkin' Bacon Egg & Cheese Croissant Sandwich",
            "Dunkin' Bagel Bites Stuffed with Cream Cheese",
        ]
    },
    {
        "name": "Arby's",
        "type": "brand",
        "category": "Fast Food & Dining Chains",
        "aliases": ["arbys", "arby's", "arbys roast beef"],
        "products": [
            "Arby's Classic Roast Beef Sandwich",
            "Arby's Curly Fries Large",
            "Arby's Beef 'n Cheddar Classic",
        ]
    },
    {
        "name": "Jimmy John's",
        "type": "brand",
        "category": "Fast Food & Dining Chains",
        "aliases": ["jimmy johns", "jimmy john's", "jimmy johns gourmet subs"],
        "products": [
            "Jimmy John's #4 Turkey Tom Sub on French Bread",
            "Jimmy John's #9 Italian Night Club Sub",
            "Jimmy John's Vito Gourmet Sandwich",
        ]
    },
    {
        "name": "Buffalo Wild Wings",
        "type": "brand",
        "category": "Fast Food & Dining Chains",
        "aliases": ["bww", "buffalo wild wings", "bdubs"],
        "products": [
            "Buffalo Wild Wings Traditional Wings with Medium Sauce",
            "Buffalo Wild Wings Boneless Wings Honey BBQ",
            "Buffalo Wild Wings Loaded Nachos Platter",
        ]
    },
    {
        "name": "Tim Hortons",
        "type": "brand",
        "category": "Fast Food & Dining Chains",
        "aliases": ["tim hortons", "tims", "tim hortons double double"],
        "products": [
            "Tim Hortons Original Blend Coffee Double Double",
            "Tim Hortons Timbits Assorted Glazed Donut Holes",
            "Tim Hortons Farmer's Breakfast Wrap with Sausage",
        ]
    },
]


def expand_conglomerate_catalogs() -> List[Dict[str, Any]]:
    """Build a structured catalog of brand and product names (over 1,000 distinct items)."""
    feed: List[Dict[str, Any]] = []
    seen_names = set()

    def add_entry(
        name: str,
        item_type: str,
        category: str,
        aliases: List[str],
    ):
        clean_name = name.strip()
        if clean_name.lower() in seen_names:
            return
        seen_names.add(clean_name.lower())

        entry = {
            "id": slugify(clean_name),
            "name": clean_name,
            "item_type": item_type,
            "category": category,
            # Ownership fields are withheld until each claim has a cited source.
            "parent_company": None,
            "ultimate_parent": None,
            "ownership_type": None,
            "ticker_or_jurisdiction": None,
            "ownership_status": WITHHELD_TEXT,
            "ethical_swap_recommendation": WITHHELD_TEXT,
            "search_aliases": [a.lower() for a in aliases] if aliases else [clean_name.lower()],
        }
        feed.append(entry)

    # 1. Add Handcrafted Core Brand Entries and their specific product lines
    for item in CORE_BRAND_ENTRIES:
        add_entry(
            name=item["name"],
            item_type="brand",
            category=item["category"],
            aliases=item.get("aliases", []),
        )
        for prod in item.get("products", []):
            add_entry(
                name=prod,
                item_type="product",
                category=item["category"],
                aliases=[prod.lower(), item["name"].lower()],
            )

    # 2. Brands and products by category
    # We populate real-world, iconic products across major categories
    CONGLOMERATE_POPULATIONS = [
        {
            "category": "Food & Beverage",
            "brands": [
                ("Coca-Cola Classic", ["Coca-Cola 12oz Can 12-Pack", "Coca-Cola 2-Liter Bottle", "Mexican Coke Glass Bottle with Cane Sugar"]),
                ("Diet Coke", ["Diet Coke 12oz Cans 12-Pack", "Diet Coke 20oz Bottle", "Diet Coke Caffeine Free 12-Pack"]),
                ("Coca-Cola Zero Sugar", ["Coca-Cola Zero Sugar 12oz Cans", "Coca-Cola Zero Sugar Cherry 12-Pack"]),
                ("Sprite", ["Sprite Lemon-Lime Soda 12oz Cans", "Sprite Zero Sugar 2-Liter Bottle", "Sprite Cherry 20oz Bottle"]),
                ("Fanta", ["Fanta Orange Soda 12oz Cans", "Fanta Grape Soda 20oz", "Fanta Strawberry Soda 12-Pack"]),
                ("Dasani", ["Dasani Purified Bottled Water 24-Pack", "Dasani Water 1-Liter Sport Cap Bottle"]),
                ("Smartwater", ["Smartwater Vapor Distilled Water 1-Liter", "Smartwater Alkaline with Antioxidants 700ml"]),
                ("Vitaminwater", ["Vitaminwater XXX Acai Blueberry Pomegranate", "Vitaminwater Zero Squeezed Lemonade"]),
                ("Minute Maid", ["Minute Maid 100% Original Orange Juice Pulp Free", "Minute Maid Lemonade 59oz Carton", "Minute Maid Fruit Punch Juice Box 10-Pack"]),
                ("Simply Orange", ["Simply Orange Pulp Free Juice 52oz Carafe", "Simply Lemonade All Natural Carafe", "Simply Apple 100% Pure Pressed Apple Juice"]),
                ("Fairlife Milk", ["Fairlife Ultra-Filtered Whole Milk 52oz", "Fairlife Core Power High Protein Milk Shake Chocolate 26g", "Fairlife Nutrition Plan Chocolate Shake 30g"]),
                ("Honest Tea", ["Honest Organic Half Tea & Half Lemonade", "Honest Kids Organic Appley Ever After Juice Drink"]),
                ("Topo Chico", ["Topo Chico Mineral Water 12oz Glass Bottle 4-Pack", "Topo Chico Sabores Lime with Mint"]),
                ("BodyArmor SuperDrink", ["BodyArmor Sports Drink Fruit Punch 16oz", "BodyArmor Lyte Low Calorie Peach Mango", "BodyArmor Flash I.V. Hydration"]),
                ("Powerade", ["Powerade Mountain Berry Blast Sports Drink 28oz", "Powerade Fruit Punch 8-Pack Cans"]),
                ("Gold Peak Tea", ["Gold Peak Unsweetened Black Iced Tea 52oz", "Gold Peak Sweet Lemon Iced Tea Bottle"]),
                ("Peace Tea", ["Peace Tea Razzleberry Raspberry Tea 23oz Tall Can", "Peace Tea Green Tea Caddy Shack"]),
                ("Fresca", ["Fresca Sparkling Soda Water Original Grapefruit Citrus", "Fresca Mixed Tequila Paloma Cans"]),
                ("Barq's", ["Barq's Root Beer 12oz Cans 12-Pack", "Barq's French Vanilla Cream Soda"]),
                ("Seagram's Ginger Ale", ["Seagram's Extra Crisp Ginger Ale 12-Pack Cans"]),
                ("Costa Coffee", ["Costa Coffee Signature Blend Medium Roast RTD Can"]),
                ("AHA Sparkling Water", ["AHA Sparkling Water Blueberry Pomegranate 8-Pack", "AHA Lime + Watermelon"]),
            ],
        },

        {
            "category": "Food & Beverage",
            "brands": [
                ("Lay's", ["Lay's Classic Potato Chips Party Size Bag", "Lay's Barbecue Flavored Potato Chips", "Lay's Sour Cream & Onion Chips", "Lay's Wavy Original Potato Chips", "Lay's Kettle Cooked Sea Salt Chips"]),
                ("Doritos", ["Doritos Nacho Cheese Tortilla Chips Party Size", "Doritos Cool Ranch Flavored Tortilla Chips", "Doritos Spicy Sweet Chili Vegan Chips", "Doritos Dinamita Chile Limon Rolled Tortilla Chips"]),
                ("Cheetos", ["Cheetos Crunchy Cheese Flavored Snacks", "Cheetos Flamin' Hot Crunchy Cheese Snacks", "Cheetos Puffs Cheese Flavored Snacks", "Cheetos Simply Organic White Cheddar Puffs"]),
                ("Tostitos", ["Tostitos Scoops Tortilla Chips", "Tostitos Crispy Rounds Tortilla Chips", "Tostitos Medium Chunky Salsa Jar", "Tostitos Salsa con Queso Dip"]),
                ("Fritos", ["Fritos Original Corn Chips 9.25oz Bag", "Fritos Chili Cheese Flavored Corn Chips", "Fritos Scoops Corn Chips Bag"]),
                ("Ruffles", ["Ruffles Cheddar & Sour Cream Ridged Potato Chips", "Ruffles Original Salted Potato Chips Party Size", "Ruffles Flamin' Hot Potato Chips"]),
                ("SunChips", ["SunChips Original Multigrain Snacks", "SunChips Harvest Cheddar Multigrain Snacks", "SunChips Garden Salsa Flavored Snacks"]),
                ("Smartfood", ["Smartfood White Cheddar Popcorn Party Size", "Smartfood Movie Theater Butter Flavored Popcorn"]),
                ("Stacy's Pita Chips", ["Stacy's Simply Naked Pita Chips Bag", "Stacy's Parmesan Garlic & Herb Pita Chips", "Stacy's Cinnamon Sugar Pita Chips"]),
                ("PopCorners", ["PopCorners White Cheddar Popped Corn Snacks", "PopCorners Sweet & Salty Kettle Corn", "PopCorners Sea Salt Popped Corn Chips"]),
                ("Quaker Oats", ["Quaker Old Fashioned Rolled Oats 42oz Canister", "Quaker Quick 1-Minute Oats Tub", "Quaker Instant Oatmeal Apples & Cinnamon 10-Count", "Quaker Chewy Chocolate Chip Granola Bars"]),
                ("Cap'n Crunch", ["Cap'n Crunch Crunch Berries Cereal", "Cap'n Crunch Original Sweet Corn & Oat Cereal", "Cap'n Crunch Peanut Butter Crunch Cereal"]),
                ("Life Cereal", ["Life Cinnamon Multi-Grain Cereal", "Life Original Multi-Grain Cereal Box"]),
                ("Pearl Milling Company", ["Pearl Milling Company Original Pancake & Waffle Mix", "Pearl Milling Original Pancake Syrup"]),
                ("Rice-A-Roni", ["Rice-A-Roni Chicken Flavor Rice & Pasta Mix", "Rice-A-Roni Beef Flavor Box", "Pasta Roni White Cheddar & Shells"]),
                ("Sabra Hummus", ["Sabra Classic Hummus Tub 10oz", "Sabra Roasted Red Pepper Hummus", "Sabra Roasted Pine Nut Hummus"]),
                ("Bare Snacks", ["Bare Baked Crunchy Apple Chips Fuji & Reds", "Bare Baked Cinnamon Apple Chips", "Bare Baked Banana Chips"]),
                ("KeVita Kombucha", ["KeVita Master Brew Kombucha Tart Cherry 15.2oz", "KeVita Sparkling Probiotic Drink Lemon Ginger"]),
                ("Gatorade", ["Gatorade Thirst Quencher Fruit Punch 32oz Bottle", "Gatorade Cool Blue Thirst Quencher 8-Pack", "Gatorade Lemon-Lime Sports Drink 20oz", "Gatorade Zero Sugar Glacier Freeze 8-Pack"]),
                ("Propel Water", ["Propel Zero Calorie Water Kiwi Strawberry with Electrolytes", "Propel Immune Support Lemon Blackberry"]),
                ("Muscle Milk", ["Muscle Milk Genuine Chocolate Protein Shake 14oz Bottle", "Muscle Milk Pro Series Intense Vanilla 40g"]),
                ("Tropicana", ["Tropicana Pure Premium Original No Pulp Orange Juice 52oz", "Tropicana Grovestand Lots of Pulp Orange Juice", "Tropicana Homestyle Some Pulp Orange Juice"]),
                ("Naked Juice", ["Naked Juice Green Machine Smoothie 15.2oz", "Naked Juice Mighty Mango Fruit Smoothie", "Naked Juice Blue Machine Antioxidant Smoothie"]),
                ("Izze", ["Izze Sparkling Juice Clementine 4-Pack Cans", "Izze Sparkling Apple Beverage 12oz Cans", "Izze Sparkling Blackberry"]),
                ("Pepsi-Cola", ["Pepsi Original Soda 12oz Cans 12-Pack", "Diet Pepsi 2-Liter Bottle", "Pepsi Zero Sugar Wild Cherry 12-Pack", "Pepsi Real Sugar Glass Bottles"]),
                ("Mountain Dew", ["Mountain Dew Original Citrus Soda 12oz Cans 12-Pack", "Mountain Dew Baja Blast 12-Pack Cans", "Diet Mountain Dew 2-Liter Bottle", "Mountain Dew Code Red Cherry Soda"]),
                ("Starry", ["Starry Lemon Lime Soda 12oz Cans 12-Pack", "Starry Zero Sugar Lemon Lime 2-Liter"]),
                ("Aquafina", ["Aquafina Purified Drinking Water 24-Pack Bottles", "Aquafina Bottled Water 1-Liter"]),
                ("Bubly", ["Bubly Sparkling Water Limebubly 8-Pack Cans", "Bubly Grapefruitbubly Sparkling Water", "Bubly Cherrybubly Sparkling Water 8-Pack"]),
                ("Pure Leaf", ["Pure Leaf Unsweetened Black Iced Tea 18.5oz Bottle", "Pure Leaf Sweet Tea Real Brewed 6-Pack", "Pure Leaf Extra Sweet Tea"]),
            ],
        },

        {
            "category": "Food & Beverage",
            "brands": [
                ("San Pellegrino", ["San Pellegrino Sparkling Natural Mineral Water 1-Liter Glass Bottle", "San Pellegrino Essenza Dark Morello Cherry & Pomegranate", "San Pellegrino Aranciata Orange Italian Soda Cans"]),
                ("Perrier", ["Perrier Carbonated Mineral Water 16.9oz Plastic Bottles 6-Pack", "Perrier Lime Flavored Sparkling Water Cans"]),
                ("Acqua Panna", ["Acqua Panna Natural Spring Water 1-Liter Plastic Bottle"]),
                ("Poland Spring", ["Poland Spring 100% Natural Spring Water 24-Pack Bottles", "Poland Spring Distilled Water 1-Gallon Jug"]),
                ("Gerber", ["Gerber 2nd Foods Sweet Potato Baby Food Tub 2-Pack", "Gerber Graduates Puffs Banana Cereal Snack", "Gerber Organic 1st Foods Prune Puree", "Gerber Good Start Gentle Pro Infant Formula"]),
                ("Toll House", ["Nestlé Toll House Semi-Sweet Chocolate Morsels 12oz Bag", "Nestlé Toll House Refrigerated Chocolate Chip Cookie Dough Tub", "Nestlé Toll House Milk Chocolate Morsels"]),
                ("KitKat (US: Hershey license / Global: Nestlé)", ["KitKat Crisp Wafers in Milk Chocolate Candy Bar", "KitKat King Size 4-Finger Chocolate Bar", "KitKat Dark Chocolate Wafer Bar"]),
                ("Nesquik", ["Nesquik Chocolate Flavored Powder Drink Mix Tub", "Nesquik Ready to Drink Lowfat Chocolate Milk Bottle 14oz", "Nesquik Strawberry Powder Mix"]),
                ("Nescafé", ["Nescafé Clásico Instant Dark Roast Coffee Jar", "Nescafé Taster's Choice House Blend Instant Coffee", "Nescafé Dolce Gusto Espresso Capsules"]),
                ("Nespresso", ["Nespresso Vertuo Line Stormio Dark Roast Coffee Pods", "Nespresso Original Line Ispirazione Ristretto Pods", "Nespresso Vertuo Double Espresso Scuro Capsules"]),
                ("Coffee-mate", ["Coffee-mate French Vanilla Liquid Coffee Creamer 32oz", "Coffee-mate Original Powdered Coffee Creamer Tub", "Coffee-mate Hazelnut Liquid Creamer 64oz", "Coffee-mate Natural Bliss Sweet Cream Creamer"]),
                ("Stouffer's", ["Stouffer's Lasagna with Meat & Sauce Family Size Frozen Entree", "Stouffer's Macaroni & Cheese Frozen Dinner 12oz", "Stouffer's French Bread Pepperoni Pizza 2-Pack", "Stouffer's Stuffed Green Peppers Frozen Meal"]),
                ("Lean Cuisine", ["Lean Cuisine Features Glazed Chicken Frozen Meal", "Lean Cuisine Favorites Four Cheese Pizza", "Lean Cuisine Vermont White Cheddar Macaroni & Beef"]),
                ("Hot Pockets", ["Hot Pockets Pepperoni Pizza Garlic Buttery Crust 2-Pack", "Hot Pockets Ham & Cheddar Crispy Crust Sandwiches", "Hot Pockets Philly Steak & Cheese 5-Pack"]),
                ("DiGiorno", ["DiGiorno Rising Crust Pepperoni Frozen Pizza", "DiGiorno Four Cheese Self-Rising Crust Pizza", "DiGiorno Stuffed Crust Five Cheese Pizza"]),
                ("Tombstone", ["Tombstone Original Pepperoni Frozen Pizza", "Tombstone Five Cheese Frozen Pizza"]),
                ("Sweet Earth", ["Sweet Earth Awesome Burger Plant-Based Patties", "Sweet Earth Traditional Seitan Strips", "Sweet Earth General Tso's Tofu Frozen Bowl"]),
                ("Chameleon Cold-Brew", ["Chameleon Organic Cold-Brew Coffee Concentrate Original", "Chameleon Organic Whole Bean Coffee Dark Roast"]),
                ("Blue Bottle Coffee", ["Blue Bottle Bella Donovan Whole Bean Craft Coffee", "Blue Bottle Giant Steps Blend Coffee Bag", "Blue Bottle Bright Cold Brew Can 8oz"]),
                ("Vital Proteins", ["Vital Proteins Collagen Peptides Unflavored Powder 20oz Tub", "Vital Proteins Marine Collagen Powder Tub", "Vital Proteins Beauty Collagen Strawberry Lemon"]),
                ("Orgain", ["Orgain Organic Plant Based Protein Powder Creamy Chocolate Fudge", "Orgain Organic Nutritional Shake Vanilla 4-Pack", "Orgain Grass Fed Whey Protein Powder Clean Vanilla"]),
                ("Purina Pro Plan", ["Purina Pro Plan Adult Complete Essentials Shredded Blend Chicken & Rice Dog Food", "Purina Pro Plan Veterinary Diets FortiFlora Probiotic Supplement", "Purina Pro Plan Focus Sensitive Skin & Stomach Salmon Dog Food"]),
                ("Purina ONE", ["Purina ONE SmartBlend True Instinct Real Turkey & Venison Dry Dog Food", "Purina ONE Tender Selects Blend Real Salmon Cat Food"]),
                ("Fancy Feast", ["Fancy Feast Grilled Seafood Feast in Gravy Wet Cat Food Can", "Fancy Feast Medleys White Meat Chicken Tuscany Cat Food", "Fancy Feast Classic Pate Salmon Feast"]),
                ("Friskies", ["Friskies Shreds with Chicken in Gravy Wet Cat Food Cans", "Friskies Surfin' & Turfin' Favorites Dry Cat Food Bag"]),
                ("Tidy Cats", ["Tidy Cats 24/7 Performance Multi-Cat Clumping Clay Cat Litter", "Tidy Cats Breeze Cat Litter Pellets Refill Pack"]),
                ("Merrick Pet Care", ["Merrick Grain Free Real Texas Beef & Sweet Potato Dry Dog Food", "Merrick Classic Healthy Grains Adult Chicken Dry Dog Food"]),
            ],
        },

        {
            "category": "Food & Beverage",
            "brands": [
                ("Kraft Mac & Cheese", ["Kraft Original Macaroni & Cheese 7.25oz Box", "Kraft Easy Mac Macaroni & Cheese Cups 4-Pack", "Kraft Deluxe Original Cheddar Macaroni & Cheese Dinner", "Kraft Thick 'n Creamy Macaroni & Cheese"]),
                ("Heinz Ketchup", ["Heinz Tomato Ketchup 32oz Squeeze Bottle", "Heinz Simply Tomato Ketchup with No Artificial Sweeteners", "Heinz Organic Yellow Mustard Squeeze Bottle", "Heinz 57 Steak Sauce Bottle"]),
                ("Philadelphia Cream Cheese", ["Philadelphia Original Cream Cheese 8oz Brick", "Philadelphia Original Cream Cheese Spread Tub 12oz", "Philadelphia Whipped Original Cream Cheese Tub", "Philadelphia 1/3 Less Fat Neufchatel Cheese"]),
                ("Velveeta", ["Velveeta Original Melting Cheese Loaf 32oz", "Velveeta Shells & Cheese Original Dinner Box", "Velveeta Cheesy Skillets Ultimate Cheeseburger Mac"]),
                ("Cheez Whiz", ["Cheez Whiz Original Cheese Dip 15oz Glass Jar"]),
                ("Oscar Mayer", ["Oscar Mayer Classic Uncured Wieners Hot Dogs 16oz", "Oscar Mayer Naturally Hardwood Smoked Bacon 16oz", "Oscar Mayer Deli Fresh Smoked Turkey Breast 9oz", "Oscar Mayer Real Bacon Bits 2.8oz"]),
                ("Lunchables", ["Lunchables Turkey & American Cracker Stackers with Capri Sun", "Lunchables Extra Cheese Pizza with Treat", "Lunchables Ham & Cheddar Cracker Stackers Snack Kit"]),
                ("Ore-Ida", ["Ore-Ida Golden Crinkles French Fried Potatoes 32oz Frozen Bag", "Ore-Ida Tater Tots Frozen Seasoned Potatoes", "Ore-Ida Extra Crispy Fast Food Fries"]),
                ("Classico", ["Classico Four Cheese Pasta Sauce 24oz Jar", "Classico Traditional Sweet Basil Marinara Sauce", "Classico Creamy Alfredo Pasta Sauce"]),
                ("Maxwell House", ["Maxwell House House Blend Medium Roast Ground Coffee 30.6oz Tub", "Maxwell House Original Roast Ground Coffee Can", "Maxwell House International French Vanilla Cafe Powder"]),
                ("Gevalia Kaffe", ["Gevalia Kaffe Traditional Mild Roast Ground Coffee 12oz", "Gevalia House Blend K-Cup Coffee Pods 32-Count"]),
                ("Capri Sun", ["Capri Sun Pacific Cooler Ready-to-Drink Juice Pouches 10-Pack", "Capri Sun Fruit Punch Juice Drinks 10-Pack", "Capri Sun Strawberry Kiwi Drink Pouches 10-Count"]),
                ("Kool-Aid", ["Kool-Aid Jammers Tropical Punch Drink Pouches 10-Pack", "Kool-Aid Unsweetened Cherry Powder Drink Mix Packet", "Kool-Aid Bursts Berry Blue Ready-to-Drink Bottles"]),
                ("Jell-O", ["Jell-O Strawberry Gelatin Dessert Mix 3oz Box", "Jell-O Cook & Serve Chocolate Pudding Mix", "Jell-O Ready-to-Eat Chocolate Vanilla Swirl Pudding Cups 4-Pack"]),
                ("Grey Poupon", ["Grey Poupon Dijon Mustard 8oz Glass Jar", "Grey Poupon Country Style Stone Ground Mustard"]),
                ("Bagel Bites", ["Bagel Bites Pizza Snacks Sausage & Pepperoni 9-Count Frozen Box", "Bagel Bites Cheese & Pepperoni Mini Bagels 18-Count"]),
                ("Cracker Barrel Cheese", ["Cracker Barrel Extra Sharp Yellow Cheddar Cheese Block 8oz", "Cracker Barrel Rich White Cheddar Cheese Slices"]),
                ("Miracle Whip", ["Miracle Whip Original Dressing Squeeze Bottle 30oz", "Miracle Whip Light Dressing Tub"]),
                ("A.1. Steak Sauce", ["A.1. Original Steak Sauce 10oz Glass Bottle", "A.1. Thick & Hearty Bold Steak Sauce"]),
                ("Shake 'n Bake", ["Shake 'n Bake Original Chicken Seasoned Coating Mix Box", "Shake 'n Bake Extra Crispy Seasoned Bread Crumbs"]),
            ],
        },

        {
            "category": "Food & Beverage",
            "brands": [
                ("Healthy Choice", ["Healthy Choice Simply Steamers Grilled Chicken & Broccoli Alfredo", "Healthy Choice Cafe Steamers Beef Merlot Frozen Meal", "Healthy Choice Power Bowls Korean Inspired Beef"]),
                ("Marie Callender's", ["Marie Callender's Chicken Pot Pie Frozen Entree 16oz", "Marie Callender's Dutch Apple Pie Frozen Dessert", "Marie Callender's Beef Pot Pie Frozen Meal"]),
                ("Banquet", ["Banquet Salisbury Steak Frozen Meal 11.88oz", "Banquet Original Crispy Fried Chicken Assorted Pieces Frozen Box", "Banquet Mega Bowls Nashville Hot Fried Chicken"]),
                ("Birds Eye", ["Birds Eye Steamfresh Sweet Corn 10oz Frozen Veggies", "Birds Eye Voila! Garlic Chicken Frozen Skillet Meal", "Birds Eye Steamfresh Cut Green Beans"]),
                ("Gardein", ["Gardein Ultimate Plant-Based Burger Patties Frozen Pack", "Gardein Seven Grain Crispy Tenders Vegan Chicken", "Gardein Meatless Meatballs Frozen Bag"]),
                ("Earth Balance", ["Earth Balance Original Natural Buttery Spread Tub 15oz", "Earth Balance Soy Free Buttery Spread", "Earth Balance Vegan Cheddar Flavor Squares"]),
                ("Glutino", ["Glutino Gluten Free Pretzel Twists 14.1oz Bag", "Glutino Gluten Free Chocolate Vanilla Creme Cookies"]),
                ("Udi's Gluten Free", ["Udi's Gluten Free Delicious Multigrain Sandwich Bread Frozen Loaf", "Udi's Gluten Free Plain Bagels 4-Count"]),
                ("Duncan Hines", ["Duncan Hines Signature Red Velvet Cake Mix Box", "Duncan Hines Dolly Parton's Southern Style Coconut Cake Mix", "Duncan Hines Creamy Cream Cheese Frosting Tub"]),
                ("Hunt's", ["Hunt's 100% Natural Diced Tomatoes 14.5oz Can", "Hunt's Traditional Pasta Sauce 24oz Can", "Hunt's Tomato Paste 6oz Can"]),
                ("Rotel", ["Rotel Original Diced Tomatoes & Green Chilies 10oz Can", "Rotel Mild Diced Tomatoes with Green Chilies Can"]),
                ("Chef Boyardee", ["Chef Boyardee Beef Ravioli in Tomato Sauce 15oz Can", "Chef Boyardee Beefaroni Pasta in Tomato Meat Sauce Can", "Chef Boyardee Spaghetti & Meatballs"]),
                ("Hebrew National", ["Hebrew National All Beef Franks Hot Dogs 12oz Pack", "Hebrew National Kosher Beef Salami"]),
                ("Slim Jim", ["Slim Jim Original Giant Smoked Meat Snack Stick 0.97oz", "Slim Jim Monster Size Mild Beef Stick", "Slim Jim Mild Snack Sticks 14-Count Box"]),
                ("Duke's Smoked Meats", ["Duke's Original Recipe Smoked Shorty Sausages 5oz Bag", "Duke's Hot & Spicy Shorty Smoked Sausages"]),
                ("Reddi-wip", ["Reddi-wip Real Whipped Dairy Cream Aerosol Can 13oz", "Reddi-wip Non-Dairy Coconut Milk Whipped Topping Can"]),
                ("PAM", ["PAM Original No-Stick Canola Oil Cooking Spray 6oz Can", "PAM Butter Flavor Cooking Spray"]),
                ("Angie's BOOMCHICKAPOP", ["Angie's BOOMCHICKAPOP Sweet & Salty Kettle Corn Bag", "Angie's BOOMCHICKAPOP Sea Salt Popcorn Bag"]),
                ("Orville Redenbacher's", ["Orville Redenbacher's Movie Theater Butter Microwave Popcorn 6-Pack", "Orville Redenbacher's Gourmet Popping Corn Kernels Jar"]),
                ("Swiss Miss", ["Swiss Miss Milk Chocolate Hot Cocoa Mix with Marshmallows 8-Count", "Swiss Miss Indulgent Collection Dark Chocolate Hot Cocoa"]),
                ("Snack Pack", ["Snack Pack Chocolate Pudding Cups 4-Pack", "Snack Pack Vanilla Pudding Cups 4-Count", "Snack Pack Lemon Juicy Gels"]),
                ("Wish-Bone", ["Wish-Bone Italian Salad Dressing Bottle 15oz", "Wish-Bone Robusto Italian Dressing", "Wish-Bone House Creamy Italian Dressing"]),
            ],
        },

        {
            "category": "Household & Cleaning",
            "brands": [
                ("Tide", ["Tide PODS Free & Gentle Liquid Laundry Detergent Pacs 42-Count", "Tide Original Liquid Laundry Detergent 92oz Bottle", "Tide with OXI Liquid Detergent 64 Loads", "Tide To Go Instant Stain Remover Pen 3-Pack"]),
                ("Gain", ["Gain Original Flings Laundry Detergent Pacs 60-Count", "Gain Original Aroma Booster Liquid Laundry Detergent", "Gain Fireworks In-Wash Scent Booster Beads Tub"]),
                ("Downy", ["Downy April Fresh Liquid Fabric Softener 103oz Bottle", "Downy Unstopables In-Wash Scent Booster Lush Scent Beads"]),
                ("Bounce", ["Bounce Outdoor Fresh Fabric Softener Dryer Sheets 240-Count Box", "Bounce Free & Gentle Hypoallergenic Dryer Sheets"]),
                ("Dawn", ["Dawn Ultra Platinum Dishwashing Liquid Dish Soap 38oz", "Dawn Powerwash Dish Spray Fresh Scent Starter Kit", "Dawn Free & Clear Liquid Dish Soap"]),
                ("Cascade", ["Cascade Platinum Plus ActionPacs Dishwasher Detergent 52-Count", "Cascade Complete Gel Dishwasher Detergent 75oz", "Cascade Original Dishwasher Pods"]),
                ("Swiffer", ["Swiffer Sweeper 2-in-1 Dry and Wet Floor Sweeper Starter Kit", "Swiffer WetJet Hardwood Floor Spray Mop Kit", "Swiffer Duster Heavy Duty Refills 10-Pack"]),
                ("Febreze", ["Febreze Air Effects Air Freshener Spray Linen & Sky 2-Pack", "Febreze Fabric Extra Strength Odor Refresher Spray 27oz"]),
                ("Bounty", ["Bounty Select-a-Size Paper Towels 12 Double Rolls", "Bounty Quick Size Paper Towels 8 Family Rolls"]),
                ("Charmin", ["Charmin Ultra Soft Toilet Paper 18 Mega Rolls", "Charmin Ultra Strong Clean Touch Bath Tissue 24 Rolls"]),
                ("Pampers", ["Pampers Swaddlers Disposable Diapers Size 1 148-Count", "Pampers Baby Dry Diapers Size 4", "Pampers Aqua Pure 99% Water Sensitive Baby Wipes 6-Pack"]),
                ("Luvs", ["Luvs Pro Level Leak Protection Diapers Size 3 Box 168-Count"]),
                ("Crest", ["Crest 3D White Advanced Radiant Mint Toothpaste 3-Pack", "Crest Pro-Health Clean Mint Antibacterial Toothpaste", "Crest 3D Whitestrips Professional Effects Teeth Whitening Kit"]),
                ("Oral-B", ["Oral-B Pro 1000 CrossAction Electric Rechargeable Toothbrush", "Oral-B Glide Pro-Health Deep Clean Dental Floss 2-Pack", "Oral-B Indicator Color Changing Manual Toothbrush 4-Pack"]),
                ("Scope", ["Scope Classic Original Mint Mouthwash 1-Liter Bottle", "Scope Outlast Long Lasting Peppermint Mouthwash"]),
                ("Gillette", ["Gillette Fusion5 Men's Razor Handle with 4 Blade Refills", "Gillette Mach3 Men's Razor Cartridges 10-Pack", "Gillette Foamy Regular Shave Cream 11oz Can"]),
                ("Venus", ["Gillette Venus Extra Smooth Women's Razor Handle plus 2 Refills", "Gillette Venus ComfortGlide White Tea Women's Razor"]),
                ("Braun", ["Braun Series 7 Electric Shaver with Clean & Charge Station", "Braun ThermoScan 7 Ear Thermometer with Age Precision"]),
                ("Head & Shoulders", ["Head & Shoulders Classic Clean Anti-Dandruff 2-in-1 Shampoo 32oz", "Head & Shoulders Dry Scalp Care Almond Oil Shampoo"]),
                ("Pantene", ["Pantene Pro-V Daily Moisture Renewal Shampoo 30.4oz", "Pantene Miracle Moisture 10-in-1 Leave-In Conditioner Spray", "Pantene Pro-V Repair & Protect Conditioner"]),
                ("Herbal Essences", ["Herbal Essences bio:renew Argan Oil of Morocco Shampoo 13.5oz", "Herbal Essences Chamomile Shine Shampoo Bottle"]),
                ("Olay", ["Olay Regenerist Micro-Sculpting Cream Face Moisturizer 1.7oz", "Olay Super Serum 5-in-1 Face Treatment 1oz", "Olay Cleansing & Nourishing B3 Body Wash 20oz"]),
                ("Old Spice", ["Old Spice High Endurance Pure Sport Men's Deodorant 3oz", "Old Spice Classic Cologne Deodorant Stick 3-Pack", "Old Spice Swagger Cedarwood Scent Body Wash 24oz"]),
                ("Secret", ["Secret Outlast Completely Clean Invisible Solid Antiperspirant 2.6oz", "Secret Aluminum Free Lavender Women's Deodorant"]),
            ],
        },

        {
            "category": "Personal Care & Cosmetics",
            "brands": [
                ("CeraVe", ["CeraVe Daily Moisturizing Lotion with Ceramides & Hyaluronic Acid 19oz", "CeraVe Hydrating Facial Cleanser for Normal to Dry Skin 16oz", "CeraVe Foaming Facial Cleanser 16oz Pump Bottle", "CeraVe Healing Ointment with Petrolatum & Ceramides 12oz Tub", "CeraVe Eye Repair Cream for Dark Circles & Puffiness"]),
                ("La Roche-Posay", ["La Roche-Posay Anthelios Ultra-Light Fluid Sunscreen SPF 60 1.7oz", "La Roche-Posay Toleriane Double Repair Face Moisturizer 2.5oz", "La Roche-Posay Effaclar Duo Dual Action Acne Treatment"]),
                ("SkinCeuticals", ["SkinCeuticals C E Ferulic Vitamin C Serum 1oz Dropper Bottle", "SkinCeuticals Triple Lipid Restore 2:4:2 Anti-Aging Cream"]),
                ("Kiehl's", ["Kiehl's Since 1851 Ultra Facial Cream with Squalane 1.7oz", "Kiehl's Creme de Corps Nourishing Body Lotion 16.9oz", "Kiehl's Midnight Recovery Concentrate Botanical Facial Oil"]),
                ("Youth to the People", ["Youth to the People Superfood Antioxidant Cleanser Kale & Green Tea 8oz", "Youth to the People Superberry Hydrate + Glow Dream Night Cream"]),
                ("Aesop", ["Aesop Resurrection Aromatique Hand Wash 16.9oz Pump Bottle", "Aesop Reverence Aromatique Hand Balm 2.6oz Tube"]),
                ("NYX Professional Makeup", ["NYX Professional Makeup Butter Gloss Non-Sticky Lip Gloss Praline", "NYX Epic Ink Waterproof Matte Liquid Eyeliner Black", "NYX Control Freak Clear Eyebrow Gel"]),
                ("Urban Decay", ["Urban Decay Naked3 Eyeshadow Palette Rose-Hued Neutrals", "Urban Decay All Nighter Long-Lasting Makeup Setting Spray 4oz"]),
                ("Maybelline New York", ["Maybelline Instant Age Rewind Concealer Eraser Neutralizer", "Maybelline Lash Sensational Sky High Washable Mascara Very Black", "Maybelline Fit Me Matte + Poreless Liquid Foundation Glass Bottle", "Maybelline Super Stay Vinyl Ink Longwear Liquid Lipcolor"]),
                ("IT Cosmetics", ["IT Cosmetics CC+ Cream with SPF 50+ Full Coverage Color Correcting Foundation", "IT Cosmetics Confidence in a Cream Hydrating Moisturizer"]),
                ("Lancôme", ["Lancôme Advanced Génifique Youth Activating Face Serum 1.7oz", "Lancôme Monsieur Big Volumizing Mascara 01 Black"]),
                ("Redken", ["Redken All Soft Argan Oil Shampoo for Dry Brittle Hair 33.8oz", "Redken Extreme Length Biotin Conditioner Liter Bottle"]),
                ("Matrix", ["Matrix Total Results Brass Off Blue Toning Shampoo for Brunettes 33.8oz", "Matrix Mega Sleek Shea Butter Conditioner Bottle"]),
                ("Pureology", ["Pureology Hydrate Moisturizing Sulfate-Free Shampoo for Color-Treated Hair", "Pureology Color Fanatic 21 Leave-In Multi-Tasking Spray Treatment"]),
                ("Garnier", ["Garnier SkinActive Micellar Cleansing Water All-in-1 Waterproof 13.5oz", "Garnier Fructis Sleek & Shine Anti-Frizz Moroccan Argan Serum", "Garnier Whole Blends Honey Treasures Restoring Hair Mask Tub"]),
            ],
        },

        {
            "category": "Personal Care & Cosmetics",
            "brands": [
                ("The Ordinary", ["The Ordinary Niacinamide 10% + Zinc 1% High-Strength Serum 1oz", "The Ordinary Hyaluronic Acid 2% + B5 Hydration Support Serum", "The Ordinary AHA 30% + BHA 2% Peeling Solution Exfoliating Facial"]),
                ("Le Labo", ["Le Labo Santal 33 Eau de Parfum 1.7oz Bottle", "Le Labo Thé Noir 29 Eau de Parfum 3.4oz Spray"]),
                ("Jo Malone London", ["Jo Malone London Wood Sage & Sea Salt Cologne 3.4oz", "Jo Malone English Pear & Freesia Home Candle"]),
                ("Clinique", ["Clinique Dramatically Different Moisturizing Lotion+ Pump Bottle 4.2oz", "Clinique Take The Day Off Cleansing Balm Makeup Remover Tub", "Clinique Almost Lipstick in Black Honey Cult Classic"]),
                ("MAC Cosmetics", ["MAC Matte Lipstick in Velvet Teddy Cult Neutral", "MAC Studio Fix Fluid Foundation SPF 15 Matte Finish", "MAC Prep + Prime Fix+ Finishing Mist Spray"]),
                ("Bobbi Brown", ["Bobbi Brown Vitamin Enriched Face Base Primer & Moisturizer Tub 1.7oz", "Bobbi Brown Long-Wear Gel Eyeliner Pot"]),
                ("Origins", ["Origins GinZing Oil-Free Energy-Boosting Gel Face Moisturizer 1.7oz", "Origins Checks and Balances Frothy Face Wash Tube 5oz"]),
                ("Aveda", ["Aveda Botanical Repair Strengthening Shampoo 33.8oz Liter", "Aveda Rosemary Mint Purifying Shampoo Liter Bottle", "Aveda Shampure Nurturing Conditioner"]),
                ("Too Faced", ["Too Faced Better Than Sex Volumizing Waterproof Mascara", "Too Faced Born This Way Super Coverage Multi-Use Concealer"]),
                ("Smashbox", ["Smashbox The Original Photo Finish Smooth & Blur Primer Tube 1oz"]),
                ("Bumble and bumble", ["Bumble and bumble Surf Spray Salt-Infused Styling Texture Spray 4oz", "Bumble and bumble Hairdresser's Invisible Oil Heat Primer"]),
            ],
        },

        {
            "category": "Personal Care & Cosmetics",
            "brands": [
                ("Neutrogena", ["Neutrogena Hydro Boost Water Gel Facial Moisturizer with Hyaluronic Acid", "Neutrogena Ultra Sheer Dry-Touch Sunscreen Lotion SPF 70", "Neutrogena Oil-Free Pink Grapefruit Acne Face Wash", "Neutrogena Makeup Remover Cleansing Towelettes Wipes 25-Pack"]),
                ("Aveeno", ["Aveeno Daily Moisturizing Body Lotion with Soothing Prebiotic Oat 18oz", "Aveeno Skin Relief Fragrance-Free Body Wash 33oz Pump", "Aveeno Baby Daily Moisture Lotion for Delicate Skin"]),
                ("OGX", ["OGX Renewing + Argan Oil of Morocco Penetrating Hair Oil 3.3oz", "OGX Nourishing + Coconut Milk Shampoo Bottle 13oz", "OGX Thick & Full + Biotin & Collagen Conditioner"]),
                ("Maui Moisture", ["Maui Moisture Heal & Hydrate + Shea Butter Hair Mask Tub 12oz", "Maui Moisture Vanilla Bean Conditioner for Frizzy Hair"]),
                ("Clean & Clear", ["Clean & Clear Essentials Foaming Daily Facial Cleanser 8oz", "Clean & Clear Morning Burst Citrus Facial Cleanser with Bursting Beads"]),
                ("Band-Aid", ["Band-Aid Brand Flexible Fabric Adhesive Bandages Assorted Sizes 100-Pack", "Band-Aid Water Block Tough-Strips Waterproof Bandages"]),
                ("Neosporin", ["Neosporin + Pain Relief Dual Action First Aid Antibiotic Ointment Tube", "Neosporin Original Triple Antibiotic First Aid Ointment"]),
                ("Listerine", ["Listerine Cool Mint Antiseptic Mouthwash 1-Liter Bottle", "Listerine Total Care Anticavity Fluoride Mouthwash Fresh Mint"]),
                ("Tylenol", ["Tylenol Extra Strength Acetaminophen 500mg Caplets 100-Count", "Children's Tylenol Oral Suspension Dye-Free Cherry Flavor"]),
                ("Motrin", ["Motrin IB Ibuprofen 200mg Pain Reliever Fever Reducer Caplets 100-Count"]),
                ("Benadryl", ["Benadryl Allergy Ultratabs Antihistamine Allergy Relief Tablets 100-Count"]),
                ("Zyrtec", ["Zyrtec 24 Hour Allergy Relief Cetirizine HCl 10mg Tablets 90-Count"]),
                ("Johnson's Baby", ["Johnson's Baby Shampoo Tear-Free Gentle Formula 27.1oz Bottle", "Johnson's Bedtime Baby Bath Nighttime Relaxing Scent 27.1oz"]),
            ],
        },

        {
            "category": "Home Appliances & Tools",
            "brands": [
                ("KitchenAid", ["KitchenAid Artisan Series 5-Quart Tilt-Head Stand Mixer", "KitchenAid 9-Speed Digital Hand Mixer with Whisk", "KitchenAid K400 Variable Speed Blender with Glass Jar", "KitchenAid 3-Speed Hand Immersion Blender"]),
                ("Maytag", ["Maytag Commercial-Grade Top Load Residential Washing Machine", "Maytag Smart Front Load Electric Dryer with Extra Power", "Maytag Heavy-Duty Stainless Steel Tub Built-In Dishwasher"]),
                ("Whirlpool", ["Whirlpool 36-inch Wide French Door Refrigerator with Ice Maker", "Whirlpool 5.3 Cu. Ft. Electric 5-in-1 Air Fry Range", "Whirlpool Top Load Washer with Removable Agitator"]),
                ("JennAir", ["JennAir Rise 36-Inch Dual-Fuel Professional Style Range", "JennAir Column Built-In Integrated Luxury Refrigerator"]),
                ("Amana", ["Amana 18.2 Cu. Ft. Top-Freezer Refrigerator", "Amana 4.8 Cu. Ft. Traditional Electric Cooktop Range"]),
            ],
        },

        {
            "category": "Home Appliances & Tools",
            "brands": [
                ("Rubbermaid", ["Rubbermaid Brilliance Leak-Proof Food Storage Containers 10-Piece Set", "Rubbermaid Commercial Products Brute 32-Gallon Heavy Duty Trash Can", "Rubbermaid Roughneck Storage Tote Box 18-Gallon"]),
                ("Coleman", ["Coleman Sundome 4-Person Camping Tent", "Coleman 54-Quart Steel-Belted Cooler Stainless Steel", "Coleman Classic 2-Burner Propane Camping Stove"]),
                ("Contigo", ["Contigo Autoseal West Loop Stainless Steel Travel Mug 16oz", "Contigo Jackson Chill 2.0 Vacuum-Insulated Water Bottle"]),
                ("CamelBak", ["CamelBak Eddy+ Water Bottle with Straw 25oz", "CamelBak Classic Light Hydration Pack 70oz Bladder"]),
                ("Oster", ["Oster Classic 700-Watt All-Metal Drive Glass Jar Blender", "Oster Extra Large Digital Air Fry Toaster Oven"]),
                ("Crock-Pot", ["Crock-Pot 7-Quart Oval Manual Slow Cooker Stainless Steel", "Crock-Pot Express 6-Quart Multi-Cooker"]),
                ("Mr. Coffee", ["Mr. Coffee 12-Cup Programmable Drip Coffee Maker", "Mr. Coffee Iced and Hot Single-Serve Coffee Machine"]),
                ("Sharpie", ["Sharpie Fine Point Permanent Markers Black 12-Pack", "Sharpie Ultra Fine Point Colored Permanent Markers 24-Count", "Sharpie S-Gel Medium Point No Smear Gel Pens 12-Pack"]),
                ("Paper Mate", ["Paper Mate Flair Felt Tip Pens Medium Point Assorted Colors 16-Pack", "Paper Mate InkJoy 100RT Retractable Ballpoint Pens"]),
                ("Expo", ["Expo Low Odor Dry Erase Chisel Tip Whiteboard Markers 8-Pack", "Expo Dry Erase Board Cleaner Spray Bottle"]),
                ("Elmer's", ["Elmer's Disappearing Purple School Glue Sticks 12-Count Box", "Elmer's Liquid Washable White School Glue 4oz"]),
                ("Yankee Candle", ["Yankee Candle Large Jar Candle Balsam & Cedar Scent", "Yankee Candle Large Jar Midsummer's Night Scent"]),
            ],
        },

        {
            "category": "Home Appliances & Tools",
            "brands": [
                ("DeWalt", ["DeWalt 20V MAX Cordless Drill and Impact Driver Combo Kit", "DeWalt 20V MAX XR Brushless Cordless Circular Saw", "DeWalt Heavy-Duty Miter Saw 12-Inch Double Bevel", "DeWalt 20V MAX 5.0Ah Lithium Ion Battery 2-Pack"]),
                ("Craftsman", ["Craftsman Mechanics Tool Set 230-Piece Ratchet and Socket Kit", "Craftsman V20 Cordless Weedwacker String Trimmer", "Craftsman 6-Gallon Portable Air Compressor"]),
                ("Stanley", ["Stanley FatMax 25-Foot Tape Measure Classic", "Stanley Classic 99 Retractable Utility Knife with Extra Blades", "Stanley 16-Ounce Fiberglass Hammer"]),
                ("Black+Decker", ["Black+Decker 20V MAX Matrix Cordless Drill Attachment System", "Black+Decker Dustbuster QuickClean Cordless Handheld Vacuum", "Black+Decker 4-Slice Toaster Oven"]),
                ("Irwin Tools", ["Irwin Vise-Grip Original Curved Jaw Locking Pliers 10-Inch", "Irwin Quick-Grip One-Handed Bar Clamps 4-Pack"]),
                ("Lenox", ["Lenox Demolition Reciprocating Saw Blades 5-Pack", "Lenox Bi-Metal Speed Slot Hole Saw"]),
                ("Bostitch", ["Bostitch 18-Gauge Brad Nailer Kit Air Powered", "Bostitch Heavy-Duty 3-in-1 Metal Staple Gun"]),
            ],
        },

        {
            "category": "Apparel, Footwear & Accessories",
            "brands": [
                ("The North Face", ["The North Face Men's McMurdo Down Parka 600-Fill", "The North Face Borealis Everyday Laptop Backpack", "The North Face Women's Osito Full-Zip Fleece Jacket", "The North Face Half Dome Graphic T-Shirt"]),
                ("Vans", ["Vans Old Skool Classic Suede Skate Shoes Black/White", "Vans Classic Slip-On Checkerboard Skate Shoes", "Vans Sk8-Hi High Top Lace-Up Skate Shoes"]),
                ("Timberland", ["Timberland 6-Inch Premium Waterproof Leather Boot Wheat Nubuck", "Timberland PRO Direct Attach Steel Toe Work Boots", "Timberland Men's White Ledge Mid Waterproof Hiking Boots"]),
                ("Supreme", ["Supreme Box Logo Heavyweight Cotton Hoodie", "Supreme Shoulder Bag Cordura Nylon", "Supreme Camp Cap Twill"]),
                ("Dickies", ["Dickies Original 874 Work Pants Classic Fit", "Dickies Short Sleeve Work Shirt Classic Twill", "Dickies Duck Canvas Bib Overalls"]),
                ("Smartwool", ["Smartwool Classic Thermal Merino Wool Base Layer Crew", "Smartwool Hike Full Cushion Crew Socks"]),
                ("Altra Footwear", ["Altra Lone Peak 8 Zero Drop Trail Running Shoes", "Altra Paradigm Road Running Shoes"]),
                ("JanSport", ["JanSport SuperBreak One Classic School Backpack 26L", "JanSport Right Pack Suede Leather Bottom Daypack"]),
            ],
        },

        {
            "category": "Finance, Retail & Staples",
            "brands": [
                ("Geico", ["Geico Auto Insurance Standard Passenger Policy", "Geico Homeowners Insurance Policy"]),
                ("Duracell", ["Duracell Coppertop AA Alkaline Batteries 24-Pack", "Duracell Optimum AAA Long-Lasting Batteries 18-Pack"]),
                ("Dairy Queen", ["Dairy Queen Oreo Blizzard Treat Large", "Dairy Queen Chicken Strip Basket with Country Gravy"]),
                ("Fruit of the Loom", ["Fruit of the Loom Men's Stay-Tucked Crew T-Shirt 6-Pack", "Fruit of the Loom Men's Breathable Boxer Briefs 5-Pack"]),
                ("Benjamin Moore", ["Benjamin Moore Regal Select Interior Paint & Primer Eggshell", "Benjamin Moore Aura Waterborne Interior Paint"]),
                ("Pampered Chef", ["Pampered Chef Classic Stoneware Round Pizza Stone", "Pampered Chef Manual Food Processor Chopper"]),
                ("Brooks Running", ["Brooks Ghost 15 Neutral Road Running Shoes", "Brooks Adrenaline GTS 23 Support Running Shoes"]),
            ],
        },
    ]

    for group in CONGLOMERATE_POPULATIONS:
        category = group["category"]

        for brand_name, product_list in group["brands"]:
            add_entry(
                name=brand_name,
                item_type="brand",
                category=category,
                aliases=[brand_name.lower()],
            )
            for prod in product_list:
                add_entry(
                    name=prod,
                    item_type="product",
                    category=category,
                    aliases=[prod.lower(), brand_name.lower()],
                )

    return feed


def generate_and_export_feed(
    json_path: str = "data/brand_parent_feed.json",
    csv_path: str = "data/brand_parent_feed.csv",
) -> List[Dict[str, Any]]:
    """Builds the brand & product feed and saves both JSON and CSV formats."""
    feed = expand_conglomerate_catalogs()
    print(f"Generated initial catalog with {len(feed)} entries.")

    # No filler: every row must be a real brand or product. (A previous version padded the
    # feed to 1,000 rows with invented SKU variants; that is intentionally gone.)

    # Save to JSON
    json_file = Path(json_path)
    json_file.parent.mkdir(parents=True, exist_ok=True)
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(feed, f, indent=2, ensure_ascii=False)
    print(f"Wrote {len(feed)} entries to {json_file.resolve()}")

    # Save to CSV
    csv_file = Path(csv_path)
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_file, "w", encoding="utf-8", newline="") as f:
        fieldnames = [
            "id",
            "name",
            "item_type",
            "category",
            "parent_company",
            "ultimate_parent",
            "ownership_type",
            "ticker_or_jurisdiction",
            "ownership_status",
            "ethical_swap_recommendation",
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in feed:
            writer.writerow(row)
    print(f"Wrote CSV feed to {csv_file.resolve()}")

    return feed


if __name__ == "__main__":
    generate_and_export_feed()
