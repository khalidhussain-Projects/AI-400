#!/usr/bin/env python3
"""
Initialize a SQLModel + FastAPI project structure.

Usage:
    python scripts/init_project.py <project_name> [--async] [--alembic]

Examples:
    python scripts/init_project.py myapp
    python scripts/init_project.py myapp --async
    python scripts/init_project.py myapp --async --alembic
"""

import argparse
import os
from pathlib import Path

def create_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"  Created: {path}")

def init_project(name: str, use_async: bool = False, use_alembic: bool = False):
    base = Path(name)

    if base.exists():
        print(f"Error: Directory '{name}' already exists")
        return

    print(f"Creating SQLModel + FastAPI project: {name}")
    print(f"  Async: {use_async}")
    print(f"  Alembic: {use_alembic}")
    print()

    # Requirements
    requirements = """fastapi>=0.100.0
sqlmodel>=0.0.14
uvicorn[standard]>=0.23.0
python-dotenv>=1.0.0
"""
    if use_async:
        requirements += "aiosqlite>=0.19.0\nasyncpg>=0.28.0\n"
    if use_alembic:
        requirements += "alembic>=1.12.0\n"

    create_file(base / "requirements.txt", requirements)

    # .env
    env_content = """DATABASE_URL=sqlite:///./database.db
DEBUG=True
"""
    if use_async:
        env_content = """DATABASE_URL=sqlite+aiosqlite:///./database.db
DEBUG=True
"""
    create_file(base / ".env", env_content)

    # .gitignore
    gitignore = """__pycache__/
*.py[cod]
.env
*.db
.pytest_cache/
.coverage
htmlcov/
dist/
*.egg-info/
"""
    create_file(base / ".gitignore", gitignore)

    # App structure
    app_dir = base / "app"

    # __init__.py
    create_file(app_dir / "__init__.py", "")

    # models.py
    models = '''"""SQLModel database models."""
from datetime import datetime
from sqlmodel import Field, SQLModel


class TimestampMixin(SQLModel):
    """Mixin for created_at and updated_at timestamps."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Example model - replace with your own
class Item(TimestampMixin, table=True):
    """Example Item model."""
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str | None = None
    price: float = Field(ge=0)
    is_active: bool = Field(default=True)


# API Schemas
class ItemCreate(SQLModel):
    name: str
    description: str | None = None
    price: float


class ItemRead(SQLModel):
    id: int
    name: str
    description: str | None
    price: float
    is_active: bool


class ItemUpdate(SQLModel):
    name: str | None = None
    description: str | None = None
    price: float | None = None
    is_active: bool | None = None
'''
    create_file(app_dir / "models.py", models)

    # database.py (sync or async)
    if use_async:
        database = '''"""Async database configuration."""
import os
from dotenv import load_dotenv
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./database.db")

engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DEBUG", "False").lower() == "true",
)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def create_db_and_tables():
    """Create database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncSession:
    """Dependency for getting async database session."""
    async with async_session() as session:
        yield session
'''
    else:
        database = '''"""Sync database configuration."""
import os
from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    echo=os.getenv("DEBUG", "False").lower() == "true",
    connect_args=connect_args,
)


def create_db_and_tables():
    """Create database tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency for getting database session."""
    with Session(engine) as session:
        yield session
'''
    create_file(app_dir / "database.py", database)

    # main.py (sync or async)
    if use_async:
        main = '''"""FastAPI application with async SQLModel."""
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from .database import create_db_and_tables, get_session
from .models import Item, ItemCreate, ItemRead, ItemUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    await create_db_and_tables()
    yield


app = FastAPI(title="SQLModel API", lifespan=lifespan)


@app.get("/items/", response_model=list[ItemRead])
async def read_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Get all items with pagination."""
    result = await session.exec(select(Item).offset(skip).limit(limit))
    return result.all()


@app.get("/items/{item_id}", response_model=ItemRead)
async def read_item(item_id: int, session: AsyncSession = Depends(get_session)):
    """Get a single item by ID."""
    item = await session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.post("/items/", response_model=ItemRead)
async def create_item(item: ItemCreate, session: AsyncSession = Depends(get_session)):
    """Create a new item."""
    db_item = Item.model_validate(item)
    session.add(db_item)
    await session.commit()
    await session.refresh(db_item)
    return db_item


@app.patch("/items/{item_id}", response_model=ItemRead)
async def update_item(
    item_id: int,
    item: ItemUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update an existing item."""
    db_item = await session.get(Item, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    item_data = item.model_dump(exclude_unset=True)
    db_item.sqlmodel_update(item_data)
    await session.commit()
    await session.refresh(db_item)
    return db_item


@app.delete("/items/{item_id}")
async def delete_item(item_id: int, session: AsyncSession = Depends(get_session)):
    """Delete an item."""
    item = await session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await session.delete(item)
    await session.commit()
    return {"ok": True}
'''
    else:
        main = '''"""FastAPI application with sync SQLModel."""
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Session, select

from .database import create_db_and_tables, get_session
from .models import Item, ItemCreate, ItemRead, ItemUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    create_db_and_tables()
    yield


app = FastAPI(title="SQLModel API", lifespan=lifespan)


@app.get("/items/", response_model=list[ItemRead])
def read_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    session: Session = Depends(get_session),
):
    """Get all items with pagination."""
    return session.exec(select(Item).offset(skip).limit(limit)).all()


@app.get("/items/{item_id}", response_model=ItemRead)
def read_item(item_id: int, session: Session = Depends(get_session)):
    """Get a single item by ID."""
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.post("/items/", response_model=ItemRead)
def create_item(item: ItemCreate, session: Session = Depends(get_session)):
    """Create a new item."""
    db_item = Item.model_validate(item)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


@app.patch("/items/{item_id}", response_model=ItemRead)
def update_item(
    item_id: int,
    item: ItemUpdate,
    session: Session = Depends(get_session),
):
    """Update an existing item."""
    db_item = session.get(Item, item_id)
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    item_data = item.model_dump(exclude_unset=True)
    db_item.sqlmodel_update(item_data)
    session.commit()
    session.refresh(db_item)
    return db_item


@app.delete("/items/{item_id}")
def delete_item(item_id: int, session: Session = Depends(get_session)):
    """Delete an item."""
    item = session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    session.delete(item)
    session.commit()
    return {"ok": True}
'''
    create_file(app_dir / "main.py", main)

    # Tests
    tests_dir = base / "tests"
    create_file(tests_dir / "__init__.py", "")

    conftest = '''"""Pytest configuration and fixtures."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.database import get_session
from app.models import Item


@pytest.fixture(name="engine")
def engine_fixture():
    engine = create_engine(
        "sqlite://",
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
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def sample_item(session):
    item = Item(name="Test Item", description="A test item", price=9.99)
    session.add(item)
    session.commit()
    session.refresh(item)
    return item
'''
    create_file(tests_dir / "conftest.py", conftest)

    test_api = '''"""API endpoint tests."""


def test_create_item(client):
    response = client.post(
        "/items/",
        json={"name": "New Item", "price": 19.99}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Item"
    assert data["price"] == 19.99
    assert "id" in data


def test_read_items(client, sample_item):
    response = client.get("/items/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == sample_item.name


def test_read_item(client, sample_item):
    response = client.get(f"/items/{sample_item.id}")
    assert response.status_code == 200
    assert response.json()["name"] == sample_item.name


def test_read_item_not_found(client):
    response = client.get("/items/999")
    assert response.status_code == 404


def test_update_item(client, sample_item):
    response = client.patch(
        f"/items/{sample_item.id}",
        json={"name": "Updated Item"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Item"


def test_delete_item(client, sample_item):
    response = client.delete(f"/items/{sample_item.id}")
    assert response.status_code == 200

    response = client.get(f"/items/{sample_item.id}")
    assert response.status_code == 404
'''
    create_file(tests_dir / "test_api.py", test_api)

    # Alembic setup
    if use_alembic:
        alembic_ini = f'''[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = sqlite:///./database.db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
'''
        create_file(base / "alembic.ini", alembic_ini)

        alembic_dir = base / "alembic"
        create_file(alembic_dir / "versions" / ".gitkeep", "")

        env_py = '''"""Alembic environment configuration."""
import os
from logging.config import fileConfig
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool
from alembic import context

from app.models import SQLModel

load_dotenv()

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = SQLModel.metadata


def get_url():
    return os.getenv("DATABASE_URL", "sqlite:///./database.db")


def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
        create_file(alembic_dir / "env.py", env_py)

        script_mako = '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
${imports if imports else ""}

revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    ${upgrades if upgrades else "pass"}


def downgrade():
    ${downgrades if downgrades else "pass"}
'''
        create_file(alembic_dir / "script.py.mako", script_mako)

    print()
    print("Project created successfully!")
    print()
    print("Next steps:")
    print(f"  cd {name}")
    print("  pip install -r requirements.txt")
    print("  uvicorn app.main:app --reload")
    print()
    print("Run tests:")
    print("  pytest")
    if use_alembic:
        print()
        print("Create migration:")
        print("  alembic revision --autogenerate -m 'Initial migration'")
        print("  alembic upgrade head")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize SQLModel + FastAPI project")
    parser.add_argument("name", help="Project name")
    parser.add_argument("--async", dest="use_async", action="store_true", help="Use async database")
    parser.add_argument("--alembic", action="store_true", help="Include Alembic migrations")

    args = parser.parse_args()
    init_project(args.name, args.use_async, args.alembic)
