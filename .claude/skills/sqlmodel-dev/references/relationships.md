# SQLModel Relationships

## Table of Contents
- [One-to-Many Relationships](#one-to-many-relationships)
- [Many-to-Many Relationships](#many-to-many-relationships)
- [Self-Referential Relationships](#self-referential-relationships)
- [Cascade Delete](#cascade-delete)
- [Lazy Loading vs Eager Loading](#lazy-loading-vs-eager-loading)

## One-to-Many Relationships

A team has many heroes; a hero belongs to one team.

```python
from sqlmodel import Field, Relationship, SQLModel

class Team(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    headquarters: str

    heroes: list["Hero"] = Relationship(back_populates="team")

class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    secret_name: str

    team_id: int | None = Field(default=None, foreign_key="team.id")
    team: Team | None = Relationship(back_populates="heroes")
```

### Usage
```python
# Create with relationship
team = Team(name="Avengers", headquarters="NYC")
hero = Hero(name="Spider-Man", secret_name="Peter Parker", team=team)

session.add(hero)
session.commit()

# Access relationship
print(hero.team.name)  # "Avengers"
print(team.heroes)     # [Hero(...)]
```

### API Models for Relationships
```python
class TeamRead(SQLModel):
    id: int
    name: str
    headquarters: str

class HeroRead(SQLModel):
    id: int
    name: str
    team: TeamRead | None = None

class TeamReadWithHeroes(SQLModel):
    id: int
    name: str
    heroes: list[HeroRead] = []
```

## Many-to-Many Relationships

Heroes can belong to multiple teams; teams have multiple heroes.

```python
class HeroTeamLink(SQLModel, table=True):
    """Link table for many-to-many relationship"""
    hero_id: int | None = Field(
        default=None, foreign_key="hero.id", primary_key=True
    )
    team_id: int | None = Field(
        default=None, foreign_key="team.id", primary_key=True
    )

class Team(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str

    heroes: list["Hero"] = Relationship(
        back_populates="teams",
        link_model=HeroTeamLink
    )

class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str

    teams: list[Team] = Relationship(
        back_populates="heroes",
        link_model=HeroTeamLink
    )
```

### Link Table with Extra Fields
```python
class HeroTeamLink(SQLModel, table=True):
    hero_id: int | None = Field(
        default=None, foreign_key="hero.id", primary_key=True
    )
    team_id: int | None = Field(
        default=None, foreign_key="team.id", primary_key=True
    )
    joined_at: datetime = Field(default_factory=datetime.utcnow)
    role: str = "member"
```

## Self-Referential Relationships

Employee reporting to another employee (manager).

```python
class Employee(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str

    manager_id: int | None = Field(default=None, foreign_key="employee.id")

    manager: "Employee | None" = Relationship(
        back_populates="subordinates",
        sa_relationship_kwargs={"remote_side": "Employee.id"}
    )
    subordinates: list["Employee"] = Relationship(back_populates="manager")
```

## Cascade Delete

Delete related records when parent is deleted.

```python
from sqlalchemy import Column
from sqlalchemy.orm import relationship

class Team(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str

    heroes: list["Hero"] = Relationship(
        back_populates="team",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )

class Hero(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str
    team_id: int | None = Field(
        default=None,
        foreign_key="team.id",
        ondelete="CASCADE"  # DB-level cascade
    )
    team: Team | None = Relationship(back_populates="heroes")
```

## Lazy Loading vs Eager Loading

### Default (Lazy Loading)
```python
hero = session.get(Hero, 1)
# Team is loaded when accessed
print(hero.team.name)  # Triggers additional query
```

### Eager Loading with selectinload
```python
from sqlalchemy.orm import selectinload

statement = select(Hero).options(selectinload(Hero.team))
heroes = session.exec(statement).all()
# Team already loaded, no additional queries
for hero in heroes:
    print(hero.team.name)
```

### Eager Loading with joinedload
```python
from sqlalchemy.orm import joinedload

statement = select(Hero).options(joinedload(Hero.team))
heroes = session.exec(statement).unique().all()
```

### When to Use Which
| Pattern | Use Case |
|---------|----------|
| `selectinload` | Loading collections (one-to-many) |
| `joinedload` | Loading single objects (many-to-one) |
| Lazy (default) | When relationship rarely accessed |
