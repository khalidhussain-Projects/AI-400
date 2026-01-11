# Testing SQLModel Applications

## Table of Contents
- [Test Database Setup](#test-database-setup)
- [Pytest Fixtures](#pytest-fixtures)
- [Testing CRUD Operations](#testing-crud-operations)
- [Testing FastAPI Endpoints](#testing-fastapi-endpoints)
- [Async Testing](#async-testing)
- [Factory Patterns](#factory-patterns)

## Test Database Setup

### Installation
```bash
pip install pytest pytest-asyncio httpx
```

### conftest.py (Sync)
```python
import pytest
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.database import get_session
from app.models import Hero, Team  # Import all models

@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine(
        "sqlite://",  # In-memory database
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    yield engine

@pytest.fixture(name="session")
def session_fixture(engine):
    with Session(engine) as session:
        yield session

@pytest.fixture(name="client")
def client_fixture(session):
    def get_session_override():
        yield session

    app.dependency_overrides[get_session] = get_session_override
    from fastapi.testclient import TestClient
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
```

## Pytest Fixtures

### Sample Data Fixtures
```python
@pytest.fixture
def sample_team(session):
    team = Team(name="Avengers", headquarters="NYC")
    session.add(team)
    session.commit()
    session.refresh(team)
    return team

@pytest.fixture
def sample_hero(session, sample_team):
    hero = Hero(
        name="Spider-Man",
        secret_name="Peter Parker",
        age=25,
        team_id=sample_team.id
    )
    session.add(hero)
    session.commit()
    session.refresh(hero)
    return hero

@pytest.fixture
def sample_heroes(session, sample_team):
    heroes = [
        Hero(name="Iron Man", secret_name="Tony Stark", age=45, team_id=sample_team.id),
        Hero(name="Thor", secret_name="Thor Odinson", age=1500, team_id=sample_team.id),
        Hero(name="Hulk", secret_name="Bruce Banner", age=40, team_id=sample_team.id),
    ]
    for hero in heroes:
        session.add(hero)
    session.commit()
    for hero in heroes:
        session.refresh(hero)
    return heroes
```

## Testing CRUD Operations

### test_crud.py
```python
from sqlmodel import select
from app.models import Hero
from app.crud import create_hero, get_hero, update_hero, delete_hero

def test_create_hero(session):
    hero_data = HeroCreate(name="Batman", secret_name="Bruce Wayne")
    hero = create_hero(session, hero_data)

    assert hero.id is not None
    assert hero.name == "Batman"
    assert hero.secret_name == "Bruce Wayne"

def test_get_hero(session, sample_hero):
    hero = get_hero(session, sample_hero.id)

    assert hero is not None
    assert hero.name == sample_hero.name

def test_get_hero_not_found(session):
    hero = get_hero(session, 999)
    assert hero is None

def test_update_hero(session, sample_hero):
    update_data = HeroUpdate(name="Spider-Man 2099")
    hero = update_hero(session, sample_hero.id, update_data)

    assert hero.name == "Spider-Man 2099"
    assert hero.secret_name == sample_hero.secret_name  # Unchanged

def test_delete_hero(session, sample_hero):
    result = delete_hero(session, sample_hero.id)

    assert result is True
    assert get_hero(session, sample_hero.id) is None

def test_query_heroes_with_filter(session, sample_heroes):
    statement = select(Hero).where(Hero.age > 100)
    result = session.exec(statement).all()

    assert len(result) == 1
    assert result[0].name == "Thor"
```

## Testing FastAPI Endpoints

### test_api.py
```python
def test_create_hero_endpoint(client):
    response = client.post(
        "/heroes/",
        json={"name": "Deadpool", "secret_name": "Wade Wilson"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Deadpool"
    assert "id" in data

def test_read_hero_endpoint(client, sample_hero):
    response = client.get(f"/heroes/{sample_hero.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == sample_hero.name

def test_read_hero_not_found(client):
    response = client.get("/heroes/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Hero not found"

def test_read_heroes_endpoint(client, sample_heroes):
    response = client.get("/heroes/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == len(sample_heroes)

def test_update_hero_endpoint(client, sample_hero):
    response = client.patch(
        f"/heroes/{sample_hero.id}",
        json={"name": "Updated Hero"}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Hero"

def test_delete_hero_endpoint(client, sample_hero):
    response = client.delete(f"/heroes/{sample_hero.id}")

    assert response.status_code == 200

    # Verify deleted
    response = client.get(f"/heroes/{sample_hero.id}")
    assert response.status_code == 404
```

## Async Testing

### conftest.py (Async)
```python
import pytest
import pytest_asyncio
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import get_async_session

@pytest_asyncio.fixture
async def async_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def async_session(async_engine):
    async_session_maker = sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_maker() as session:
        yield session

@pytest_asyncio.fixture
async def async_client(async_session):
    async def get_session_override():
        yield async_session

    app.dependency_overrides[get_async_session] = get_session_override
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        yield client
    app.dependency_overrides.clear()
```

### test_async.py
```python
import pytest

@pytest.mark.asyncio
async def test_async_create_hero(async_client):
    response = await async_client.post(
        "/heroes/",
        json={"name": "Deadpool", "secret_name": "Wade Wilson"}
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Deadpool"

@pytest.mark.asyncio
async def test_async_read_heroes(async_client, async_session):
    # Create test data
    hero = Hero(name="Test Hero", secret_name="Secret")
    async_session.add(hero)
    await async_session.commit()

    response = await async_client.get("/heroes/")

    assert response.status_code == 200
    assert len(response.json()) == 1
```

## Factory Patterns

### factories.py
```python
from typing import Any
from app.models import Hero, Team

class HeroFactory:
    _counter = 0

    @classmethod
    def create(cls, session, **overrides) -> Hero:
        cls._counter += 1
        defaults = {
            "name": f"Hero {cls._counter}",
            "secret_name": f"Secret {cls._counter}",
            "age": 30,
        }
        defaults.update(overrides)
        hero = Hero(**defaults)
        session.add(hero)
        session.commit()
        session.refresh(hero)
        return hero

    @classmethod
    def create_batch(cls, session, count: int, **overrides) -> list[Hero]:
        return [cls.create(session, **overrides) for _ in range(count)]

class TeamFactory:
    _counter = 0

    @classmethod
    def create(cls, session, **overrides) -> Team:
        cls._counter += 1
        defaults = {
            "name": f"Team {cls._counter}",
            "headquarters": f"HQ {cls._counter}",
        }
        defaults.update(overrides)
        team = Team(**defaults)
        session.add(team)
        session.commit()
        session.refresh(team)
        return team
```

### Using Factories in Tests
```python
def test_with_factory(session):
    team = TeamFactory.create(session, name="Justice League")
    heroes = HeroFactory.create_batch(session, 5, team_id=team.id)

    assert len(heroes) == 5
    assert all(h.team_id == team.id for h in heroes)
```

## Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_api.py

# Run specific test function
pytest tests/test_api.py::test_create_hero_endpoint

# Run with coverage
pytest --cov=app --cov-report=html

# Run async tests only
pytest -m asyncio
```
