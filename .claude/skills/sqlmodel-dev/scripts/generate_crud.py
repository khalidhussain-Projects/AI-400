#!/usr/bin/env python3
"""
Generate CRUD operations for SQLModel models.

Usage:
    python scripts/generate_crud.py <ModelName> [--async]

Examples:
    python scripts/generate_crud.py Hero
    python scripts/generate_crud.py Hero --async

Output is printed to stdout. Redirect to file as needed:
    python scripts/generate_crud.py Hero > app/crud/hero.py
"""

import argparse
import re


def to_snake_case(name: str) -> str:
    """Convert CamelCase to snake_case."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def generate_sync_crud(model_name: str) -> str:
    """Generate synchronous CRUD operations."""
    snake_name = to_snake_case(model_name)

    return f'''"""CRUD operations for {model_name}."""
from sqlmodel import Session, select

from app.models import {model_name}, {model_name}Create, {model_name}Update


def create_{snake_name}(session: Session, {snake_name}: {model_name}Create) -> {model_name}:
    """Create a new {snake_name}."""
    db_{snake_name} = {model_name}.model_validate({snake_name})
    session.add(db_{snake_name})
    session.commit()
    session.refresh(db_{snake_name})
    return db_{snake_name}


def get_{snake_name}(session: Session, {snake_name}_id: int) -> {model_name} | None:
    """Get a {snake_name} by ID."""
    return session.get({model_name}, {snake_name}_id)


def get_{snake_name}s(
    session: Session,
    skip: int = 0,
    limit: int = 100,
) -> list[{model_name}]:
    """Get all {snake_name}s with pagination."""
    return session.exec(
        select({model_name}).offset(skip).limit(limit)
    ).all()


def update_{snake_name}(
    session: Session,
    {snake_name}_id: int,
    {snake_name}: {model_name}Update,
) -> {model_name} | None:
    """Update an existing {snake_name}."""
    db_{snake_name} = session.get({model_name}, {snake_name}_id)
    if not db_{snake_name}:
        return None
    {snake_name}_data = {snake_name}.model_dump(exclude_unset=True)
    db_{snake_name}.sqlmodel_update({snake_name}_data)
    session.commit()
    session.refresh(db_{snake_name})
    return db_{snake_name}


def delete_{snake_name}(session: Session, {snake_name}_id: int) -> bool:
    """Delete a {snake_name} by ID."""
    {snake_name} = session.get({model_name}, {snake_name}_id)
    if not {snake_name}:
        return False
    session.delete({snake_name})
    session.commit()
    return True


def search_{snake_name}s(
    session: Session,
    query: str,
    field: str = "name",
    skip: int = 0,
    limit: int = 100,
) -> list[{model_name}]:
    """Search {snake_name}s by field containing query string."""
    from sqlmodel import col
    statement = (
        select({model_name})
        .where(col(getattr({model_name}, field)).contains(query))
        .offset(skip)
        .limit(limit)
    )
    return session.exec(statement).all()
'''


def generate_async_crud(model_name: str) -> str:
    """Generate asynchronous CRUD operations."""
    snake_name = to_snake_case(model_name)

    return f'''"""Async CRUD operations for {model_name}."""
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models import {model_name}, {model_name}Create, {model_name}Update


async def create_{snake_name}(
    session: AsyncSession,
    {snake_name}: {model_name}Create,
) -> {model_name}:
    """Create a new {snake_name}."""
    db_{snake_name} = {model_name}.model_validate({snake_name})
    session.add(db_{snake_name})
    await session.commit()
    await session.refresh(db_{snake_name})
    return db_{snake_name}


async def get_{snake_name}(
    session: AsyncSession,
    {snake_name}_id: int,
) -> {model_name} | None:
    """Get a {snake_name} by ID."""
    return await session.get({model_name}, {snake_name}_id)


async def get_{snake_name}s(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
) -> list[{model_name}]:
    """Get all {snake_name}s with pagination."""
    result = await session.exec(
        select({model_name}).offset(skip).limit(limit)
    )
    return result.all()


async def update_{snake_name}(
    session: AsyncSession,
    {snake_name}_id: int,
    {snake_name}: {model_name}Update,
) -> {model_name} | None:
    """Update an existing {snake_name}."""
    db_{snake_name} = await session.get({model_name}, {snake_name}_id)
    if not db_{snake_name}:
        return None
    {snake_name}_data = {snake_name}.model_dump(exclude_unset=True)
    db_{snake_name}.sqlmodel_update({snake_name}_data)
    await session.commit()
    await session.refresh(db_{snake_name})
    return db_{snake_name}


async def delete_{snake_name}(
    session: AsyncSession,
    {snake_name}_id: int,
) -> bool:
    """Delete a {snake_name} by ID."""
    {snake_name} = await session.get({model_name}, {snake_name}_id)
    if not {snake_name}:
        return False
    await session.delete({snake_name})
    await session.commit()
    return True


async def search_{snake_name}s(
    session: AsyncSession,
    query: str,
    field: str = "name",
    skip: int = 0,
    limit: int = 100,
) -> list[{model_name}]:
    """Search {snake_name}s by field containing query string."""
    from sqlmodel import col
    statement = (
        select({model_name})
        .where(col(getattr({model_name}, field)).contains(query))
        .offset(skip)
        .limit(limit)
    )
    result = await session.exec(statement)
    return result.all()
'''


def main():
    parser = argparse.ArgumentParser(
        description="Generate CRUD operations for SQLModel models"
    )
    parser.add_argument("model", help="Model name (e.g., Hero, Item, User)")
    parser.add_argument(
        "--async",
        dest="use_async",
        action="store_true",
        help="Generate async CRUD operations",
    )

    args = parser.parse_args()

    if args.use_async:
        print(generate_async_crud(args.model))
    else:
        print(generate_sync_crud(args.model))


if __name__ == "__main__":
    main()
