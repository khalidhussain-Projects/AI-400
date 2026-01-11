"""
FastAPI CRUD Application with SQLModel.

CRUD stands for:
- Create: POST /items/ - Add new items
- Read:   GET /items/ and GET /items/{id} - Retrieve items
- Update: PATCH /items/{id} - Modify existing items
- Delete: DELETE /items/{id} - Remove items
"""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import Session, select

from database import create_db_and_tables, get_session
from models import Item, ItemCreate, ItemRead, ItemUpdate


# =============================================================================
# APPLICATION LIFESPAN
# =============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler - runs code on startup and shutdown.

    STARTUP (before yield):
    - Creates database tables if they don't exist

    SHUTDOWN (after yield):
    - Could add cleanup code here if needed
    """
    create_db_and_tables()
    yield


app = FastAPI(
    title="Items API",
    description="A CRUD API for managing items using FastAPI and SQLModel",
    lifespan=lifespan,
)


# =============================================================================
# ROOT ENDPOINT
# =============================================================================
@app.get("/")
def read_root():
    """Welcome endpoint."""
    return {"message": "Welcome to the Items API! Visit /docs for documentation."}


# =============================================================================
# CREATE - POST /items/
# =============================================================================
@app.post("/items/", response_model=ItemRead)
def create_item(item: ItemCreate, session: Session = Depends(get_session)):
    """
    Create a new item.

    HOW IT WORKS:
    1. FastAPI validates the request body against ItemCreate model
    2. We convert ItemCreate to Item (the database model)
    3. Add to session, commit to database, refresh to get the generated id
    4. Return the created item (FastAPI converts to ItemRead)

    DEPENDS EXPLAINED:
    - Depends(get_session) tells FastAPI to call get_session()
    - The returned session is injected into our function
    - This is called "Dependency Injection"
    """
    db_item = Item.model_validate(item)  # Convert ItemCreate -> Item
    session.add(db_item)  # Stage for insertion
    session.commit()  # Write to database
    session.refresh(db_item)  # Reload to get generated id
    return db_item


# =============================================================================
# READ ALL - GET /items/
# =============================================================================
@app.get("/items/", response_model=list[ItemRead])
def read_items(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
):
    """
    Get all items with pagination.

    QUERY PARAMETERS:
    - skip: Number of items to skip (for pagination)
    - limit: Maximum number of items to return

    EXAMPLE: GET /items/?skip=10&limit=5
    Returns items 11-15 (skip first 10, get next 5)
    """
    statement = select(Item).offset(skip).limit(limit)
    items = session.exec(statement).all()
    return items


# =============================================================================
# READ ONE - GET /items/{item_id}
# =============================================================================
@app.get("/items/{item_id}", response_model=ItemRead)
def read_item(item_id: int, session: Session = Depends(get_session)):
    """
    Get a single item by ID.

    HTTP EXCEPTION:
    - If item doesn't exist, we raise HTTPException with 404
    - 404 = "Not Found" status code
    """
    item = session.get(Item, item_id)  # Get by primary key
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


# =============================================================================
# UPDATE - PATCH /items/{item_id}
# =============================================================================
@app.patch("/items/{item_id}", response_model=ItemRead)
def update_item(
    item_id: int,
    item_update: ItemUpdate,
    session: Session = Depends(get_session),
):
    """
    Update an existing item (partial update).

    PATCH vs PUT:
    - PATCH: Partial update (only send fields you want to change)
    - PUT: Full update (must send ALL fields)

    HOW IT WORKS:
    1. Find the existing item
    2. Get only the fields that were actually sent (exclude_unset=True)
    3. Update only those fields
    4. Save to database
    """
    db_item = session.get(Item, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    # Get only the fields that were provided in the request
    item_data = item_update.model_dump(exclude_unset=True)

    # Update the database item with provided fields
    db_item.sqlmodel_update(item_data)

    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


# =============================================================================
# DELETE - DELETE /items/{item_id}
# =============================================================================
@app.delete("/items/{item_id}")
def delete_item(item_id: int, session: Session = Depends(get_session)):
    """
    Delete an item by ID.

    Returns a confirmation message, not the deleted item.
    """
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    session.delete(item)
    session.commit()
    return {"message": "Item deleted successfully", "id": item_id}
