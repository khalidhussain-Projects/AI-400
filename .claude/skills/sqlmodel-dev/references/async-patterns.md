# SQLModel Async Patterns

## Table of Contents
- [Async Engine Setup](#async-engine-setup)
- [Async Session](#async-session)
- [FastAPI Async Integration](#fastapi-async-integration)
- [Async CRUD Operations](#async-crud-operations)
- [Async Relationships](#async-relationships)

## Async Engine Setup

### Installation
```bash
pip install aiosqlite    # SQLite async driver
pip install asyncpg      # PostgreSQL async driver
pip install aiomysql     # MySQL async driver
```

### Engine Configuration
```python
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine

# SQLite (development)
DATABASE_URL = "sqlite+aiosqlite:///./database.db"

# PostgreSQL (production)
DATABASE_URL = "postgresql+asyncpg://user:pass@localhost/db"

# MySQL
DATABASE_URL = "mysql+aiomysql://user:pass@localhost/db"

engine = create_async_engine(DATABASE_URL, echo=True)
```

### Create Tables (Async)
```python
async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
```

## Async Session

```python
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session
```

## FastAPI Async Integration

### Lifespan Event
```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)
```

### Async Dependency
```python
from fastapi import Depends

async def get_async_session() -> AsyncSession:
    async with async_session() as session:
        yield session

@app.get("/heroes/{hero_id}")
async def read_hero(
    hero_id: int,
    session: AsyncSession = Depends(get_async_session)
):
    hero = await session.get(Hero, hero_id)
    if not hero:
        raise HTTPException(status_code=404, detail="Hero not found")
    return hero
```

## Async CRUD Operations

```python
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

# CREATE
async def create_hero(session: AsyncSession, hero: HeroCreate) -> Hero:
    db_hero = Hero.model_validate(hero)
    session.add(db_hero)
    await session.commit()
    await session.refresh(db_hero)
    return db_hero

# READ
async def get_hero(session: AsyncSession, hero_id: int) -> Hero | None:
    return await session.get(Hero, hero_id)

async def get_heroes(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100
) -> list[Hero]:
    result = await session.exec(
        select(Hero).offset(skip).limit(limit)
    )
    return result.all()

# UPDATE
async def update_hero(
    session: AsyncSession,
    hero_id: int,
    hero: HeroUpdate
) -> Hero | None:
    db_hero = await session.get(Hero, hero_id)
    if db_hero:
        hero_data = hero.model_dump(exclude_unset=True)
        db_hero.sqlmodel_update(hero_data)
        await session.commit()
        await session.refresh(db_hero)
    return db_hero

# DELETE
async def delete_hero(session: AsyncSession, hero_id: int) -> bool:
    hero = await session.get(Hero, hero_id)
    if hero:
        await session.delete(hero)
        await session.commit()
        return True
    return False
```

## Async Relationships

### Eager Loading (Required for Async)
```python
from sqlalchemy.orm import selectinload

async def get_hero_with_team(
    session: AsyncSession,
    hero_id: int
) -> Hero | None:
    statement = (
        select(Hero)
        .where(Hero.id == hero_id)
        .options(selectinload(Hero.team))
    )
    result = await session.exec(statement)
    return result.first()

async def get_team_with_heroes(
    session: AsyncSession,
    team_id: int
) -> Team | None:
    statement = (
        select(Team)
        .where(Team.id == team_id)
        .options(selectinload(Team.heroes))
    )
    result = await session.exec(statement)
    return result.first()
```

### Full Async FastAPI Example
```python
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker, selectinload

DATABASE_URL = "sqlite+aiosqlite:///./database.db"
engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield

app = FastAPI(lifespan=lifespan)

async def get_session():
    async with async_session() as session:
        yield session

@app.get("/heroes/", response_model=list[HeroRead])
async def read_heroes(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
):
    result = await session.exec(
        select(Hero)
        .options(selectinload(Hero.team))
        .offset(skip)
        .limit(limit)
    )
    return result.all()

@app.post("/heroes/", response_model=HeroRead)
async def create_hero(
    hero: HeroCreate,
    session: AsyncSession = Depends(get_session)
):
    db_hero = Hero.model_validate(hero)
    session.add(db_hero)
    await session.commit()
    await session.refresh(db_hero)
    return db_hero
```

## Async Best Practices

| Practice | Reason |
|----------|--------|
| Always use `selectinload` for relationships | Lazy loading doesn't work in async |
| Use `expire_on_commit=False` | Prevents detached instance errors |
| Run sync operations with `run_sync` | For metadata operations |
| Use connection pooling | Better performance in production |
