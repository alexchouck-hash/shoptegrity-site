from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from api.app.main import app
from api.app.db.session import SessionLocal
from api.app.models.core import generate_uuid
from api.app.models.community import JournalArticle, DiscussionTopic, DiscussionComment, RollupTip
from api.app.services.community_service import WITHHELD, get_discussion_rooms

client = TestClient(app)

PAUSED = "Submissions are paused on this copy of Shoptegrity."
NONE_PUBLISHED = "None published yet"

# Text from the removed sample articles, sample testimonials, sample tips, and the old form copy.
REMOVED_CONTENT = [
    "Swedish Co-ops",
    "Disguised Rollup",
    "90/10 Wealth Siphon",
    "Sarah M.",
    "Dave R.",
    "Elena T.",
    "Wells Fargo Checking",
    "Precision Air & Heating",
    "Valley Animal Hospital",
    "Heritage Tree & Landscaping",
    "Apex Service Partners",
    "Wrench Group",
    "Mars Petcare",
    "Submit for Corporate Registry Audit",
    "VERIFIED ROLLUP",
    "Corporate Registry",
    "Shoptegrity's Swarm Desk",
    "Use our databases",
    "Evidence-based deep dives",
]

JOURNAL_SLUGS = [
    "swedish-coop-revolt-breaking-cartels",
    "disguised-private-equity-rollup-machine",
    "the-90-10-wealth-pump-blackrock-vanguard-empire",
    "non-existent-investigation-article",
]


def _row_counts():
    db = SessionLocal()
    try:
        return {
            "articles": db.query(JournalArticle).count(),
            "topics": db.query(DiscussionTopic).count(),
            "comments": db.query(DiscussionComment).count(),
            "tips": db.query(RollupTip).count(),
        }
    finally:
        db.close()


@pytest.fixture
def published_tip():
    """A published tip, so the public filter can be checked. Removed after the test."""
    tip_id = generate_uuid()
    db = SessionLocal()
    try:
        db.add(RollupTip(
            id=tip_id,
            business_name="Published Test Hvac",
            service_category="HVAC",
            city="Testville",
            state="TX",
            suspected_acquirer="Example Acquirer LLC",
            evidence_notes="Example note text for the public filter",
            status="published",
            created_at=datetime.now(timezone.utc),
        ))
        db.commit()
    finally:
        db.close()
    yield tip_id
    db = SessionLocal()
    try:
        db.query(RollupTip).filter(RollupTip.id == tip_id).delete()
        db.commit()
    finally:
        db.close()


def test_community_hub_view():
    res = client.get("/community")
    assert res.status_code == 200
    assert "The Shoptegrity Commons" in res.text
    assert "The Field Journal" in res.text
    assert "Whistleblower Tip-Line" in res.text
    assert "Action Commons &amp; Swap Stories" in res.text or "Action Commons & Swap Stories" in res.text


def test_hub_has_no_removed_or_seeded_content():
    text = client.get("/community").text
    for marker in REMOVED_CONTENT:
        assert marker not in text, f"removed content still on page: {marker}"


def test_hub_shows_paused_forms_and_none_published():
    text = client.get("/community").text
    assert PAUSED in text
    assert NONE_PUBLISHED in text
    assert 'action="/community/tips"' not in text
    assert "/community/discussions/" not in text
    assert "<form" not in text


def test_get_handlers_do_not_write():
    before = _row_counts()
    for path in [
        "/community",
        "/community/journal/swedish-coop-revolt-breaking-cartels",
        "/v1/community/articles",
        "/v1/community/tips",
        "/v1/community/impact",
    ]:
        client.get(path)
    assert _row_counts() == before


@pytest.mark.parametrize("slug", JOURNAL_SLUGS)
def test_journal_pages_are_404(slug):
    res = client.get(f"/community/journal/{slug}")
    assert res.status_code == 404


def test_api_articles_are_not_public():
    res = client.get("/v1/community/articles")
    assert res.status_code == 200
    assert res.json() == []
    res = client.get("/v1/community/articles/swedish-coop-revolt-breaking-cartels")
    assert res.status_code == 404


def test_submitted_tip_is_saved_pending_and_not_listed():
    form_data = {
        "business_name": "Pending Test Plumbing Co",
        "service_category": "Plumbing",
        "city": "Austin",
        "state": "TX",
        "suspected_acquirer": "Example Holdings LLC",
        "evidence_notes": "Pending test note that must stay private.",
    }
    res = client.post("/community/tips", data=form_data, follow_redirects=False)
    assert res.status_code == 303
    assert "/community?tip_submitted=true#whistleblower" in res.headers["location"]

    db = SessionLocal()
    try:
        row = db.query(RollupTip).filter(RollupTip.business_name == "Pending Test Plumbing Co").first()
        assert row is not None
        assert row.status == "pending"
        db.delete(row)
        db.commit()
    finally:
        db.close()

    tips = client.get("/v1/community/tips").json()
    assert all(t["status"] == "published" for t in tips)
    assert all(t["business_name"] != "Pending Test Plumbing Co" for t in tips)
    assert "Pending test note that must stay private." not in client.get("/community").text


def test_published_tip_is_listed_with_claims_withheld(published_tip):
    tips = client.get("/v1/community/tips").json()
    matched = [t for t in tips if t["id"] == published_tip]
    assert len(matched) == 1
    assert matched[0]["status"] == "published"
    assert matched[0]["suspected_acquirer"] == WITHHELD
    assert matched[0]["evidence_notes"] == WITHHELD

    page = client.get("/community").text
    assert "Published Test Hvac" in page
    assert "Example Acquirer LLC" not in page
    assert "Example note text for the public filter" not in page

    impact = client.get("/v1/community/impact").json()
    assert impact["total_whistleblower_tips"] >= 1


def test_impact_is_zero_when_nothing_is_published():
    impact = client.get("/v1/community/impact").json()
    assert impact["total_whistleblower_tips"] == 0
    assert impact["verified_rollups"] == 0
    assert impact["total_swap_stories"] == 0
    assert impact["total_dollars_diverted"] == 0


def test_submitted_comment_is_saved_pending_and_not_shown():
    room_slug = "credit-union-migration-stories"
    content = "Pending comment body that must not be shown."
    comment_data = {
        "author_name": "Maria Organizer",
        "author_location": "Portland, OR",
        "content": content,
        "swap_story": "Big Bank -> Local CU",
        "dollars_diverted": 12000.0,
    }
    res = client.post(f"/community/discussions/{room_slug}/comments", data=comment_data, follow_redirects=False)
    assert res.status_code == 303
    assert f"/community?topic_id={room_slug}#discussions" in res.headers["location"]

    db = SessionLocal()
    try:
        comment = db.query(DiscussionComment).filter(DiscussionComment.content == content).first()
        assert comment is not None
        if hasattr(DiscussionComment, "status"):
            assert comment.status == "pending"
        db.delete(comment)
        db.commit()
    finally:
        db.close()

    assert content not in client.get("/community").text
    assert client.get("/v1/community/impact").json()["total_swap_stories"] == 0


def test_comment_on_unknown_room_is_404():
    res = client.post(
        "/community/discussions/no-such-room/comments",
        data={"author_name": "Someone", "content": "Hello"},
        follow_redirects=False,
    )
    assert res.status_code == 404


def test_discussion_rooms_are_defined_in_code():
    slugs = [room.slug for room in get_discussion_rooms()]
    assert len(slugs) == 4
    assert len(set(slugs)) == 4
