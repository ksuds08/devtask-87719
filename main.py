from datetime import timedelta
from typing import List

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from auth import (
    create_access_token,
    get_current_user,
    get_db,
    get_password_hash,
    verify_password,
)
from config import get_settings
from models import Task, TaskStatus, User, init_db

settings = get_settings()

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: int
    email: EmailStr

    class Config:
        orm_mode = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TaskCreate(BaseModel):
    title: str
    status: TaskStatus = TaskStatus.TODO
    time_logged: float = 0.0


class TaskUpdate(BaseModel):
    title: str | None = None
    status: TaskStatus | None = None
    time_logged: float | None = None


class TaskRead(BaseModel):
    id: int
    title: str
    status: TaskStatus
    time_logged: float

    class Config:
        orm_mode = True


@app.on_event("startup")
async def on_startup() -> None:
    init_db()


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}


@app.post("/auth/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=user_in.email, hashed_password=get_password_hash(user_in.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/auth/login", response_model=TokenResponse)
async def login(user_in: UserCreate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    return TokenResponse(access_token=access_token)


@app.post("/tasks", response_model=TaskRead)
async def create_task(
    task_in: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = Task(
        title=task_in.title,
        status=task_in.status.value,
        time_logged=task_in.time_logged,
        owner_id=current_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.get("/tasks", response_model=List[TaskRead])
async def list_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    tasks = db.query(Task).filter(Task.owner_id == current_user.id).all()
    return tasks


@app.put("/tasks/{task_id}", response_model=TaskRead)
async def update_task(
    task_id: int,
    task_in: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task_in.title is not None:
        task.title = task_in.title
    if task_in.status is not None:
        task.status = task_in.status.value
    if task_in.time_logged is not None:
        task.time_logged = task_in.time_logged

    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id, Task.owner_id == current_user.id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()
    return None


# Static files & basic frontend routes
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/", include_in_schema=False)
async def serve_landing() -> FileResponse:
    return FileResponse("static/index.html")


@app.get("/dashboard", include_in_schema=False)
async def serve_dashboard() -> FileResponse:
    return FileResponse("static/dashboard.html")


@app.get("/login", include_in_schema=False)
async def serve_login() -> FileResponse:
    return FileResponse("static/login.html")


@app.get("/signup", include_in_schema=False)
async def serve_signup() -> FileResponse:
    return FileResponse("static/signup.html")
