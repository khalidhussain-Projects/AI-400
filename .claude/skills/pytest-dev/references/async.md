# Async Testing

## Table of Contents
- [Setup](#setup)
- [Basic Async Tests](#basic-async-tests)
- [Async Fixtures](#async-fixtures)
- [FastAPI Async Testing](#fastapi-async-testing)

## Setup

```bash
uv add --dev pytest-asyncio
```

Configure in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

Or mark individual tests with `@pytest.mark.asyncio`.

## Basic Async Tests

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result == "expected"
```

With auto mode enabled:

```python
async def test_auto_detected():
    # No decorator needed with asyncio_mode = "auto"
    result = await fetch_data()
    assert result is not None
```

## Async Fixtures

```python
import pytest

@pytest.fixture
async def async_client():
    async with AsyncClient() as client:
        yield client

async def test_with_async_fixture(async_client):
    response = await async_client.get("/")
    assert response.status_code == 200
```

## FastAPI Async Testing

For async FastAPI endpoints, use httpx.AsyncClient:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from main import app

@pytest.fixture
async def async_client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

async def test_async_endpoint(async_client):
    response = await async_client.get("/async-endpoint")
    assert response.status_code == 200
```
