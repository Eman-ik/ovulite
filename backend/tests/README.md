# Ovulite Test Suite

Comprehensive automated test suite for the Ovulite backend API.

## Quick Start

```powershell
# Install dependencies
cd backend
pip install pytest pytest-asyncio pytest-cov httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Open coverage report
start htmlcov/index.html
```

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures (db, client, auth, sample data)
├── pytest.ini               # Test configuration
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_auth.py        # Password hashing, JWT generation (10 tests)
│   └── test_validation.py  # Pydantic schema validation (15 tests)
├── integration/             # API integration tests
│   ├── test_auth_api.py    # Auth endpoints (8 tests)
│   ├── test_validation_api.py   # Validation errors (10 tests)
│   ├── test_prediction_api.py   # ML prediction endpoint (12 tests)
│   ├── test_qc_api.py      # Quality control endpoints (15 tests)
│   ├── test_analytics_api.py    # Analytics dashboard (18 tests)
│   └── test_api_headers.py # Headers & middleware (12 tests)
├── regression/              # Regression tests (placeholders)
└── performance/             # Performance tests (placeholders)
```

**Total: 100+ tests created**

## Running Tests

### By Test Type

```powershell
# Unit tests only (fast)
pytest tests/unit/ -v

# Integration tests only
pytest tests/integration/ -v

# Specific test file
pytest tests/integration/test_auth_api.py -v

# Specific test class
pytest tests/unit/test_auth.py::TestPasswordHashing -v

# Specific test
pytest tests/unit/test_auth.py::TestPasswordHashing::test_password_hash_is_different_from_plaintext -v
```

### By Marker

```powershell
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run performance tests
pytest -m performance

# Skip slow tests
pytest -m "not slow"
```

### With Coverage

```powershell
# Coverage report in terminal
pytest --cov=app --cov-report=term

# HTML coverage report
pytest --cov=app --cov-report=html
# Open: htmlcov/index.html

# XML coverage report (for CI)
pytest --cov=app --cov-report=xml

# Coverage for specific module
pytest --cov=app.auth --cov-report=term
```

### Verbose Output

```powershell
# Verbose mode
pytest -v

# Very verbose (show all output)
pytest -vv

# Show print statements
pytest -s

# Show full tracebacks
pytest --tb=long

# Show short tracebacks
pytest --tb=short
```

## Test Fixtures

Defined in `conftest.py`:

### Database Fixtures

- **`db_engine`** (session-scoped): Test database engine (SQLite in-memory or PostgreSQL)
- **`db_session`** (function-scoped): Database session with automatic rollback after each test

### API Client Fixtures

- **`client`**: FastAPI TestClient for making API requests
- **`admin_user`**: Creates admin user via `/auth/seed`
- **`admin_token`**: JWT token for admin user
- **`auth_headers`**: Authorization headers with Bearer token

### Sample Data Fixtures

- **`sample_donor_data`**: Sample donor payload
- **`sample_sire_data`**: Sample sire payload
- **`sample_recipient_data`**: Sample recipient payload
- **`sample_transfer_data`**: Sample ET transfer payload
- **`sample_prediction_input`**: Sample prediction request payload

## Test Configuration

Configuration in `pytest.ini`:

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

markers =
    unit: Unit tests (fast, isolated)
    integration: Integration tests (API, database)
    regression: Regression tests (critical user flows)
    performance: Performance/load tests
    slow: Slow-running tests

asyncio_mode = auto
```

## Environment Variables

Tests use environment variables for configuration:

```powershell
# Database (defaults to SQLite in-memory)
$env:DATABASE_URL = "postgresql://user:pass@localhost/ovulite_test"

# JWT secrets (use test values)
$env:SECRET_KEY = "test-secret-key"
$env:JWT_SECRET_KEY = "test-jwt-secret"
```

## CI/CD Integration

Tests run automatically on push/PR via GitHub Actions (`.github/workflows/test.yml`):

1. **Lint**: flake8, black, isort
2. **Unit Tests**: Fast isolated tests
3. **Integration Tests**: API + Database tests with PostgreSQL
4. **E2E Tests**: Playwright browser tests
5. **Regression Tests**: Critical user flows (main branch only)

## Test Coverage Goals

- **Overall**: >75% code coverage
- **Auth module**: >85% coverage
- **Validation module**: >85% coverage
- **API endpoints**: >70% coverage

## Writing New Tests

### Unit Test Template

```python
import pytest

@pytest.mark.unit
class TestFeatureName:
    """Test feature description"""

    def test_specific_behavior(self):
        """Test that specific behavior works correctly"""
        # Arrange
        input_value = "test"
        
        # Act
        result = function_under_test(input_value)
        
        # Assert
        assert result == expected_value
```

### Integration Test Template

```python
import pytest

@pytest.mark.integration
class TestEndpointName:
    """Test /api/v1/endpoint"""

    def test_endpoint_returns_200(self, client, auth_headers):
        """Test that endpoint returns 200 with valid request"""
        response = client.get(
            "/api/v1/endpoint",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data
```

## Troubleshooting

### Import Errors

```powershell
# Ensure backend directory is in PYTHONPATH
cd backend
pytest
```

### Database Errors

```powershell
# Use PostgreSQL for production-like tests
$env:DATABASE_URL = "postgresql://user:pass@localhost/ovulite_test"

# Or use SQLite (default)
Remove-Item Env:\DATABASE_URL
```

### Fixture Not Found

Make sure fixture is defined in `conftest.py` or imported properly.

### Async Test Issues

Use `pytest-asyncio` and mark async tests:

```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov](https://pytest-cov.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Test Strategy](.gsd/test-strategy/TEST_STRATEGY.md)
- [Implementation Checklist](.gsd/test-strategy/IMPLEMENTATION_CHECKLIST.md)
