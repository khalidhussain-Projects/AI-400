# FastAPI Validation Reference

## Table of Contents
- [Path Parameters](#path-parameters)
- [Query Parameters](#query-parameters)
- [Request Body Validation](#request-body-validation)
- [Nested Models](#nested-models)
- [Custom Validators](#custom-validators)
- [Response Models](#response-models)

---

## Path Parameters

### Basic Path Parameter
```python
@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id}
```

### Path with Validation
```python
from fastapi import Path

@app.get("/items/{item_id}")
def read_item(
    item_id: int = Path(..., gt=0, le=1000, description="Item ID must be 1-1000")
):
    return {"item_id": item_id}
```

### Enum Path Parameter
```python
from enum import Enum

class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"

@app.get("/models/{model_name}")
def get_model(model_name: ModelName):
    return {"model": model_name.value}
```

### Multiple Path Parameters
```python
@app.get("/users/{user_id}/items/{item_id}")
def read_user_item(user_id: int, item_id: int):
    return {"user_id": user_id, "item_id": item_id}
```

### Path Parameter with Regex
```python
@app.get("/files/{file_path:path}")
def read_file(file_path: str):
    return {"file_path": file_path}
```

---

## Query Parameters

### Basic Query Parameters
```python
@app.get("/items/")
def read_items(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}
```

### Required vs Optional
```python
@app.get("/items/")
def read_items(
    required_param: str,                    # Required
    optional_param: str | None = None,      # Optional
    default_param: str = "default"          # Optional with default
):
    return {"required": required_param, "optional": optional_param}
```

### Query with Validation
```python
from fastapi import Query

@app.get("/items/")
def read_items(
    q: str | None = Query(
        None,
        min_length=3,
        max_length=50,
        regex="^[a-zA-Z]+$",
        description="Search query"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    return {"q": q, "skip": skip, "limit": limit}
```

### List Query Parameters
```python
@app.get("/items/")
def read_items(tags: list[str] = Query(default=[])):
    return {"tags": tags}
# URL: /items/?tags=foo&tags=bar
```

### Alias and Deprecated
```python
@app.get("/items/")
def read_items(
    item_query: str | None = Query(None, alias="item-query"),
    old_param: str | None = Query(None, deprecated=True)
):
    return {"item_query": item_query}
```

---

## Request Body Validation

### Basic Pydantic Model
```python
from pydantic import BaseModel, Field

class Item(BaseModel):
    name: str
    price: float
    description: str | None = None
    tax: float | None = None

@app.post("/items/")
def create_item(item: Item):
    return item
```

### Field Validation
```python
class Item(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    price: float = Field(..., gt=0, description="Price must be positive")
    quantity: int = Field(default=1, ge=1, le=1000)
    tags: list[str] = Field(default_factory=list, max_length=10)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "name": "Widget",
                    "price": 29.99,
                    "quantity": 5,
                    "tags": ["electronics"]
                }
            ]
        }
    }
```

### Multiple Body Parameters
```python
class Item(BaseModel):
    name: str
    price: float

class User(BaseModel):
    username: str
    email: str

@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item, user: User):
    return {"item_id": item_id, "item": item, "user": user}
```

### Body with Embed
```python
from fastapi import Body

@app.put("/items/{item_id}")
def update_item(
    item_id: int,
    item: Item = Body(..., embed=True)
):
    return {"item_id": item_id, "item": item}
# Expects: {"item": {"name": "...", "price": ...}}
```

### Single Values in Body
```python
@app.put("/items/{item_id}")
def update_item(
    item_id: int,
    item: Item,
    importance: int = Body(..., gt=0)
):
    return {"item_id": item_id, "item": item, "importance": importance}
```

---

## Nested Models

### Basic Nesting
```python
class Address(BaseModel):
    street: str
    city: str
    country: str
    zip_code: str = Field(..., pattern=r"^\d{5}(-\d{4})?$")

class User(BaseModel):
    name: str
    email: str
    address: Address
```

### List of Nested Models
```python
class OrderItem(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    price: float = Field(..., gt=0)

class Order(BaseModel):
    user_id: int
    items: list[OrderItem]
    total: float | None = None
```

### Deeply Nested Structures
```python
class Image(BaseModel):
    url: str
    name: str

class Item(BaseModel):
    name: str
    images: list[Image] | None = None

class Offer(BaseModel):
    name: str
    items: list[Item]
```

### Dict with Typed Values
```python
class Weights(BaseModel):
    __root__: dict[str, float]

# Or in Pydantic v2:
@app.post("/weights/")
def create_weights(weights: dict[str, float]):
    return {"weights": weights}
```

### Self-Referencing Models
```python
from typing import ForwardRef

class Category(BaseModel):
    name: str
    subcategories: list["Category"] = []

Category.model_rebuild()
```

---

## Custom Validators

### Field Validators (Pydantic v2)
```python
from pydantic import field_validator

class User(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.isalnum():
            raise ValueError("must be alphanumeric")
        return v

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("invalid email format")
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v
```

### Model Validators
```python
from pydantic import model_validator

class DateRange(BaseModel):
    start_date: date
    end_date: date

    @model_validator(mode="after")
    def check_dates(self) -> "DateRange":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be after start_date")
        return self
```

### Computed Fields
```python
from pydantic import computed_field

class Rectangle(BaseModel):
    width: float
    height: float

    @computed_field
    @property
    def area(self) -> float:
        return self.width * self.height
```

### Custom Types
```python
from typing import Annotated
from pydantic import AfterValidator

def validate_positive(v: int) -> int:
    if v <= 0:
        raise ValueError("must be positive")
    return v

PositiveInt = Annotated[int, AfterValidator(validate_positive)]

class Item(BaseModel):
    quantity: PositiveInt
```

---

## Response Models

### Basic Response Model
```python
class ItemOut(BaseModel):
    name: str
    price: float
    # Note: no 'password' or sensitive fields

@app.post("/items/", response_model=ItemOut)
def create_item(item: ItemIn):
    return item  # Extra fields filtered automatically
```

### Response Model Exclude
```python
class User(BaseModel):
    username: str
    email: str
    password: str

@app.get("/users/{user_id}", response_model=User, response_model_exclude={"password"})
def read_user(user_id: int):
    return get_user(user_id)
```

### Multiple Response Types
```python
from typing import Union

class Cat(BaseModel):
    name: str
    meows: bool

class Dog(BaseModel):
    name: str
    barks: bool

@app.get("/animals/{animal_id}", response_model=Union[Cat, Dog])
def get_animal(animal_id: int):
    return get_animal_from_db(animal_id)
```

### List Response
```python
@app.get("/items/", response_model=list[Item])
def read_items():
    return [Item(name="Item1", price=10), Item(name="Item2", price=20)]
```

### Status Code Specific Responses
```python
from fastapi import status
from fastapi.responses import JSONResponse

@app.post("/items/", status_code=status.HTTP_201_CREATED)
def create_item(item: Item):
    return item

@app.get("/items/{item_id}")
def read_item(item_id: int):
    item = get_item(item_id)
    if not item:
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    return item
```

### OpenAPI Response Documentation
```python
from fastapi import HTTPException

@app.get(
    "/items/{item_id}",
    responses={
        200: {"description": "Item found", "model": Item},
        404: {"description": "Item not found"},
        422: {"description": "Validation error"}
    }
)
def read_item(item_id: int):
    item = get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item
```
