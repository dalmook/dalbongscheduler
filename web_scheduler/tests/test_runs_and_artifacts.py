def _create_python_task(client):
    response = client.post(
        "/tasks",
        json={
            "name": "phase2_python_task",
            "description": "run python",
            "task_type": "python",
            "schedule_type": "manual",
            "python_code": "print('phase2')\nresult={'summary':'done','artifact_type':'text','content_text':'ok'}",
            "params_json": '{"k":"v"}',
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_html_task(client):
    response = client.post(
        "/tasks",
        json={
            "name": "phase2_html_task",
            "description": "run html",
            "task_type": "html",
            "schedule_type": "manual",
            "html_template": "<html><body><h1>{{ title }}</h1></body></html>",
            "params_json": '{"title":"Hello"}',
        },
    )
    assert response.status_code == 201
    return response.json()


def test_run_task_python_success(client):
    task = _create_python_task(client)

    run_res = client.post(f"/tasks/{task['id']}/run")
    assert run_res.status_code == 201
    body = run_res.json()
    assert body["task_id"] == task["id"]
    assert body["status"] == "success"


def test_run_task_html_success_and_preview(client):
    task = _create_html_task(client)

    run_res = client.post(f"/tasks/{task['id']}/run")
    assert run_res.status_code == 201

    artifacts = client.get("/artifacts", params={"task_id": task["id"]})
    assert artifacts.status_code == 200
    items = artifacts.json()
    assert len(items) == 1

    artifact_id = items[0]["id"]
    preview = client.get(f"/artifacts/{artifact_id}/preview")
    assert preview.status_code == 200
    assert "<h1>Hello</h1>" in preview.text


def test_list_runs_and_task_runs(client):
    task = _create_python_task(client)
    client.post(f"/tasks/{task['id']}/run")

    runs = client.get("/runs")
    assert runs.status_code == 200
    assert len(runs.json()) == 1

    task_runs = client.get(f"/tasks/{task['id']}/runs")
    assert task_runs.status_code == 200
    assert len(task_runs.json()) == 1


def test_run_invalid_task_id(client):
    response = client.post("/tasks/99999/run")
    assert response.status_code == 404
