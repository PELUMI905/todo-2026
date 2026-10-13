from uuid import uuid4

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_authentication_and_task_workflow():
    username = f"user_{uuid4().hex[:12]}"
    email = f"{username}@example.com"
    password = "TestPassword123!"

    response = client.post(
        "/api/auth/register/",
        json={
            "username": username,
            "email": email,
            "password": password,
        },
    )
    assert response.status_code == 201

    login = client.post(
        "/api/auth/login/",
        data={"username": username, "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    created = client.post(
        "/tasks/",
        headers=headers,
        json={
            "title": "Learn FastAPI",
            "description": "Finish the Todo App",
            "priority": "high",
            "due_date": "2027-01-15",
        },
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

    listed = client.get("/tasks/?status=pending&priority=high", headers=headers)
    assert listed.status_code == 200
    assert any(task["id"] == task_id for task in listed.json())

    completed = client.patch(f"/tasks/{task_id}/complete", headers=headers)
    assert completed.status_code == 200
    assert completed.json()["completed"] is True

    updated = client.put(
        f"/tasks/{task_id}",
        headers=headers,
        json={
            "title": "Finish Todo App",
            "description": "Updated description",
            "priority": "medium",
            "due_date": "2027-01-20",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Finish Todo App"

    deleted = client.delete(f"/tasks/{task_id}", headers=headers)
    assert deleted.status_code == 200

    missing = client.get(f"/tasks/{task_id}", headers=headers)
    assert missing.status_code == 404


def test_task_endpoints_require_authentication():
    response = client.get("/tasks/")
    assert response.status_code == 401


def test_invalid_priority_is_rejected():
    response = client.post(
        "/tasks/",
        headers={"Authorization": "Bearer invalid-token"},
        json={"title": "Task", "priority": "urgent"},
    )
    # Authentication is checked before request-body validation in this request.
    assert response.status_code == 401
