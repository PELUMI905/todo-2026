# Todo App

A complete API-only task manager built with FastAPI, SQLAlchemy, SQLite, and JWT authentication.

## Features

- User registration and login
- Hashed passwords and JWT access tokens
- Create, view, edit, and delete tasks
- Mark tasks as completed
- Task due dates and priorities (`low`, `medium`, `high`)
- Filter tasks by `all`, `pending`, or `completed`
- Search task titles and descriptions
- Pagination using `skip` and `limit`
- Each user can only access their own tasks
- Request validation and useful HTTP errors
- Interactive API docs and health check

## Run on Windows

Open a terminal in the `Todo App` folder.

### 1. Create a virtual environment

```bat
py -m venv venv
```

### 2. Activate it

Command Prompt:

```bat
venv\Scripts\activate.bat
```

PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bat
python -m pip install -r requirements.txt
```

### 4. Configure environment variables

Copy `.env.example` to a new file named `.env`. Change `SECRET_KEY` to a long random secret. Do not upload `.env` to GitHub.

### 5. Start the API

```bat
python -m uvicorn main:app --reload
```

### 6. Open the documentation

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health check: http://127.0.0.1:8000/health

## Suggested API usage

1. Use `POST /api/auth/register/` to create an account. Send JSON:
   `{"username":"pelumi","email":"pelumi@example.com","password":"StrongPass123!"}`
2. Use `POST /api/auth/login/` with form fields `username` and `password`.
3. Copy the returned `access_token`.
4. In Swagger, click **Authorize** and enter the username/password, or use the token as `Bearer <token>` in the Authorization header.
5. Try the task endpoints.

## Task filters

- All tasks: `GET /tasks/?status=all`
- Pending tasks: `GET /tasks/?status=pending`
- Completed tasks: `GET /tasks/?status=completed`
- High priority: `GET /tasks/?priority=high`
- Search: `GET /tasks/?search=meeting`
- Pagination: `GET /tasks/?skip=0&limit=10`

Filters can be combined, for example:
`/tasks/?status=pending&priority=high&skip=0&limit=10`

## Security note

The default secret in the code is for local learning only. Set a strong secret in `.env` before using this outside your own computer. This project is a learning baseline, not a production security review.
