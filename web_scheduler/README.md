# web_scheduler

`dalbongscheduler`의 tkinter 코드와 분리된 웹 백엔드 프로젝트입니다.  
현재는 **2단계(수동 실행 + 실행 이력 + 결과물 저장)** 기준으로 구현되어 있습니다.

## 1. 프로젝트 목적

- 기존 스케줄러를 웹 구조로 전환하기 위한 백엔드 기반 구축
- 사용자가 웹에서 등록한 `python/sql/html` task를 저장하고 수동 실행
- 실행 결과를 `TaskRun`/`TaskArtifact`로 DB에 기록
- 추후 APScheduler 자동 실행, 대시보드, 권한/감사 기능을 붙일 수 있도록 구조 유지

---

## 2. 현재 구현 범위 (2단계)

### 포함
- TaskDefinition CRUD API (`/tasks`)
- 수동 실행 API (`POST /tasks/{task_id}/run`)
- 실행 이력 API (`/runs`, `/runs/{id}`, `/tasks/{task_id}/runs`)
- 결과물 API (`/artifacts`, `/artifacts/{id}`, `/tasks/{task_id}/artifacts`)
- HTML preview API (`/artifacts/{id}/preview`)
- SQLite 기본 사용, PostgreSQL 전환 가능한 설정
- APScheduler lifecycle + enabled task sync 대상 로그

### 제외(다음 단계)
- cron/interval 실제 자동 실행 등록
- 외부 DB 실제 SQL 실행(현재 mock)
- 사내 연동(메일/메신저/Oracle 등)

---

## 3. 폴더 구조

```text
web_scheduler/
  app/
    api/
      routes_health.py
      routes_tasks.py
      routes_runs.py
      routes_artifacts.py
    core/
      config.py
      logging.py
    db/
      base.py
      session.py
      models.py
      init_db.py
    runners/
      python_runner.py
      sql_runner.py
      html_runner.py
    schemas/
      common.py
      task.py
      run.py
      artifact.py
    services/
      task_service.py
      execution_service.py
      artifact_service.py
      scheduler_service.py
      exceptions.py
    utils/
      time_utils.py
    main.py
  tests/
    conftest.py
    test_health.py
    test_tasks.py
    test_runs_and_artifacts.py
  .env.example
  requirements.txt
  README.md
```

---

## 4. 데이터 모델

### TaskDefinition
- 작업 정의(코드/스케줄/상태) 저장

### TaskRun
- 작업 실행 이력 저장
- status: `queued/running/success/failed`
- started_at, finished_at, duration_ms, error_message 등 포함

### TaskArtifact
- 실행 결과물 버전 저장
- 새 artifact 저장 시 기존 `is_latest=true`는 false로 변경
- task 단위 `version_no` 자동 증가

---

## 5. 실행 흐름

1. `/tasks/{id}/run` 호출
2. `TaskRun(status=queued)` 생성
3. `running` 전환 + 시작시각 기록
4. task_type에 맞는 runner 호출
   - python: 제한된 exec + print/result 수집
   - sql: mock 실행 결과 생성
   - html: Jinja2 렌더링
5. `TaskArtifact` 생성
6. `TaskRun success/failed` 마무리
7. `TaskDefinition.last_run_status/last_run_at` 갱신

> 참고: Python runner는 현재 내부 운영/신뢰된 코드 전제를 둔 최소 제한 실행입니다.

---

## 6. 설치 및 실행

```bash
cd web_scheduler
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

- Swagger: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health

---

## 7. 환경 변수 (.env.example)

```env
APP_NAME=web_scheduler
APP_ENV=local
APP_HOST=0.0.0.0
APP_PORT=8000
DATABASE_URL=sqlite:///./web_scheduler.db
LOG_LEVEL=INFO
DEFAULT_TIMEZONE=Asia/Seoul
```

PostgreSQL 전환 예시:
```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/web_scheduler
```

---

## 8. API 요약

- `GET /health`
- `POST /tasks`
- `GET /tasks`
- `GET /tasks/{task_id}` (`include_recent_runs=true` 지원)
- `PUT /tasks/{task_id}`
- `DELETE /tasks/{task_id}`
- `POST /tasks/{task_id}/run`
- `GET /runs`
- `GET /runs/{run_id}`
- `GET /tasks/{task_id}/runs`
- `GET /artifacts`
- `GET /artifacts/{artifact_id}`
- `GET /tasks/{task_id}/artifacts`
- `GET /artifacts/{artifact_id}/preview`

---

## 9. 샘플 호출

### 9-1) Python task 생성

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "python_daily_report",
    "description": "일간 리포트",
    "task_type": "python",
    "schedule_type": "manual",
    "python_code": "print(\"hello report\")\nresult={\"summary\":\"ok\",\"artifact_type\":\"text\",\"content_text\":\"done\"}",
    "params_json": "{\"target_date\":\"2026-01-01\"}",
    "output_format": "text"
  }'
```

### 9-2) Python task 수동 실행

```bash
curl -X POST http://127.0.0.1:8000/tasks/1/run
```

### 9-3) HTML task 생성

```bash
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "name": "html_notice",
    "description": "공지 렌더링",
    "task_type": "html",
    "schedule_type": "manual",
    "html_template": "<html><body><h1>{{ title }}</h1><p>{{ body }}</p></body></html>",
    "params_json": "{\"title\":\"Hello\",\"body\":\"World\"}",
    "output_format": "html"
  }'
```

### 9-4) HTML preview 확인

1) 먼저 실행 결과 artifact id 확인
```bash
curl http://127.0.0.1:8000/tasks/2/artifacts
```

2) 브라우저에서 preview URL 접속
```text
http://127.0.0.1:8000/artifacts/{artifact_id}/preview
```

---

## 10. 테스트

```bash
pytest -q
```

검증 항목:
- health endpoint
- task CRUD
- python/html task 수동 실행
- runs/artifacts 목록 조회
- artifact preview
- 잘못된 task_id 실행 시 404

---

## 11. 다음 단계 TODO

- [ ] APScheduler 실제 cron/interval 자동 실행
- [ ] 대시보드 요약 API
- [ ] 프론트엔드 관리자 화면
- [ ] delivery channel(email/knox/webhook)
- [ ] 권한관리 / 감사로그
