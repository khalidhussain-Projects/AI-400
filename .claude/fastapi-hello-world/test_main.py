"""
Tests for the FastAPI CRUD Application.

TESTING WITH DATABASE:
----------------------
When testing database operations, we need a separate test database so we don't
mess with real data. We use SQLite in-memory database (":memory:") which:
- Lives only in RAM
- Is created fresh for each test
- Is automatically deleted when tests finish

FIXTURE EXPLAINED:
------------------
A pytest fixture is a function that provides data or setup for tests.
- @pytest.fixture decorator marks a function as a fixture
- Tests can request fixtures by including them as parameters
- Fixtures can have different scopes (function, class, module, session)
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from main import app
from database import get_session
from models import Item


# =============================================================================
# TEST DATABASE SETUP
# =============================================================================
@pytest.fixture(name="session")
def session_fixture():
    """
    Create a fresh in-memory database for each test.

    WHY IN-MEMORY DATABASE?
    - Fast: No disk I/O
    - Isolated: Each test gets a fresh database
    - Clean: Automatically destroyed after test

    StaticPool keeps the same connection for the whole test,
    which is required for in-memory SQLite.
    """
    engine = create_engine(
        "sqlite://",  # In-memory SQLite
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Reuse the same connection
    )
    SQLModel.metadata.create_all(engine)  # Create tables
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """
    Create a TestClient that uses our test database.

    DEPENDENCY OVERRIDE:
    - We replace get_session with a function that returns our test session
    - This way, all database operations use the test database
    - After the test, we restore the original dependency
    """

    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()  # Clean up after test


# =============================================================================
# TEST: ROOT ENDPOINT
# =============================================================================
def test_read_root(client: TestClient):
    """Test the welcome message endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to the Items API! Visit /docs for documentation."
    }


# =============================================================================
# TEST: CREATE (POST /items/)
# =============================================================================
def test_create_item(client: TestClient):
    """
    Test creating a new item.

    WHAT WE TEST:
    1. POST request returns 200 status
    2. Response includes the data we sent
    3. Response includes a generated 'id'
    4. Default values are applied (is_available=True)
    """
    response = client.post(
        "/items/",
        json={
            "name": "Test Item",
            "description": "A test item",
            "price": 9.99,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Item"
    assert data["description"] == "A test item"
    assert data["price"] == 9.99
    assert data["is_available"] is True  # Default value
    assert "id" in data  # ID should be generated


def test_create_item_without_description(client: TestClient):
    """Test that description is optional."""
    response = client.post(
        "/items/",
        json={"name": "Simple Item", "price": 5.00},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Simple Item"
    assert data["description"] is None  # Optional field


def test_create_item_invalid_price(client: TestClient):
    """
    Test that price must be greater than 0.

    VALIDATION:
    - In models.py, we defined: price: float = Field(gt=0)
    - 'gt=0' means "greater than 0"
    - FastAPI returns 422 for validation errors
    """
    response = client.post(
        "/items/",
        json={"name": "Free Item", "price": 0},  # Invalid: price must be > 0
    )

    assert response.status_code == 422  # Validation error


# =============================================================================
# TEST: READ ALL (GET /items/)
# =============================================================================
def test_read_items_empty(client: TestClient):
    """Test reading items when database is empty."""
    response = client.get("/items/")

    assert response.status_code == 200
    assert response.json() == []  # Empty list


def test_read_items(client: TestClient, session: Session):
    """
    Test reading multiple items.

    ARRANGE:
    - First, we create items directly in the database
    - This is faster than using POST requests
    """
    # ARRANGE: Create test items in database
    item1 = Item(name="Item 1", price=10.00)
    item2 = Item(name="Item 2", price=20.00)
    session.add(item1)
    session.add(item2)
    session.commit()

    # ACT: Get all items
    response = client.get("/items/")

    # ASSERT
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Item 1"
    assert data[1]["name"] == "Item 2"


def test_read_items_pagination(client: TestClient, session: Session):
    """
    Test pagination with skip and limit.

    PAGINATION:
    - skip: How many items to skip from the start
    - limit: Maximum number of items to return
    """
    # ARRANGE: Create 5 items
    for i in range(5):
        session.add(Item(name=f"Item {i}", price=float(i + 1)))
    session.commit()

    # ACT: Get items 2-3 (skip 2, limit 2)
    response = client.get("/items/?skip=2&limit=2")

    # ASSERT
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "Item 2"
    assert data[1]["name"] == "Item 3"


# =============================================================================
# TEST: READ ONE (GET /items/{item_id})
# =============================================================================
def test_read_item(client: TestClient, session: Session):
    """Test reading a single item by ID."""
    # ARRANGE
    item = Item(name="Single Item", price=15.00)
    session.add(item)
    session.commit()
    session.refresh(item)  # Get the generated ID

    # ACT
    response = client.get(f"/items/{item.id}")

    # ASSERT
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == item.id
    assert data["name"] == "Single Item"


def test_read_item_not_found(client: TestClient):
    """
    Test reading an item that doesn't exist.

    HTTP 404:
    - 404 = "Not Found"
    - This is the standard response when a resource doesn't exist
    """
    response = client.get("/items/999")  # ID 999 doesn't exist

    assert response.status_code == 404
    assert response.json()["detail"] == "Item not found"


# =============================================================================
# TEST: UPDATE (PATCH /items/{item_id})
# =============================================================================
def test_update_item(client: TestClient, session: Session):
    """Test updating an item."""
    # ARRANGE
    item = Item(name="Old Name", description="Old desc", price=10.00)
    session.add(item)
    session.commit()
    session.refresh(item)

    # ACT: Update name and price
    response = client.patch(
        f"/items/{item.id}",
        json={"name": "New Name", "price": 25.00},
    )

    # ASSERT
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Name"
    assert data["price"] == 25.00
    assert data["description"] == "Old desc"  # Unchanged


def test_update_item_partial(client: TestClient, session: Session):
    """
    Test partial update (only one field).

    PATCH is for partial updates:
    - Only fields included in the request are updated
    - Other fields remain unchanged
    """
    # ARRANGE
    item = Item(name="Original", price=10.00, is_available=True)
    session.add(item)
    session.commit()
    session.refresh(item)

    # ACT: Only update is_available
    response = client.patch(
        f"/items/{item.id}",
        json={"is_available": False},
    )

    # ASSERT
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Original"  # Unchanged
    assert data["price"] == 10.00  # Unchanged
    assert data["is_available"] is False  # Updated


def test_update_item_not_found(client: TestClient):
    """Test updating an item that doesn't exist."""
    response = client.patch("/items/999", json={"name": "New Name"})

    assert response.status_code == 404


# =============================================================================
# TEST: DELETE (DELETE /items/{item_id})
# =============================================================================
def test_delete_item(client: TestClient, session: Session):
    """Test deleting an item."""
    # ARRANGE
    item = Item(name="To Delete", price=5.00)
    session.add(item)
    session.commit()
    session.refresh(item)

    # ACT: Delete the item
    response = client.delete(f"/items/{item.id}")

    # ASSERT: Check response
    assert response.status_code == 200
    assert response.json()["message"] == "Item deleted successfully"

    # ASSERT: Verify item is actually deleted
    get_response = client.get(f"/items/{item.id}")
    assert get_response.status_code == 404


def test_delete_item_not_found(client: TestClient):
    """Test deleting an item that doesn't exist."""
    response = client.delete("/items/999")

    assert response.status_code == 404
