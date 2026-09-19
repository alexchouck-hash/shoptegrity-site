import pytest
from pipeline.seed_data import run_seed


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Initializes and seeds the database before running tests."""
    run_seed()
