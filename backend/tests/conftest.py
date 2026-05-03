"""
Shared test fixtures for Ovulite backend tests.

This module provides pytest fixtures for:
- Database connections (test database)
- FastAPI test client
- Authentication tokens
- Sample data for testing
"""
import pytest
import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, get_db


# Test database URL - use in-memory SQLite for speed or PostgreSQL for production-like tests
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", 
    "sqlite:///:memory:"  # Fast in-memory database for unit/integration tests
    # For PostgreSQL: "postgresql://test:test@localhost:5433/ovulite_test"
)


@pytest.fixture(scope="session")
def db_engine():
    """
    Create a test database engine.
    Scope: session (created once per test session)
    """
    if "sqlite" in TEST_DATABASE_URL:
        # SQLite in-memory database - use StaticPool to share across threads
        engine = create_engine(
            TEST_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        # PostgreSQL test database
        engine = create_engine(TEST_DATABASE_URL)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    yield engine
    
    # Cleanup: drop all tables
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Create a new database session for each test.
    Automatically rolls back changes after the test.
    Scope: function (new session per test)
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    
    # Create session bound to this connection
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=connection)
    session = TestSessionLocal()
    
    yield session
    
    # Cleanup: rollback transaction and close connection
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """
    Create FastAPI test client with dependency overrides.
    Uses the test database session instead of production DB.
    Scope: function (new client per test)
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Session cleanup handled by db_session fixture
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    # Cleanup: remove override
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def admin_user(client, db_session):
    """
    Create admin user in test database.
    Returns the user object (not the token).
    Scope: function
    """
    # Call seed endpoint to create admin user
    response = client.post("/auth/seed")
    assert response.status_code in (201, 409), f"Failed to seed admin: {response.text}"

    # 409 means bootstrap user already exists; auth fixture can still login.
    if response.status_code == 409:
        return {"username": "admin"}

    user_data = response.json()
    return user_data


@pytest.fixture(scope="function")
def admin_token(client, admin_user):
    """
    Get JWT token for admin user.
    Scope: function
    """
    response = client.post(
        "/auth/login",
        data={"username": "admin", "password": "ovulite2026"},
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200, f"Failed to login admin: {response.text}"
    
    token_data = response.json()
    return token_data["access_token"]


@pytest.fixture(scope="function")
def auth_headers(admin_token):
    """
    Return authorization headers with Bearer token.
    Scope: function
    """
    return {"Authorization": f"Bearer {admin_token}"}


# Sample data fixtures for testing

@pytest.fixture
def sample_donor_data():
    """Sample donor data for testing"""
    return {
        "tag_id": "TEST-DONOR-001",
        "breed": "Holstein",
        "birth_weight_epd": 2.5,
        "notes": "Test donor for automated tests"
    }


@pytest.fixture
def sample_sire_data():
    """Sample sire data for testing"""
    return {
        "name": "TEST-SIRE-001",
        "breed": "Angus",
        "birth_weight_epd": 3.0,
        "semen_type": "Conventional",
        "notes": "Test sire for automated tests"
    }


@pytest.fixture
def sample_recipient_data():
    """Sample recipient data for testing"""
    return {
        "tag_id": "TEST-RECIP-001",
        "farm_location": "Test Farm",
        "cow_or_heifer": "Cow",
        "notes": "Test recipient for automated tests"
    }


@pytest.fixture
def sample_transfer_data():
    """Sample ET transfer data for testing (minimal required fields)"""
    return {
        "et_date": "2026-03-01",
        "recipient_tag": "TEST-RECIP-001",
        "donor_tag": "TEST-DONOR-001",
        "sire_name": "TEST-SIRE-001",
        "embryo_stage": 7,  # Blastocyst
        "embryo_grade": 1,
        "cl_size_mm": 25.0,
        "protocol_name": "CIDR",
        "fresh_or_frozen": "Fresh",
        "technician_name": "Test Technician"
    }


@pytest.fixture
def sample_prediction_input():
    """Sample prediction input for testing"""
    return {
        "cl_size_mm": 25.0,
        "embryo_stage": 7,
        "embryo_grade": 1,
        "protocol_name": "CIDR",
        "donor_breed": "Holstein",
        "sire_breed": "Angus",
        "fresh_or_frozen": "Fresh"
    }
