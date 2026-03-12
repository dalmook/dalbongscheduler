def _create_task(client, payload):
    response = client.post("/tasks", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_cron_task_registers_scheduler_job(client):
    task = _create_task(
        client,
        {
            "name": "cron_phase3_task",
            "task_type": "html",
            "schedule_type": "cron",
            "cron_expr": "*/5 * * * *",
            "html_template": "<h1>cron</h1>",
            "is_enabled": True,
        },
    )

    jobs_res = client.get("/dashboard/jobs")
    assert jobs_res.status_code == 200
    jobs = jobs_res.json()

    job = next((item for item in jobs if item["task_id"] == task["id"]), None)
    assert job is not None
    assert job["job_id"] == f"task:{task['id']}"
    assert job["next_run_time"] is not None


def test_interval_task_registers_scheduler_job(client):
    task = _create_task(
        client,
        {
            "name": "interval_phase3_task",
            "task_type": "python",
            "schedule_type": "interval",
            "interval_seconds": 30,
            "python_code": "print('interval')",
            "is_enabled": True,
        },
    )

    jobs = client.get("/dashboard/jobs").json()
    job = next((item for item in jobs if item["task_id"] == task["id"]), None)
    assert job is not None
    assert "interval" in job["trigger"].lower()


def test_manual_task_not_registered(client):
    task = _create_task(
        client,
        {
            "name": "manual_phase3_task",
            "task_type": "python",
            "schedule_type": "manual",
            "python_code": "print('manual')",
            "is_enabled": True,
        },
    )

    jobs = client.get("/dashboard/jobs").json()
    assert all(item["task_id"] != task["id"] for item in jobs)


def test_disable_task_removes_job(client):
    task = _create_task(
        client,
        {
            "name": "disable_phase3_task",
            "task_type": "python",
            "schedule_type": "interval",
            "interval_seconds": 30,
            "python_code": "print('x')",
            "is_enabled": True,
        },
    )

    response = client.put(f"/tasks/{task['id']}", json={"is_enabled": False})
    assert response.status_code == 200

    jobs = client.get("/dashboard/jobs").json()
    assert all(item["task_id"] != task["id"] for item in jobs)


def test_update_schedule_updates_job(client):
    task = _create_task(
        client,
        {
            "name": "update_phase3_task",
            "task_type": "python",
            "schedule_type": "cron",
            "cron_expr": "*/10 * * * *",
            "python_code": "print('u')",
            "is_enabled": True,
        },
    )

    res = client.put(
        f"/tasks/{task['id']}",
        json={"schedule_type": "interval", "interval_seconds": 30, "cron_expr": None},
    )
    assert res.status_code == 200, res.text

    jobs = client.get("/dashboard/jobs").json()
    job = next((item for item in jobs if item["task_id"] == task["id"]), None)
    assert job is not None
    assert "interval" in job["trigger"].lower()


def test_dashboard_summary_jobs_html_results(client):
    task = _create_task(
        client,
        {
            "name": "dashboard_html_task",
            "task_type": "html",
            "schedule_type": "interval",
            "interval_seconds": 30,
            "html_template": "<html><body><h1>{{ title }}</h1></body></html>",
            "params_json": '{"title":"Dash"}',
            "is_enabled": True,
        },
    )
    run_res = client.post(f"/tasks/{task['id']}/run")
    assert run_res.status_code == 201

    summary = client.get("/dashboard/summary")
    assert summary.status_code == 200
    s = summary.json()
    assert s["total_tasks"] >= 1
    assert s["scheduled_tasks"] >= 1

    jobs = client.get("/dashboard/jobs")
    assert jobs.status_code == 200
    assert any(item["task_id"] == task["id"] for item in jobs.json())

    html_results = client.get("/dashboard/html-results")
    assert html_results.status_code == 200
    rows = html_results.json()
    target = next((r for r in rows if r["task_id"] == task["id"]), None)
    assert target is not None
    assert target["latest_artifact_id"] is not None
