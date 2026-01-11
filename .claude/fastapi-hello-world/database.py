"""
Database configuration for SQLModel.

This file sets up:
1. The database engine (connection to SQLite)
2. A session dependency for FastAPI endpoints
"""

from sqlmodel import Session, SQLModel, create_engine

# DATABASE URL
# - "sqlite:///" means we're using SQLite
# - "./database.db" is the file where data will be stored
# - For PostgreSQL, it would be: "postgresql://user:password@localhost/dbname"
DATABASE_URL = "sqlite:///./database.db"

# CREATE ENGINE
# - The engine is the "home base" for the database connection
# - echo=True prints SQL statements to console (helpful for learning!)
# - connect_args={"check_same_thread": False} is needed for SQLite with FastAPI
engine = create_engine(
    DATABASE_URL,
    echo=True,  # Set to False in production
    connect_args={"check_same_thread": False},
)


def create_db_and_tables():
    """
    Create all database tables defined by SQLModel models.

    This reads all classes with `table=True` and creates the corresponding
    tables in the database if they don't exist.
    """
    SQLModel.metadata.create_all(engine)


def get_session():
    """
    Dependency that provides a database session to FastAPI endpoints.

    HOW IT WORKS:
    1. Creates a new Session when an endpoint is called
    2. The endpoint uses the session to interact with the database
    3. After the endpoint finishes, the session is automatically closed

    The 'yield' keyword makes this a generator, which FastAPI uses
    to manage the session lifecycle (open -> use -> close).
    """
    with Session(engine) as session:
        yield session
