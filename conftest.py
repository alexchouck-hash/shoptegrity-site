import pytest
from pipeline.seed_data import run_seed
from pipeline.top2000_brands import seed_top2000_db
from api.app.db.session import SessionLocal


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Initializes and seeds the database before running tests."""
    run_seed()


