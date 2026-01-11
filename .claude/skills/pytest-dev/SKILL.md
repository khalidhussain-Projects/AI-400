---
name: pytest-dev
description: Python testing assistant using pytest framework. Use when writing, running, or debugging tests for Python projects including FastAPI/web APIs and general Python code. Triggers on test creation, test debugging, coverage analysis, fixture setup, or when user mentions pytest, unit tests, or testing Python code. Uses uv for dependency management (--dev flag).
---

# Pytest Development

Write and run Python tests using pytest with uv for dependency management.

## Quick Start

### Setup Testing Environment

```bash
# Add pytest and common testing dependencies
uv add --dev pytest httpx pytest-cov pytest-asyncio
```

### Basic Test Structure

```python
# test_example.py
def test_addition():
    assert 1 + 1 == 2

def test_string_methods():
    assert "hello".upper() == "HELLO"
```

Run: `uv run pytest` or `uv run pytest -v` (verbose)

## Test Discovery

pytest automatically finds tests matching these patterns:
- Files: `test_*.py` or `*_test.py`
- Functions: `test_*`
- Classes: `Test*` (no `__init__` method)

## Writing Tests

### Assertions

```python
# Basic assertions
assert value == expected
assert value != other
assert value is None
assert value is not None
assert value in collection
assert isinstance(obj, MyClass)

# With custom messages
assert result == 42, f"Expected 42, got {result}"
```

### Testing Exceptions

```python
import pytest

def test_raises_error():
    with pytest.raises(ValueError):
        int("not a number")

def test_raises_with_message():
    with pytest.raises(ValueError, match="invalid literal"):
        int("not a number")
```

### Parametrized Tests

```python
import pytest

@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_double(input, expected):
    assert input * 2 == expected
```

## FastAPI Testing

```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}

def test_create_item():
    response = client.post("/items/", json={"name": "Test", "price": 10.5})
    assert response.status_code == 201
```

## Common pytest Commands

| Command | Purpose |
|---------|---------|
| `uv run pytest` | Run all tests |
| `uv run pytest -v` | Verbose output |
| `uv run pytest test_file.py` | Run specific file |
| `uv run pytest test_file.py::test_name` | Run specific test |
| `uv run pytest -k "keyword"` | Run tests matching keyword |
| `uv run pytest -x` | Stop on first failure |
| `uv run pytest --tb=short` | Shorter tracebacks |
| `uv run pytest --cov=src` | Run with coverage |

## Testing Scenarios

For detailed patterns on specific testing scenarios, see:

- **Fixtures & Mocking**: [references/fixtures.md](references/fixtures.md) - pytest fixtures, conftest.py, mocking
- **Async Testing**: [references/async.md](references/async.md) - testing async/await code
- **Database Testing**: [references/database.md](references/database.md) - SQLAlchemy, test databases
- **API Mocking**: [references/mocking.md](references/mocking.md) - responses, httpx-mock, monkeypatch

## Documentation Lookup

For latest pytest documentation or specific features not covered here, use the browsing-with-playwright skill to fetch official docs from https://docs.pytest.org/
