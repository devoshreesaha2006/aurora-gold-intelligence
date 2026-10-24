import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.app.database import Base, get_db
import backend.app.models  # Ensure all models are registered on Base.metadata
from backend.app.main import app
import backend.app.main as main_module
from backend.app.services.contract_service import seed_default_contracts

# Use StaticPool with in-memory SQLite so all connections share the same memory DB
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Creates fresh database tables per test and seeds standard contracts.
    """
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    seed_default_contracts(session)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session, monkeypatch):
    """
    FastAPI TestClient with overridden get_db dependency.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    # Keep application startup schema initialization isolated from the user's
    # configured database while tests use an overridden in-memory session.
    monkeypatch.setattr(main_module, "engine", test_engine)
    monkeypatch.setattr(main_module, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(main_module, "upgrade_provider_timestamp_column", lambda: None)
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
