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
            "principle": "Scores are derived strictly from documented, publicly verifiable facts and pure mathematical rubrics.",
            "rules": [
                "No entity can pay to improve, alter, or remove a score.",
                "Affiliate relationships or advertising never touch the scoring engine. Affiliate data lives in a separate isolated database layer that the rubric engine cannot read.",
                "Every negative claim must cite an official regulatory record, legal settlement, or filed document with a direct URL.",
                "Corrections submitted with valid evidence are reviewed and publicly logged within 5 business days.",
            ],
        },
    }
