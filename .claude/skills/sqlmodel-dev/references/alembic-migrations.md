# Alembic Migrations with SQLModel

## Table of Contents
- [Initial Setup](#initial-setup)
- [Configuration](#configuration)
- [Creating Migrations](#creating-migrations)
- [Running Migrations](#running-migrations)
- [Common Operations](#common-operations)
- [Async Migrations](#async-migrations)

## Initial Setup

### Installation
```bash
pip install alembic
```

### Initialize Alembic
```bash
alembic init alembic
```

This creates:
```
project/
├── alembic/
│   ├── versions/        # Migration files
│   ├── env.py          # Environment configuration
│   └── script.py.mako  # Migration template
└── alembic.ini         # Alembic configuration
```

## Configuration

### alembic.ini
```ini
[alembic]
script_location = alembic
sqlalchemy.url = sqlite:///./database.db

# For environment variable
# sqlalchemy.url = %(DATABASE_URL)s
```

### env.py (Sync)
```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Import your models
from app.models import SQLModel  # Your models file

config = context.config
fileConfig(config.config_file_name)

# Set target metadata
target_metadata = SQLModel.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### env.py with Environment Variables
```python
import os
from dotenv import load_dotenv

load_dotenv()

def get_url():
    return os.getenv("DATABASE_URL", "sqlite:///./database.db")

def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    # ... rest of function
```

## Creating Migrations

### Auto-Generate Migration
```bash
# After changing models
alembic revision --autogenerate -m "Add hero table"
```

### Manual Migration
```bash
alembic revision -m "Add index to name column"
```

### Migration File Structure
```python
"""Add hero table

Revision ID: abc123
Revises:
Create Date: 2024-01-15 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
import sqlmodel

revision = 'abc123'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'hero',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('secret_name', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_hero_name'), 'hero', ['name'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_hero_name'), table_name='hero')
    op.drop_table('hero')
```

## Running Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific revision
alembic upgrade abc123

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade abc123

# Rollback all
alembic downgrade base

# Show current revision
alembic current

# Show migration history
alembic history
```

## Common Operations

### Add Column
```python
def upgrade():
    op.add_column('hero', sa.Column('power_level', sa.Integer(), nullable=True))

def downgrade():
    op.drop_column('hero', 'power_level')
```

### Add Index
```python
def upgrade():
    op.create_index('ix_hero_power_level', 'hero', ['power_level'])

def downgrade():
    op.drop_index('ix_hero_power_level', table_name='hero')
```

### Add Foreign Key
```python
def upgrade():
    op.add_column('hero', sa.Column('team_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_hero_team',
        'hero', 'team',
        ['team_id'], ['id']
    )

def downgrade():
    op.drop_constraint('fk_hero_team', 'hero', type_='foreignkey')
    op.drop_column('hero', 'team_id')
```

### Rename Column
```python
def upgrade():
    op.alter_column('hero', 'name', new_column_name='hero_name')

def downgrade():
    op.alter_column('hero', 'hero_name', new_column_name='name')
```

### Data Migration
```python
from sqlalchemy.sql import table, column

def upgrade():
    hero_table = table('hero', column('power_level', sa.Integer))
    op.execute(hero_table.update().values(power_level=0))

def downgrade():
    pass  # Data migrations typically aren't reversed
```

## Async Migrations

### env.py (Async)
```python
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine

def get_url():
    url = os.getenv("DATABASE_URL", "sqlite:///./database.db")
    # Convert to async URL
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://")
    if url.startswith("sqlite://"):
        return url.replace("sqlite://", "sqlite+aiosqlite://")
    return url

def run_migrations_offline():
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
    connectable = create_async_engine(get_url(), poolclass=pool.NullPool)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

## Best Practices

| Practice | Reason |
|----------|--------|
| Always review auto-generated migrations | May miss edge cases or generate incorrect code |
| Test migrations on a copy of production data | Catch data-specific issues |
| Keep migrations small and focused | Easier to debug and rollback |
| Include both upgrade and downgrade | Enable rollback when needed |
| Use meaningful migration messages | Easier to understand history |
