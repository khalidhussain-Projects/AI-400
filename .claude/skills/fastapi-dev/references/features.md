# FastAPI Built-in Features Reference

## Table of Contents
- [Dependency Injection](#dependency-injection)
- [Background Tasks](#background-tasks)
- [WebSockets](#websockets)
- [CORS](#cors)
- [File Uploads](#file-uploads)
- [OAuth2 & JWT Authentication](#oauth2--jwt-authentication)
- [Testing](#testing)

---

## Dependency Injection

FastAPI's DI system manages shared resources and reusable logic.

### Basic Dependency
```python
from fastapi import Depends, FastAPI

app = FastAPI()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/items/")
def read_items(db: Session = Depends(get_db)):
    return db.query(Item).all()
```

### Class-based Dependency
```python
class CommonQueryParams:
    def __init__(self, skip: int = 0, limit: int = 100, q: str | None = None):
        self.skip = skip
        self.limit = limit
        self.q = q

@app.get("/items/")
def read_items(commons: CommonQueryParams = Depends()):
    return {"skip": commons.skip, "limit": commons.limit}
```

### Nested Dependencies
```python
def get_settings():
    return Settings()

def get_db(settings: Settings = Depends(get_settings)):
    return Database(settings.db_url)

def get_user_repo(db: Database = Depends(get_db)):
    return UserRepository(db)
```

### Dependency with Yield (Context Manager)
```python
async def get_async_db():
    async with AsyncSession() as session:
        yield session
```

---

## Background Tasks

Execute tasks after returning a response.

### Basic Background Task
```python
from fastapi import BackgroundTasks

def write_log(message: str):
    with open("log.txt", "a") as f:
        f.write(f"{message}\n")

@app.post("/send-notification/")
async def send_notification(
    email: str,
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(write_log, f"Notification sent to {email}")
    return {"message": "Notification scheduled"}
```

### Multiple Background Tasks
```python
@app.post("/process/")
async def process_data(background_tasks: BackgroundTasks):
    background_tasks.add_task(task_one, arg1)
    background_tasks.add_task(task_two, arg2)
    background_tasks.add_task(task_three, arg3)
    return {"status": "processing"}
```

### Background Task with Dependency
```python
def get_background_tasks(background_tasks: BackgroundTasks):
    return background_tasks

@app.post("/items/")
async def create_item(
    item: Item,
    tasks: BackgroundTasks = Depends(get_background_tasks)
):
    tasks.add_task(log_creation, item.id)
    return item
```

---

## WebSockets

Real-time bidirectional communication.

### Basic WebSocket
```python
from fastapi import WebSocket

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(f"Echo: {data}")
```

### WebSocket with Connection Manager
```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"Client {client_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

### WebSocket with Dependencies
```python
async def get_token(websocket: WebSocket, token: str | None = Query(None)):
    if token is None:
        await websocket.close(code=1008)
        return None
    return token

@app.websocket("/ws")
async def ws_endpoint(
    websocket: WebSocket,
    token: str = Depends(get_token)
):
    await websocket.accept()
    # ... handle connection
```

---

## CORS

Cross-Origin Resource Sharing configuration.

### Basic CORS Setup
```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://myapp.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Development CORS (Allow All)
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Production CORS (Strict)
```python
origins = [
    "https://production-domain.com",
    "https://api.production-domain.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Custom-Header"],
    max_age=600,
)
```

---

## File Uploads

Handle single and multiple file uploads.

### Single File Upload
```python
from fastapi import File, UploadFile

@app.post("/uploadfile/")
async def upload_file(file: UploadFile):
    contents = await file.read()
    return {
        "filename": file.filename,
        "content_type": file.content_type,
        "size": len(contents)
    }
```

### Multiple File Uploads
```python
@app.post("/uploadfiles/")
async def upload_files(files: list[UploadFile]):
    return {"filenames": [f.filename for f in files]}
```

### File with Form Data
```python
from fastapi import Form

@app.post("/files/")
async def create_file(
    file: UploadFile,
    description: str = Form(...),
    tags: list[str] = Form(default=[])
):
    return {
        "filename": file.filename,
        "description": description,
        "tags": tags
    }
```

### Save Uploaded File
```python
import shutil
from pathlib import Path

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.post("/upload/")
async def upload(file: UploadFile):
    file_path = UPLOAD_DIR / file.filename
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    return {"path": str(file_path)}
```

### Streaming Large Files
```python
from fastapi.responses import StreamingResponse

@app.post("/upload-stream/")
async def upload_stream(file: UploadFile):
    async def generate():
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            yield chunk

    return StreamingResponse(generate(), media_type=file.content_type)
```

---

## OAuth2 & JWT Authentication

### Password Bearer Flow
```python
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(username)
    if user is None:
        raise credentials_exception
    return user

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect credentials")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
```

### Role-Based Access Control
```python
from enum import Enum

class Role(str, Enum):
    admin = "admin"
    user = "user"

def require_role(required_role: Role):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

@app.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(require_role(Role.admin))
):
    return {"deleted": user_id}
```

### API Key Authentication
```python
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Depends(api_key_header)):
    if api_key != "expected-api-key":
        raise HTTPException(status_code=403, detail="Invalid API key")
    return api_key

@app.get("/protected/")
async def protected_route(api_key: str = Depends(verify_api_key)):
    return {"status": "authenticated"}
```

---

## Testing

### Basic Test Setup
```python
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}
```

### Testing with Dependencies Override
```python
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

def test_create_item():
    response = client.post("/items/", json={"name": "Test", "price": 10.5})
    assert response.status_code == 200
```

### Async Testing with pytest-asyncio
```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_async_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/async-endpoint")
    assert response.status_code == 200
```

### Testing WebSockets
```python
def test_websocket():
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text("Hello")
        data = websocket.receive_text()
        assert data == "Echo: Hello"
```

### Testing File Uploads
```python
def test_upload_file():
    response = client.post(
        "/uploadfile/",
        files={"file": ("test.txt", b"file content", "text/plain")}
    )
    assert response.status_code == 200
    assert response.json()["filename"] == "test.txt"
```

### Testing with Authentication
```python
def test_protected_route():
    # First, get token
    response = client.post(
        "/token",
        data={"username": "testuser", "password": "testpass"}
    )
    token = response.json()["access_token"]

    # Use token
    response = client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
```

### Fixtures for Reusable Test Setup
```python
import pytest

@pytest.fixture
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def auth_headers():
    response = client.post("/token", data={"username": "test", "password": "test"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def test_authenticated_endpoint(auth_headers):
    response = client.get("/protected/", headers=auth_headers)
    assert response.status_code == 200
```
