"""
Unit tests for the Task API.

Uses pytest with FastAPI's TestClient and an in-memory SQLite database
to test API endpoints without running an actual server.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from sqlmodel import SQLModel, Session, create_engine
from sqlmodel.pool import StaticPool

from main import app, get_session


# =============================================================================
# Test Database Setup
# =============================================================================
@pytest.fixture(name="session")
def session_fixture():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create a TestClient with the test database session."""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# =============================================================================
# Test: POST /tasks - Create Task
# =============================================================================
def test_create_task(client: TestClient):
    """Test creating a new task."""
    response = client.post(
        "/tasks",
        json={"title": "Buy groceries", "description": "Milk, eggs, bread"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Buy groceries"
    assert data["description"] == "Milk, eggs, bread"
    assert "id" in data


def test_create_task_without_description(client: TestClient):
    """Test creating a task without a description."""
    response = client.post(
        "/tasks",
        json={"title": "Simple task"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Simple task"
    assert data["description"] is None


def test_create_task_missing_title(client: TestClient):
    """Test that creating a task without a title fails with IntegrityError."""
    with pytest.raises(IntegrityError):
        client.post(
            "/tasks",
            json={"description": "No title provided"}
        )


# =============================================================================
# Test: GET /tasks - Get All Tasks
# =============================================================================
def test_get_tasks_empty(client: TestClient):
    """Test getting tasks when none exist."""
    response = client.get("/tasks")

    assert response.status_code == 200
    assert response.json() == []


def test_get_tasks_returns_list(client: TestClient):
    """Test that /tasks returns a list of tasks."""
    # Create some tasks first
    client.post("/tasks", json={"title": "Task 1"})
    client.post("/tasks", json={"title": "Task 2"})

    response = client.get("/tasks")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_get_tasks_returns_correct_data(client: TestClient):
    """Test that tasks contain correct fields."""
    client.post("/tasks", json={"title": "Test Task", "description": "Test Desc"})

    response = client.get("/tasks")
    data = response.json()

    assert len(data) == 1
    task = data[0]
    assert "id" in task
    assert task["title"] == "Test Task"
    assert task["description"] == "Test Desc"


# =============================================================================
# Test: GET /tasks/{task_id} - Get Single Task
# =============================================================================
def test_get_task_by_id(client: TestClient):
    """Test getting a specific task by ID."""
    # Create a task
    create_response = client.post(
        "/tasks",
        json={"title": "Specific Task", "description": "Find me"}
    )
    task_id = create_response.json()["id"]

    # Get the task
    response = client.get(f"/tasks/{task_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task_id
    assert data["title"] == "Specific Task"


def test_get_task_not_found(client: TestClient):
    """Test getting a task that doesn't exist."""
    response = client.get("/tasks/999")

    assert response.status_code == 200
    assert response.json() is None


# =============================================================================
# Test: PATCH /tasks/{task_id} - Partial Update Task
# =============================================================================
def test_patch_task_title(client: TestClient):
    """Test partially updating only the title."""
    # Create a task
    create_response = client.post(
        "/tasks",
        json={"title": "Original Title", "description": "Original Desc"}
    )
    task_id = create_response.json()["id"]

    # Patch only the title
    response = client.patch(
        f"/tasks/{task_id}",
        json={"title": "Updated Title"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Title"
    assert data["description"] == "Original Desc"


def test_patch_task_description(client: TestClient):
    """Test partially updating only the description."""
    # Create a task
    create_response = client.post(
        "/tasks",
        json={"title": "Keep This", "description": "Change Me"}
    )
    task_id = create_response.json()["id"]

    # Patch only the description
    response = client.patch(
        f"/tasks/{task_id}",
        json={"title": "Keep This", "description": "New Description"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Keep This"
    assert data["description"] == "New Description"


def test_patch_task_not_found(client: TestClient):
    """Test patching a task that doesn't exist."""
    response = client.patch(
        "/tasks/999",
        json={"title": "Won't Work"}
    )

    assert response.status_code == 200
    assert response.json() == {"error": "Task not found"}


# =============================================================================
# Test: PUT /tasks/{task_id} - Full Update Task
# =============================================================================
def test_update_task(client: TestClient):
    """Test fully updating a task."""
    # Create a task
    create_response = client.post(
        "/tasks",
        json={"title": "Old Title", "description": "Old Desc"}
    )
    task_id = create_response.json()["id"]

    # Update the task
    response = client.put(
        f"/tasks/{task_id}",
        json={"title": "New Title", "description": "New Desc"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "New Title"
    assert data["description"] == "New Desc"


def test_update_task_not_found(client: TestClient):
    """Test updating a task that doesn't exist."""
    response = client.put(
        "/tasks/999",
        json={"title": "Won't Work", "description": "Nope"}
    )

    assert response.status_code == 200
    assert response.json() == {"error": "Task not found"}


# =============================================================================
# Test: DELETE /tasks/{task_id} - Delete Task
# =============================================================================
def test_delete_task(client: TestClient):
    """Test deleting a task."""
    # Create a task
    create_response = client.post(
        "/tasks",
        json={"title": "Delete Me"}
    )
    task_id = create_response.json()["id"]

    # Delete the task
    response = client.delete(f"/tasks/{task_id}")

    assert response.status_code == 200
    assert response.json() == {"message": "Task deleted successfully"}

    # Verify it's gone
    get_response = client.get(f"/tasks/{task_id}")
    assert get_response.json() is None


def test_delete_task_not_found(client: TestClient):
    """Test deleting a task that doesn't exist."""
    response = client.delete("/tasks/999")

    assert response.status_code == 200
    assert response.json() == {"error": "Task not found"}


# =============================================================================
# Test: Task Field Validation
# =============================================================================
def test_task_id_is_integer(client: TestClient):
    """Test that task IDs are integers."""
    client.post("/tasks", json={"title": "Test"})
    response = client.get("/tasks")

    for task in response.json():
        assert isinstance(task["id"], int)


def test_task_title_is_string(client: TestClient):
    """Test that task titles are strings."""
    client.post("/tasks", json={"title": "String Title"})
    response = client.get("/tasks")

    for task in response.json():
        assert isinstance(task["title"], str)
