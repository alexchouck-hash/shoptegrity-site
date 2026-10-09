import pytest
from fastapi.testclient import TestClient
from api.app.main import app

client = TestClient(app)


def test_community_hub_view():
    res = client.get("/community")
    assert res.status_code == 200
    assert "The Shoptegrity Commons" in res.text
    assert "The Field Journal" in res.text
    assert "Whistleblower Tip-Line" in res.text
    assert "Action Commons &amp; Swap Stories" in res.text or "Action Commons & Swap Stories" in res.text


def test_article_detail_view_success():
    res = client.get("/community/journal/swedish-coop-revolt-breaking-cartels")
    assert res.status_code == 200
    assert "How Swedish Co-ops Broke the Cartels" in res.text
    assert "Kooperativa Förbundet" in res.text
    assert "Turn Information into Direct Action" in res.text


def test_article_detail_view_not_found():
    res = client.get("/community/journal/non-existent-investigation-article")
    assert res.status_code == 404


def test_submit_rollup_tip():
    form_data = {
        "business_name": "Test Hometown Plumber",
        "service_category": "Plumbing",
        "city": "Austin",
        "state": "TX",
        "suspected_acquirer": "Lone Star PE Holdings",
        "evidence_notes": "Techs started using pushy sales quotes and invoice now has a Delaware LLC parent name.",
    }
    res = client.post("/community/tips", data=form_data, follow_redirects=False)
    assert res.status_code == 303
    assert "/community?tip_submitted=true#whistleblower" in res.headers["location"]

    # Verify it shows up in the API
    res_tips = client.get("/v1/community/tips")
    assert res_tips.status_code == 200
    tips = res_tips.json()
    matched = [t for t in tips if t["business_name"] == "Test Hometown Plumber"]
    assert len(matched) >= 1
    assert matched[0]["suspected_acquirer"] == "Lone Star PE Holdings"
    assert matched[0]["state"] == "TX"


def test_submit_topic_comment():
    # First fetch topics to get a valid topic ID
    hub_res = client.get("/community")
    assert hub_res.status_code == 200

    # Get topics via DB or test with a known seeded topic
    from api.app.db.session import SessionLocal
    from api.app.services.community_service import get_topics

    db = SessionLocal()
    topics = get_topics(db)
    assert len(topics) > 0
    target_topic = topics[0]
    db.close()

    comment_data = {
        "author_name": "Maria Organizer",
        "author_location": "Portland, OR",
        "content": "We moved our neighborhood clinic accounts to a local credit union. It took one afternoon.",
        "swap_story": "MegaBank -> Local CU",
        "dollars_diverted": 12000.0,
    }
    res = client.post(f"/community/discussions/{target_topic.id}/comments", data=comment_data, follow_redirects=False)
    assert res.status_code == 303
    assert f"/community?topic_id={target_topic.id}#discussions" in res.headers["location"]


def test_api_articles():
    res = client.get("/v1/community/articles")
    assert res.status_code == 200
    articles = res.json()
    assert len(articles) >= 3
    slugs = [a["slug"] for a in articles]
    assert "swedish-coop-revolt-breaking-cartels" in slugs
    assert "disguised-private-equity-rollup-machine" in slugs


def test_api_article_detail():
    res = client.get("/v1/community/articles/swedish-coop-revolt-breaking-cartels")
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "How Swedish Co-ops Broke the Cartels: A Modern Manual for American Shoppers"
    assert "body_html" in data
    assert len(data["body_html"]) > 100


def test_api_community_impact():
    res = client.get("/v1/community/impact")
    assert res.status_code == 200
    data = res.json()
    assert "total_whistleblower_tips" in data
    assert "verified_rollups" in data
    assert "total_swap_stories" in data
    assert "total_dollars_diverted" in data
    assert data["total_whistleblower_tips"] >= 1
    assert data["total_dollars_diverted"] > 0
