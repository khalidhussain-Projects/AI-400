# Fixtures & Conftest

## Table of Contents
- [Basic Fixtures](#basic-fixtures)
- [Fixture Scopes](#fixture-scopes)
- [conftest.py](#conftestpy)
- [Fixture Factories](#fixture-factories)

## Basic Fixtures

Fixtures provide reusable setup/teardown for tests:

```python
import pytest

@pytest.fixture
def sample_user():
    """Fixture that returns a user dict."""
    return {"name": "Alice", "email": "alice@example.com"}

def test_user_name(sample_user):
    assert sample_user["name"] == "Alice"
```

### Fixtures with Teardown

```python
@pytest.fixture
def temp_file():
    # Setup
    path = Path("test_file.txt")
    path.write_text("test content")

    yield path  # Test runs here

    # Teardown
    path.unlink()
```

## Fixture Scopes

| Scope | Created | Destroyed |
|-------|---------|-----------|
| `function` (default) | Per test | After test |
| `class` | Per test class | After class |
| `module` | Per module | After module |
| `session` | Once | End of session |

```python
@pytest.fixture(scope="module")
def db_connection():
    conn = create_connection()
    yield conn
    conn.close()
```

## conftest.py

Place shared fixtures in `conftest.py` - automatically discovered by pytest:

```python
# conftest.py
import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}
```

```python
# test_api.py - fixtures are automatically available
def test_endpoint(client, auth_headers):
    response = client.get("/protected", headers=auth_headers)
    assert response.status_code == 200
```

## Fixture Factories

When you need fixtures with parameters:

```python
@pytest.fixture
def make_user():
    def _make_user(name="Test", role="user"):
        return {"name": name, "role": role}
    return _make_user

def test_admin(make_user):
    admin = make_user(name="Admin", role="admin")
    assert admin["role"] == "admin"
```
