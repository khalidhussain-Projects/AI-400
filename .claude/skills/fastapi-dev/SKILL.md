---
name: fastapi-dev
description: FastAPI development assistant for building Python APIs from hello world to production. Use when creating, modifying, or debugging FastAPI applications. Covers routing, validation (path/query/body params, Pydantic models), automatic docs (Swagger/ReDoc), dependency injection, authentication (OAuth2/JWT), WebSockets, CORS, file uploads, background tasks, testing, and project structure. Triggers on FastAPI-related tasks, API development, or when user mentions FastAPI, Pydantic, or building REST APIs with Python.
---

# FastAPI Development

Build modern, high-performance Python APIs with automatic validation and documentation.

## Quick Start

### Hello World
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None):
    return {"item_id": item_id, "q": q}
```

Run: `fastapi dev main.py` or `uvicorn main:app --reload`

Docs available at: `/docs` (Swagger UI) and `/redoc` (ReDoc)

### CRUD Example
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class Item(BaseModel):
    name: str
    price: float
    description: str | None = None

items_db: dict[int, Item] = {}

@app.post("/items/", status_code=201)
def create_item(item: Item):
    item_id = len(items_db) + 1
    items_db[item_id] = item
    return {"id": item_id, **item.model_dump()}

@app.get("/items/{item_id}")
def read_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    return items_db[item_id]

@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    items_db[item_id] = item
    return item

@app.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    del items_db[item_id]
```

## Feature Selection Guide

| Need | Solution | Reference |
|------|----------|-----------|
| Share database connections | Dependency Injection | [features.md](references/features.md#dependency-injection) |
| Run tasks after response | Background Tasks | [features.md](references/features.md#background-tasks) |
| Real-time communication | WebSockets | [features.md](references/features.md#websockets) |
| Frontend on different domain | CORS | [features.md](references/features.md#cors) |
| Accept user files | File Uploads | [features.md](references/features.md#file-uploads) |
| Protect endpoints | OAuth2/JWT | [features.md](references/features.md#oauth2--jwt-authentication) |
| Write tests | TestClient/pytest | [features.md](references/features.md#testing) |

## Validation Quick Reference

### Path Parameters
```python
from fastapi import Path

@app.get("/items/{item_id}")
def get_item(item_id: int = Path(..., gt=0, le=1000)):
    return {"item_id": item_id}
```

### Query Parameters
```python
from fastapi import Query

@app.get("/search/")
def search(
    q: str = Query(..., min_length=3, max_length=50),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, le=100)
):
    return {"q": q, "skip": skip, "limit": limit}
```

### Request Body
```python
from pydantic import BaseModel, Field, field_validator

class CreateUser(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=8)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if "@" not in v:
            raise ValueError("Invalid email")
        return v.lower()

@app.post("/users/")
def create_user(user: CreateUser):
    return user
```

For nested models, custom validators, and response models: [validation.md](references/validation.md)

## Automatic Documentation

FastAPI auto-generates OpenAPI docs from type hints:

```python
from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

app = FastAPI(
    title="My API",
    description="API for managing items",
    version="1.0.0"
)

class Item(BaseModel):
    """Item model for the store."""
    name: str = Field(..., description="Item name", examples=["Widget"])
    price: float = Field(..., gt=0, description="Item price in USD")

@app.post("/items/", summary="Create item", tags=["items"])
def create_item(item: Item):
    """
    Create a new item with:
    - **name**: required, unique name
    - **price**: required, must be positive
    """
    return item
```

Access at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Project Structure

### Simple (Single File)
```
project/
├── main.py
├── requirements.txt
└── .env
```

### Professional (Modular)
```
project/
├── app/
│   ├── __init__.py
│   ├── main.py           # App instance, middleware
│   ├── config.py         # Settings (pydantic-settings)
│   ├── dependencies.py   # Shared dependencies
│   ├── api/
│   │   └── v1/
│   │       ├── router.py
│   │       └── endpoints/
│   ├── models/           # SQLAlchemy models
│   ├── schemas/          # Pydantic schemas
│   ├── crud/             # Database operations
│   └── core/
│       ├── security.py
│       └── exceptions.py
├── tests/
├── alembic/              # Migrations
└── requirements.txt
```

## References

- **Built-in Features**: [references/features.md](references/features.md) - DI, background tasks, WebSockets, CORS, file uploads, auth, testing
- **Validation Patterns**: [references/validation.md](references/validation.md) - Path/query/body validation, nested models, custom validators
- **Dependencies & Setup**: [references/dependencies.md](references/dependencies.md) - Starlette, Pydantic, Uvicorn, project setup
