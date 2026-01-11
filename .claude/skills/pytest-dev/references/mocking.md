# Mocking & Patching

## Table of Contents
- [Monkeypatch](#monkeypatch)
- [unittest.mock](#unittestmock)
- [HTTP Mocking](#http-mocking)
- [Environment Variables](#environment-variables)

## Monkeypatch

pytest's built-in fixture for patching:

```python
def test_with_monkeypatch(monkeypatch):
    # Patch a function
    monkeypatch.setattr("module.function", lambda: "mocked")

    # Patch an attribute
    monkeypatch.setattr(obj, "attribute", "new_value")

    # Set environment variable
    monkeypatch.setenv("API_KEY", "test-key")

    # Delete attribute
    monkeypatch.delattr(obj, "attribute")
```

## unittest.mock

For more complex mocking scenarios:

```python
from unittest.mock import Mock, patch, MagicMock

def test_with_mock():
    mock_service = Mock()
    mock_service.get_data.return_value = {"id": 1}

    result = function_using_service(mock_service)
    mock_service.get_data.assert_called_once()

@patch("module.external_api")
def test_with_patch(mock_api):
    mock_api.return_value = {"status": "ok"}
    result = call_api()
    assert result["status"] == "ok"
```

### Async Mocking

```python
from unittest.mock import AsyncMock

async def test_async_mock():
    mock_client = AsyncMock()
    mock_client.fetch.return_value = {"data": "test"}

    result = await mock_client.fetch()
    assert result == {"data": "test"}
```

## HTTP Mocking

### Using responses (for requests library)

```bash
uv add --dev responses
```

```python
import responses

@responses.activate
def test_external_api():
    responses.add(
        responses.GET,
        "https://api.example.com/data",
        json={"id": 1},
        status=200
    )

    result = fetch_from_api()
    assert result["id"] == 1
```

### Using respx (for httpx)

```bash
uv add --dev respx
```

```python
import respx
from httpx import Response

@respx.mock
async def test_httpx_call():
    respx.get("https://api.example.com/data").mock(
        return_value=Response(200, json={"id": 1})
    )

    result = await async_fetch()
    assert result["id"] == 1
```

## Environment Variables

```python
def test_env_config(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("DEBUG", "true")

    config = load_config()
    assert config.debug is True
```

Using pytest-env plugin:

```toml
# pyproject.toml
[tool.pytest.ini_options]
env = [
    "DATABASE_URL=sqlite:///:memory:",
    "DEBUG=true",
]
```
