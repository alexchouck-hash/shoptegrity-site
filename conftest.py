import os

# Tests must never write into the live database (shoptegrity.db). Point the engine at a
# separate file before any app module is imported; override with DATABASE_URL to run in parallel.
os.environ.setdefault("DATABASE_URL", "sqlite:///./.pytest_shoptegrity.db")

import pytest
from pipeline.seed_data import run_seed
from pipeline.top2000_brands import seed_top2000_db
from pipeline.healthcare_2000 import seed_healthcare_db
from api.app.db.session import SessionLocal


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Initializes and seeds the database before running tests."""
    run_seed()
    with SessionLocal() as db:
        seed_top2000_db(db)
        seed_healthcare_db(db)


