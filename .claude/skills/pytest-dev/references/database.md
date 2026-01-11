# Database Testing

## Table of Contents
- [SQLAlchemy Test Setup](#sqlalchemy-test-setup)
- [Test Database Fixture](#test-database-fixture)
- [Transaction Rollback Pattern](#transaction-rollback-pattern)
- [FastAPI Database Testing](#fastapi-database-testing)

## SQLAlchemy Test Setup

Use an in-memory SQLite database for fast tests:

```python
# conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base

@pytest.fixture(scope="function")
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.close()
```

## Test Database Fixture

```python
# conftest.py
@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    yield session

    session.rollback()
    session.close()

# test_models.py
def test_create_user(test_db):
    user = User(name="Test", email="test@example.com")
    test_db.add(user)
    test_db.commit()

    assert test_db.query(User).count() == 1
```

## Transaction Rollback Pattern

Wrap each test in a transaction that rolls back:

```python
@pytest.fixture
def db_session(test_db):
    connection = test_db.bind.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    transaction.rollback()
    connection.close()
```

## FastAPI Database Testing

Override the dependency to use test database:

```python
# conftest.py
from main import app, get_db

@pytest.fixture
def client(test_db):
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()

# test_api.py
def test_create_item(client):
    response = client.post("/items/", json={"name": "Test"})
    assert response.status_code == 201
```
