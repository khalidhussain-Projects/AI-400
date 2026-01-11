# FastAPI Key Dependencies Reference

## Table of Contents
- [Starlette](#starlette)
- [Pydantic](#pydantic)
- [Uvicorn](#uvicorn)
- [Additional Dependencies](#additional-dependencies)

---

## Starlette

FastAPI is built on top of Starlette, an ASGI framework providing the core web functionality.

### What Starlette Provides
- Request and Response handling
- WebSocket support
- Background tasks
- Middleware system
- Routing
- Static files serving
- Test client

### Using Starlette Features Directly

#### Middleware
```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        import time
        start = time.time()
        response = await call_next(request)
        duration = time.time() - start
        response.headers["X-Process-Time"] = str(duration)
        return response

app.add_middleware(TimingMiddleware)
```

#### Static Files
```python
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")
```

#### Custom Responses
```python
from starlette.responses import (
    HTMLResponse,
    PlainTextResponse,
    RedirectResponse,
    StreamingResponse,
    FileResponse
)

@app.get("/html", response_class=HTMLResponse)
def get_html():
    return "<html><body><h1>Hello</h1></body></html>"

@app.get("/redirect")
def redirect():
    return RedirectResponse(url="/target")

@app.get("/file")
def get_file():
    return FileResponse("path/to/file.pdf", filename="download.pdf")
```

#### Routing
```python
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1", tags=["v1"])

@router.get("/items/")
def read_items():
    return []

app.include_router(router)
```

---

## Pydantic

Pydantic handles data validation, serialization, and settings management.

### Core Features Used by FastAPI
- Request body validation
- Response serialization
- OpenAPI schema generation
- Settings management

### Model Configuration (Pydantic v2)
```python
from pydantic import BaseModel, ConfigDict

class User(BaseModel):
    model_config = ConfigDict(
        str_strip_whitespace=True,      # Strip whitespace from strings
        str_min_length=1,               # Minimum string length
        validate_assignment=True,        # Validate on attribute assignment
        populate_by_name=True,          # Allow population by field name or alias
        use_enum_values=True,           # Use enum values instead of enum objects
        extra="forbid"                  # Forbid extra fields
    )

    username: str
    email: str
```

### Serialization
```python
class Item(BaseModel):
    name: str
    price: float
    tax: float | None = None

item = Item(name="Widget", price=10.5)

# To dict
item.model_dump()  # {'name': 'Widget', 'price': 10.5, 'tax': None}
item.model_dump(exclude_none=True)  # {'name': 'Widget', 'price': 10.5}

# To JSON
item.model_dump_json()
```

### Settings Management
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_name: str = "My App"
    debug: bool = False
    database_url: str
    secret_key: str

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

settings = Settings()
```

### Generic Models
```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class Response(BaseModel, Generic[T]):
    data: T
    message: str
    success: bool = True

class User(BaseModel):
    name: str

# Usage
response: Response[User] = Response(data=User(name="John"), message="OK")
response: Response[list[User]] = Response(data=[User(name="John")], message="OK")
```

---

## Uvicorn

Uvicorn is the recommended ASGI server for running FastAPI applications.

### Basic Usage
```bash
# Development with auto-reload
uvicorn main:app --reload

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Programmatic Usage
```python
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        workers=1  # workers > 1 incompatible with reload
    )
```

### Production Configuration
```python
uvicorn.run(
    "main:app",
    host="0.0.0.0",
    port=8000,
    workers=4,
    log_level="info",
    access_log=True,
    ssl_keyfile="key.pem",
    ssl_certfile="cert.pem"
)
```

### With Gunicorn (Production)
```bash
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

---

## Additional Dependencies

### Standard Installation
```bash
pip install "fastapi[standard]"
```
Includes: uvicorn, python-multipart, email-validator, httpx, jinja2

### Common Additional Packages

| Package | Purpose | Install |
|---------|---------|---------|
| `sqlalchemy` | Database ORM | `pip install sqlalchemy` |
| `asyncpg` | Async PostgreSQL | `pip install asyncpg` |
| `aiosqlite` | Async SQLite | `pip install aiosqlite` |
| `redis` | Redis client | `pip install redis` |
| `celery` | Task queue | `pip install celery` |
| `python-jose[cryptography]` | JWT tokens | `pip install python-jose[cryptography]` |
| `passlib[bcrypt]` | Password hashing | `pip install passlib[bcrypt]` |
| `httpx` | Async HTTP client | `pip install httpx` |
| `pytest` | Testing | `pip install pytest` |
| `pytest-asyncio` | Async testing | `pip install pytest-asyncio` |

### Database Setup Examples

#### SQLAlchemy (Sync)
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./app.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
```

#### SQLAlchemy (Async)
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/db"
engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

### Project Structure (Professional)
```
project/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app instance
│   ├── config.py            # Settings
│   ├── dependencies.py      # Shared dependencies
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py    # API router
│   │   │   └── endpoints/
│   │   │       ├── users.py
│   │   │       └── items.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── security.py      # Auth logic
│   │   └── exceptions.py    # Custom exceptions
│   ├── models/
│   │   ├── __init__.py
│   │   └── user.py          # SQLAlchemy models
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── user.py          # Pydantic schemas
│   ├── crud/
│   │   ├── __init__.py
│   │   └── user.py          # Database operations
│   └── services/
│       └── email.py         # Business logic
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── test_users.py
├── alembic/                  # Migrations
├── requirements.txt
├── .env
└── docker-compose.yml
```
