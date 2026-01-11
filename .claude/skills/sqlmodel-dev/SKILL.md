---
name: sqlmodel-dev
description: SQLModel development assistant for building FastAPI applications with SQL databases. Use when creating, modifying, or debugging SQLModel models and database operations. Covers model definition, CRUD operations, relationships (one-to-many, many-to-many), async/sync patterns, FastAPI integration, dependency injection, Alembic migrations, and testing. Triggers on SQLModel-related tasks, database modeling, or when user mentions SQLModel, database models, or building FastAPI apps with SQL databases.
---

# SQLModel Development

Build FastAPI applications with SQLModel ORM combining SQLAlchemy + Pydantic.

## Quick Start

### Installation
```bash
pip install sqlmodel
# For async support
pip install aiosqlite  # SQLite async
pip install asyncpg    # PostgreSQL async
# For migrations
pip install alembic
```

### Basic Model
```python
from sqlmodel import Field, SQLModel

class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    secret_name: str
    age: int | None = Field(default=None, index=True)
```

### Database Setup
```python
from sqlmodel import create_engine, SQLModel

# SQLite (development)
engine = create_engine("sqlite:///database.db", echo=True)

# PostgreSQL (production)
engine = create_engine("postgresql://user:pass@localhost/db")

# MySQL
engine = create_engine("mysql+pymysql://user:pass@localhost/db")

SQLModel.metadata.create_all(engine)
```

## Core Patterns

### Model Types

| Type | Usage | Example |
|------|-------|---------|
| **Table Model** | `table=True` | Database table with columns |
| **Data Model** | No `table` param | Pydantic model for API schemas |

```python
# Table model (DB)
class HeroDB(SQLModel, table=True):
    __tablename__ = "heroes"
    id: int | None = Field(default=None, primary_key=True)
    name: str
    secret_name: str

# Data models (API)
class HeroCreate(SQLModel):
    name: str
    secret_name: str

class HeroRead(SQLModel):
    id: int
    name: str

class HeroUpdate(SQLModel):
    name: str | None = None
    secret_name: str | None = None
```

### CRUD Operations

```python
from sqlmodel import Session, select

# CREATE
def create_hero(session: Session, hero: HeroCreate) -> HeroDB:
    db_hero = HeroDB.model_validate(hero)
    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)
    return db_hero

# READ
def get_hero(session: Session, hero_id: int) -> HeroDB | None:
    return session.get(HeroDB, hero_id)

def get_heroes(session: Session, skip: int = 0, limit: int = 100) -> list[HeroDB]:
    return session.exec(select(HeroDB).offset(skip).limit(limit)).all()

# UPDATE
def update_hero(session: Session, hero_id: int, hero: HeroUpdate) -> HeroDB | None:
    db_hero = session.get(HeroDB, hero_id)
    if db_hero:
        hero_data = hero.model_dump(exclude_unset=True)
        db_hero.sqlmodel_update(hero_data)
        session.commit()
        session.refresh(db_hero)
    return db_hero

# DELETE
def delete_hero(session: Session, hero_id: int) -> bool:
    hero = session.get(HeroDB, hero_id)
    if hero:
        session.delete(hero)
        session.commit()
        return True
    return False
```

### Query Patterns

```python
from sqlmodel import select, or_, col

# Filter
statement = select(Hero).where(Hero.age >= 18)

# Multiple conditions
statement = select(Hero).where(Hero.age >= 18, Hero.name != "Admin")

# OR condition
statement = select(Hero).where(or_(Hero.age < 18, Hero.age > 65))

# LIKE pattern
statement = select(Hero).where(col(Hero.name).contains("man"))

# Order and limit
statement = select(Hero).order_by(Hero.name).limit(10)

# Execute
results = session.exec(statement).all()
first = session.exec(statement).first()
one = session.exec(statement).one()  # Raises if not exactly one
```

## FastAPI Integration

### Session Dependency (Sync)
```python
from fastapi import Depends, FastAPI
from sqlmodel import Session

def get_session():
    with Session(engine) as session:
        yield session

@app.get("/heroes/{hero_id}")
def read_hero(hero_id: int, session: Session = Depends(get_session)):
    hero = session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    return hero
```

### Response Models
```python
@app.get("/heroes/", response_model=list[HeroRead])
def read_heroes(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    return session.exec(select(Hero).offset(skip).limit(limit)).all()

@app.post("/heroes/", response_model=HeroRead)
def create_hero(hero: HeroCreate, session: Session = Depends(get_session)):
    db_hero = Hero.model_validate(hero)
    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)
    return db_hero
```

## References

For detailed patterns, see:

- **[references/relationships.md](references/relationships.md)** - One-to-many, many-to-many relationships with `Relationship()` and `back_populates`
- **[references/async-patterns.md](references/async-patterns.md)** - Async engine, sessions, and FastAPI integration
- **[references/alembic-migrations.md](references/alembic-migrations.md)** - Database migrations setup and workflows
- **[references/testing.md](references/testing.md)** - Testing patterns with pytest and test databases

## Scripts

- `scripts/init_project.py` - Initialize SQLModel + FastAPI project structure
- `scripts/generate_crud.py` - Generate CRUD operations from model definition

## Common Patterns

### Environment-Based Database URL
```python
import os
from sqlmodel import create_engine

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./dev.db"  # Default for development
)

# Handle Heroku-style postgres:// URLs
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL, echo=os.getenv("DEBUG", False))
```

### Soft Delete Pattern
```python
from datetime import datetime

class BaseModel(SQLModel):
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: datetime | None = None

class Hero(BaseModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str

# Query only active records
active_heroes = session.exec(
    select(Hero).where(Hero.deleted_at == None)
).all()
```

### Pagination Response
```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

def paginate(session: Session, query, page: int = 1, size: int = 10):
    total = session.exec(select(func.count()).select_from(query.subquery())).one()
    items = session.exec(query.offset((page - 1) * size).limit(size)).all()
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )
```
