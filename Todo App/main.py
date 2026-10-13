import os
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy import Boolean, Column, Date, ForeignKey, Integer, String, create_engine, or_
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./todo.db")
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "development-only-change-this-secret-before-deployment",
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    tasks = relationship(
        "Task",
        back_populates="owner",
        cascade="all, delete-orphan",
    )


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(120), nullable=False)
    description = Column(String(1000), nullable=True)
    completed = Column(Boolean, default=False, nullable=False)
    due_date = Column(Date, nullable=True)
    priority = Column(String(10), default="medium", nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    owner = relationship("User", back_populates="tasks")


Base.metadata.create_all(bind=engine)



class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def clean_username(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Username cannot be blank.")
        return value


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr

    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    due_date: date | None = None
    priority: Literal["low", "medium", "high"] = "medium"

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Task title cannot be blank.")
        return value

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        if value is not None:
            value = value.strip()
            return value or None
        return value


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None
    completed: bool
    due_date: date | None
    priority: str

    model_config = ConfigDict(from_attributes=True)



pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login/")


def create_access_token(username: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": username, "exp": expires_at}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise unauthorized
    except JWTError:
        raise unauthorized

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise unauthorized
    return user


app = FastAPI(
    title="Todo App API",
    description=(
        "A task manager API with registration, login, JWT authentication, "
        "task CRUD, completion, due dates, priorities, search, filtering, and pagination."
    ),
    version="1.0.0",
)


@app.get("/", tags=["General"])
def home():
    return {
        "message": "Todo API is working!",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["General"])
def health_check():
    return {"status": "healthy"}



@app.post(
    "/api/auth/register/",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Authentication"],
)
def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    username = user_data.username.strip()
    email = str(user_data.email).strip().lower()

    existing_user = db.query(User).filter(
        or_(User.username == username, User.email == email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username or email already registered.",
        )

    user = User(
        username=username,
        email=email,
        hashed_password=pwd_context.hash(user_data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@app.post("/api/auth/login/", tags=["Authentication"])
def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == form_data.username).first()

    if user is None or not pwd_context.verify(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": create_access_token(user.username),
        "token_type": "bearer",
    }


@app.get(
    "/api/auth/me/",
    response_model=UserResponse,
    tags=["Authentication"],
)
def get_my_account(current_user: User = Depends(get_current_user)):
    return current_user



@app.post(
    "/tasks/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Tasks"],
)
def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = Task(
        title=task_data.title,
        description=task_data.description,
        due_date=task_data.due_date,
        priority=task_data.priority,
        owner_id=current_user.id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.get(
    "/tasks/",
    response_model=list[TaskResponse],
    tags=["Tasks"],
)
def get_tasks(
    task_status: Literal["all", "pending", "completed"] = Query(
        default="all", alias="status"
    ),
    priority: Literal["low", "medium", "high"] | None = None,
    search: str | None = Query(default=None, max_length=120),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Task).filter(Task.owner_id == current_user.id)

    if task_status == "pending":
        query = query.filter(Task.completed.is_(False))
    elif task_status == "completed":
        query = query.filter(Task.completed.is_(True))

    if priority:
        query = query.filter(Task.priority == priority)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(Task.title.ilike(term), Task.description.ilike(term))
        )

    return (
        query.order_by(Task.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@app.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    tags=["Tasks"],
)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.owner_id == current_user.id,
    ).first()

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")
    return task


@app.put(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    tags=["Tasks"],
)
def update_task(
    task_id: int,
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.owner_id == current_user.id,
    ).first()

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")

    task.title = task_data.title
    task.description = task_data.description
    task.due_date = task_data.due_date
    task.priority = task_data.priority

    db.commit()
    db.refresh(task)
    return task


@app.delete("/tasks/{task_id}", tags=["Tasks"])
def delete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.owner_id == current_user.id,
    ).first()

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")

    db.delete(task)
    db.commit()
    return {"message": "Task deleted successfully."}


@app.patch(
    "/tasks/{task_id}/complete",
    response_model=TaskResponse,
    tags=["Tasks"],
)
def complete_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.query(Task).filter(
        Task.id == task_id,
        Task.owner_id == current_user.id,
    ).first()

    if task is None:
        raise HTTPException(status_code=404, detail="Task not found.")

    task.completed = True
    db.commit()
    db.refresh(task)
    return task
