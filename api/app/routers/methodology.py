from fastapi import APIRouter
from rubric.engine import load_rubric

router = APIRouter(prefix="/v1/methodology", tags=["Methodology & Firewall"])


@router.get("")
def get_methodology():
    """Returns the active scoring rubric, cited data sources, and strict integrity firewall policy."""
    rubric = load_rubric()
    return {
        "rubric_version": rubric.get("version", "1.0.0"),
        "dimensions": rubric.get("dimensions", {}),
        "data_sources": [
            {
                "name": "SEC EDGAR (10-K, DEF 14A)",
                "type": "Public Filing",
                "metrics": ["CEO-to-median-worker pay ratio", "Stock buybacks", "Dividends", "Subsidiaries"],
                "url": "https://www.sec.gov/edgar",
            },
            {
                "name": "USDA Economic Research Service (ERS)",
                "type": "Federal Agency Data",
                "metrics": ["Food Dollar Series farm share", "Industry marketing bill", "Supply chain margins"],
                "url": "https://www.ers.usda.gov/data-products/food-dollar-series/",
            },
            {
                "name": "OSHA Enforcement Data",
                "type": "Federal Regulatory Records",
                "metrics": ["Workplace safety violations", "Severe injury reports", "Penalties"],
                "url": "https://www.osha.gov/enforcement",
            },
            {
                "name": "EPA Enforcement and Compliance History Online (ECHO)",
                "type": "Federal Environmental Records",
                "metrics": ["Clean Water Act violations", "Clean Air Act enforcement", "Toxic chemical releases"],
                "url": "https://echo.epa.gov",
            },
            {
                "name": "NLRB Case Search",
                "type": "Federal Labor Board",
                "metrics": ["Unfair labor practice complaints", "Union election interference"],
                "url": "https://www.nlrb.gov/search/case",
            },
            {
                "name": "USDA Organic INTEGRITY Database",
                "type": "Certification Directory",
                "metrics": ["Certified organic farms and handlers", "Certification status"],
                "url": "https://organic.ams.usda.gov/integrity",
            },
            {
                "name": "NCUA Credit Union Directory",
                "type": "Federal Financial Regulator",
                "metrics": ["Credit union charter, assets, field of membership"],
                "url": "https://www.ncua.gov",
            },
        ],
        "integrity_firewall_policy": {
            "principle": "Grades are Shoptegrity opinions, applied with a published rubric to cited facts. A grade is withheld when its facts are not cited.",
            "rules": [
                "Our policy: no entity can pay to improve, alter, or remove a score.",
                "Our policy: we do not accept sponsored listings, paid placements, or consulting from rated brands. Commercial relationships are listed on the disclosures page.",
                "Our policy: every negative factual claim must cite an official regulatory record, legal filing, or primary document with a direct URL. A claim without a citation is marked withheld.",
                "The only affiliate link on the site is on the Sell Direct page. The test suite checks that the brand, healthcare, and swap pages carry no affiliate links.",
                "Our policy: corrections are reviewed before any change is made. See the corrections page for how to request one.",
            ],
        },
    }
