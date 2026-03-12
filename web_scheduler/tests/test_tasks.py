def _create_task(client):
    payload = {
        "name": "daily_python_report",
        "description": "python report task",
        "task_type": "python",
        "schedule_type": "manual",
        "python_code": "print('hello')",
        "params_json": '{"region": "KR"}',
        "output_format": "json",
    }
    response = client.post("/tasks", json=payload)
    assert response.status_code == 201
    return response.json()


def test_create_task(client):
    task = _create_task(client)
    assert task["id"] > 0
    assert task["name"] == "daily_python_report"


def test_list_tasks(client):
    _create_task(client)

    response = client.get("/tasks")
    assert response.status_code == 200
    data = response.json()

    assert len(data) == 1
    assert data[0]["name"] == "daily_python_report"


def test_update_task(client):
    task = _create_task(client)

    response = client.put(
        f"/tasks/{task['id']}",
        json={"description": "updated description", "is_enabled": False},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["description"] == "updated description"
    assert body["is_enabled"] is False


def test_delete_task(client):
    task = _create_task(client)

    delete_response = client.delete(f"/tasks/{task['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json()["message"] == "Task deleted successfully"

    get_response = client.get(f"/tasks/{task['id']}")
    assert get_response.status_code == 404
