"""Community & Field Journal Service.

Manages editorial articles, structured discussions, swap impact tallies,
and the crowdsourced private equity rollup tip-line.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from api.app.models.community import (
    JournalArticle,
    DiscussionTopic,
    DiscussionComment,
    RollupTip,
)
from api.app.models.core import generate_uuid


SAMPLE_ARTICLES = [
    {
        "slug": "swedish-coop-revolt-breaking-cartels",
        "title": "How Swedish Co-ops Broke the Cartels: A Modern Manual for American Shoppers",
        "subtitle": "In the 1920s, private monopoly trusts controlled flour, bread, and electric light in Scandinavia. Working families didn't ask politicians for help—they built competing cooperative factories and bankrupted the cartels.",
        "category": "Historical Precedents",
        "author": "Shoptegrity Economic History Desk",
        "read_time": "6 min read",
        "hero_icon": "🌾",
        "body_html": """
<p>Today, American consumers feel trapped in a grocery aisle dominated by 10 multi-billion-dollar conglomerates. If you want oatmeal, soup, or cleaning spray, you are almost always buying from General Mills, Unilever, PepsiCo, or Nestlé. When prices skyrocket, corporate spokespeople blame inflation while their SEC filings celebrate record stock buybacks.</p>

<p>Almost exactly 100 years ago, Swedish workers faced the exact same bottleneck.</p>

<h3>The Flour Trust of Stockholm</h3>
<p>In the early 1920s, the Swedish milling cartel (known as <em>Kvarnkartellen</em>) had acquired every commercial grain mill in the nation. They fixed the price of flour so high that Swedish working families were spending over 35% of their total income just on basic daily bread. Meanwhile, the mill owners returned gigantic dividend payouts to the Stockholm aristocracy.</p>

<p>Instead of lobbying a gridlocked parliament or organizing short-lived boycotts that left people hungry, working-class households took a different route: <strong>economic counter-organization</strong>.</p>

<h3>The Rochdale Strategy at Industrial Scale</h3>
<p>Under the banner of <strong>Kooperativa Förbundet (KF)</strong>, hundreds of local neighborhood buying clubs pooled modest membership fees—often just a few kronor a week. In 1922, they took a bold gamble: they raised enough capital to buy the massive Tre Kronor mill in Stockholm harbor.</p>

<p>When the cartel attempted to price-gouge, KF did something revolutionary: <strong>they sold top-grade flour at true cost-plus-operations</strong>. Within six months:</p>
<ul>
  <li>The private cartel was forced to slash national flour prices by 25%.</li>
  <li>KF expanded from flour to margarine, rubber boots, and oatmeal.</li>
  <li>In 1931, when General Electric and the Phoebus Cartel doubled the price of incandescent lightbulbs, KF built its own cooperative lightbulb factory (Luma), cutting national lightbulb prices across Scandinavia in half within a year.</li>
</ul>

<h3>The Lesson for America in 2026</h3>
<p>Monopolies are vulnerable to cooperative competition. When consumers organize their purchasing power into member-owned institutions—like modern food co-ops, Azure Standard bulk drops, and employee-owned producers (King Arthur, WinCo Foods, Bob's Red Mill)—the corporate siphon loses its leverage.</p>
        """
    },
    {
        "slug": "disguised-private-equity-rollup-machine",
        "title": "The Disguised Rollup: Why Your Local Vet & Plumber Suddenly Got Sold to Wall Street",
        "subtitle": "Private equity platforms are quietly buying thousands of family HVAC, veterinary, and plumbing businesses. They keep the grandfather's name on the van, triple the invoice rates, and extract the wealth to Manhattan.",
        "category": "Investigative",
        "author": "Shoptegrity Corporate Research",
        "read_time": "7 min read",
        "hero_icon": "🏢",
        "body_html": """
<p>If you have called your trusted local plumber or veterinary clinic recently and walked away with a bill that was 200% higher than three years ago, you may not be experiencing inflation. You may be interacting with a <strong>disguised private equity rollup</strong>.</p>

<h3>The Rollup Playbook</h3>
<p>Over the past decade, private equity firms discovered that essential local services—trades that cannot be outsourced overseas or automated by AI—are goldmines for leveraged cash flow. Platforms like Apex Service Partners, Wrench Group, and Mars Petcare have acquired thousands of local businesses.</p>

<p>The core trick is psychological: <strong>they deliberately retain the legacy family name</strong>. The sign out front still says 'Miller & Sons Plumbing, Established 1974.' The familiar white vans still park in your driveway. But behind the scenes:</p>
<ul>
  <li>The original family owners have cashed out and signed non-compete agreements.</li>
  <li>Technicians are paid on commission and given high-pressure sales scripts requiring them to recommend full $12,000 system replacements instead of a $200 valve repair.</li>
  <li>Up to 40% of every customer payment is funneled out of state to service leveraged buyout debt and pay private equity management fees.</li>
</ul>

<h3>How Shoptegrity's Swarm Desk Fights Back</h3>
<p>We believe consumers have a fundamental right to know who cashes their check. Our <strong>Local Directory (`/local`)</strong> and community whistleblower tip-line cross-reference state business entity registries to expose these disguised platforms and redirect homeowners to genuine independent owner-operators.</p>
        """
    },
    {
        "slug": "the-90-10-wealth-pump-blackrock-vanguard-empire",
        "title": "The 90/10 Wealth Siphon: How 401(k) Auto-Deductions Built an Asset Monopoly",
        "subtitle": "Federal Reserve data proves the top 10% of Americans own roughly 90% of equities. Here is how automatic payroll deductions turned middle-class retirements into an extraction engine for the wealthiest decile.",
        "category": "Macroeconomics",
        "author": "Shoptegrity Economic Analysis",
        "read_time": "8 min read",
        "hero_icon": "📉",
        "body_html": """
<p>There is a comforting story told in financial media: <em>'The stock market is doing great, which means everyday Americans are doing great!'</em></p>

<p>The Federal Reserve’s official Distributional Financial Accounts tell a completely different story.</p>

<h3>The Hard Fed Data</h3>
<p>As of 2026, corporate stock and mutual fund ownership in the United States is distributed as follows:</p>
<ul>
  <li><strong>Top 1% of Households:</strong> Owns ~54.2% of all corporate equities and mutual fund shares.</li>
  <li><strong>Next 9% (90th–99th Percentile):</strong> Owns ~37.1%.</li>
  <li><strong>Combined Top 10%:</strong> Controls <strong>91.3%</strong> of total equity market wealth.</li>
  <li><strong>Middle 40% (50th–90th Percentile):</strong> Divides just 8.1%.</li>
  <li><strong>Bottom 50%:</strong> Holds only <strong>0.6%</strong> (essentially zero).</li>
</ul>

<h3>The Automated Conveyor Belt</h3>
<p>Every two weeks, millions of American workers have money automatically deducted from their paychecks into Target Date retirement funds managed by Vanguard, BlackRock, and State Street. These mega-managers pool that capital to buy S&P 500 shares.</p>

<p>When S&P 500 corporations raise consumer prices and execute multi-billion-dollar stock buybacks, <strong>91 cents of every dollar of net wealth generated goes directly to the top 10%</strong>. The average worker's $40,000 retirement account is mathematically diluted by the multi-million-dollar portfolios of the top tier.</p>

<p>To patch this leak, consumers must deliberately redirect daily transactions to worker-owned ESOPs, local credit unions, and direct-producer agriculture.</p>
        """
    }
]

SAMPLE_TOPICS = [
    {
        "slug": "credit-union-migration-stories",
        "title": "Credit Union Migration: Moving Money Out of Wall Street",
        "category": "Banking & Finance",
        "description": "Have you switched from a Big 4 bank (Chase, Wells, BofA, Citi) to a local credit union or community CDFI? Share your experiences, savings on fees, and advice for others making the leap.",
    },
    {
        "slug": "whistleblower-disguised-rollups",
        "title": "Whistleblower Desk: Exposing Disguised PE Rollups",
        "category": "Local Services & Trades",
        "description": "Notice a local HVAC company, vet clinic, or plumber that suddenly changed its pricing or sales tactics? Help our researchers investigate state corporate registry filings.",
    },
    {
        "slug": "csa-direct-farm-playbook",
        "title": "Direct Farm & CSA Sourcing: Cutting Out the Grocery Middleman",
        "category": "Food Chain Integrity",
        "description": "How do you source directly from local growers? Share your favorite regional CSAs, farm stands, and bulk buying clubs like Azure Standard.",
    },
    {
        "slug": "401k-proxy-voting-reform",
        "title": "Reclaiming Your 401(k): Proxy Voting & Non-Extractive Funds",
        "category": "Retirement & Policy",
        "description": "How to talk to your HR department about pass-through shareholder voting and adding worker-owned or non-Big-Three index options to employee retirement plans.",
    },
]

SAMPLE_COMMENTS = [
    {
        "topic_slug": "credit-union-migration-stories",
        "author_name": "Sarah M.",
        "author_location": "Minneapolis, MN",
        "content": "Moved our family accounts from Wells Fargo to a local teacher credit union last spring. Saved over $180 in monthly account maintenance and ATM fees, and our mortgage rate was 0.4% lower. Best economic move we ever made.",
        "swap_story": "Wells Fargo Checking -> Local Credit Union",
        "estimated_dollars_diverted": 2200.0,
    },
    {
        "topic_slug": "whistleblower-disguised-rollups",
        "author_name": "Dave R.",
        "author_location": "Columbus, OH",
        "content": "Our 25-year trusted neighborhood plumber suddenly showed up in an unmarked shiny wrap van. Tech refused to rebuild a toilet valve and tried to quote a $9,800 whole-house repipe on an iPad. Checked Ohio Sec of State: acquired 4 months ago by a Delaware LLC linked to private equity.",
        "swap_story": "Acquired Local Plumbing -> Certified Independent Master Plumber",
        "estimated_dollars_diverted": 9500.0,
    },
    {
        "topic_slug": "csa-direct-farm-playbook",
        "author_name": "Elena T.",
        "author_location": "Portland, OR",
        "content": "Joined our first vegetable CSA this year. $35/week gets us two full crates of heirloom organic produce harvested the morning of delivery. Farmer keeps 100% of the cash instead of the 11 cents Kroger pays.",
        "swap_story": "Supermarket Produce -> 100% Direct Farm CSA",
        "estimated_dollars_diverted": 1400.0,
    }
]

SAMPLE_TIPS = [
    {
        "business_name": "Precision Air & Heating",
        "service_category": "HVAC",
        "city": "Phoenix",
        "state": "AZ",
        "suspected_acquirer": "Apex Service Partners (Private Equity)",
        "evidence_notes": "State LLC filing changed to Delaware holding company; technicians now use standardized high-pressure sales iPads.",
        "status": "verified"
    },
    {
        "business_name": "Valley Animal Hospital",
        "service_category": "Veterinary Clinic",
        "city": "Denver",
        "state": "CO",
        "suspected_acquirer": "Mars Petcare (VCA)",
        "evidence_notes": "Prescription diets switched exclusively to Royal Canin; billing system rebranded to corporate portal.",
        "status": "verified"
    },
    {
        "business_name": "Heritage Tree & Landscaping",
        "service_category": "Home Services",
        "city": "Austin",
        "state": "TX",
        "suspected_acquirer": "Commercial Tree Platform LLC",
        "evidence_notes": "Longtime local owner retired; phone numbers redirect to out-of-state call center in Georgia.",
        "status": "under_investigation"
    }
]


def seed_community_data(db: Session):
    """Ensure baseline articles, discussion topics, and initial tips exist."""
    # 1. Seed Articles
    for art in SAMPLE_ARTICLES:
        existing = db.query(JournalArticle).filter(JournalArticle.slug == art["slug"]).first()
        if not existing:
            obj = JournalArticle(
                id=generate_uuid(),
                slug=art["slug"],
                title=art["title"],
                subtitle=art["subtitle"],
                category=art["category"],
                author=art["author"],
                read_time=art["read_time"],
                hero_icon=art["hero_icon"],
                body_html=art["body_html"],
                created_at=datetime.now(timezone.utc),
            )
            db.add(obj)

    # 2. Seed Topics
    topic_map = {}
    for top in SAMPLE_TOPICS:
        existing = db.query(DiscussionTopic).filter(DiscussionTopic.slug == top["slug"]).first()
        if not existing:
            obj = DiscussionTopic(
                id=generate_uuid(),
                slug=top["slug"],
                title=top["title"],
                category=top["category"],
                description=top["description"],
                created_at=datetime.now(timezone.utc),
            )
            db.add(obj)
            db.flush()
            topic_map[top["slug"]] = obj.id
        else:
            topic_map[top["slug"]] = existing.id

    # 3. Seed Comments
    for comm in SAMPLE_COMMENTS:
        t_id = topic_map.get(comm["topic_slug"])
        if t_id:
            has_comment = db.query(DiscussionComment).filter(
                DiscussionComment.topic_id == t_id,
                DiscussionComment.author_name == comm["author_name"]
            ).first()
            if not has_comment:
                c_obj = DiscussionComment(
                    id=generate_uuid(),
                    topic_id=t_id,
                    author_name=comm["author_name"],
                    author_location=comm["author_location"],
                    content=comm["content"],
                    swap_story=comm["swap_story"],
                    estimated_dollars_diverted=comm["estimated_dollars_diverted"],
                    created_at=datetime.now(timezone.utc),
                )
                db.add(c_obj)

    # 4. Seed Rollup Tips
    for tip in SAMPLE_TIPS:
        existing = db.query(RollupTip).filter(
            RollupTip.business_name == tip["business_name"],
            RollupTip.city == tip["city"]
        ).first()
        if not existing:
            t_obj = RollupTip(
                id=generate_uuid(),
                business_name=tip["business_name"],
                service_category=tip["service_category"],
                city=tip["city"],
                state=tip["state"],
                suspected_acquirer=tip["suspected_acquirer"],
                evidence_notes=tip["evidence_notes"],
                status=tip["status"],
                created_at=datetime.now(timezone.utc),
            )
            db.add(t_obj)

    db.commit()


def get_articles(db: Session, limit: int = 10) -> List[JournalArticle]:
    return db.query(JournalArticle).order_by(JournalArticle.created_at.desc()).limit(limit).all()


def get_article_by_slug(db: Session, slug: str) -> Optional[JournalArticle]:
    return db.query(JournalArticle).filter(JournalArticle.slug == slug).first()


def get_topics(db: Session) -> List[DiscussionTopic]:
    return db.query(DiscussionTopic).order_by(DiscussionTopic.created_at.asc()).all()


def get_topic_by_slug(db: Session, slug: str) -> Optional[DiscussionTopic]:
    return db.query(DiscussionTopic).filter(DiscussionTopic.slug == slug).first()


def add_comment(
    db: Session,
    topic_id: str,
    author_name: str,
    author_location: Optional[str],
    content: str,
    swap_story: Optional[str] = None,
    dollars_diverted: Optional[float] = 0.0,
) -> DiscussionComment:
    comment = DiscussionComment(
        id=generate_uuid(),
        topic_id=topic_id,
        author_name=author_name or "Community Member",
        author_location=author_location,
        content=content,
        swap_story=swap_story,
        estimated_dollars_diverted=dollars_diverted or 0.0,
        created_at=datetime.now(timezone.utc),
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def add_rollup_tip(
    db: Session,
    business_name: str,
    service_category: str,
    city: str,
    state: str,
    suspected_acquirer: str,
    evidence_notes: str,
) -> RollupTip:
    tip = RollupTip(
        id=generate_uuid(),
        business_name=business_name,
        service_category=service_category,
        city=city,
        state=state,
        suspected_acquirer=suspected_acquirer,
        evidence_notes=evidence_notes,
        status="under_investigation",
        created_at=datetime.now(timezone.utc),
    )
    db.add(tip)
    db.commit()
    db.refresh(tip)
    return tip


def get_recent_tips(db: Session, limit: int = 15) -> List[RollupTip]:
    return db.query(RollupTip).order_by(RollupTip.created_at.desc()).limit(limit).all()


def get_impact_summary(db: Session) -> Dict[str, Any]:
    """Calculate community impact metrics."""
    from sqlalchemy import func

    total_tips = db.query(func.count(RollupTip.id)).scalar() or 0
    verified_tips = db.query(func.count(RollupTip.id)).filter(RollupTip.status == "verified").scalar() or 0
    total_comments = db.query(func.count(DiscussionComment.id)).scalar() or 0
    dollars_diverted = db.query(func.sum(DiscussionComment.estimated_dollars_diverted)).scalar() or 0.0

    return {
        "total_whistleblower_tips": total_tips,
        "verified_rollups": verified_tips,
        "total_swap_stories": total_comments,
        "total_dollars_diverted": round(dollars_diverted, 2),
    }
