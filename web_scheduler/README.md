# web_scheduler (Phase 5)

`dalbongscheduler`에서 분리한 웹 스케줄러 프로젝트입니다.

현재 단계는 **5단계: 자동 스케줄 등록 + 대시보드 API + 관리자 프론트 연동** 입니다.

## 1) 이번 단계 핵심 변경

- APScheduler가 `cron`/`interval` Task를 실제로 자동 등록/갱신/제거
- Dashboard 전용 API 제공
  - `GET /dashboard/summary`
  - `GET /dashboard/jobs`
  - `GET /dashboard/html-results`
- Frontend Dashboard / HTML Results가 위 Dashboard API를 직접 사용

## 2) 현재 구현 범위

### 백엔드
- Task CRUD API: `/tasks`
- Task preset API: `GET /tasks/presets`, `POST /tasks/bootstrap-defaults`
- 수동 실행 API: `POST /tasks/{task_id}/run`
- 실행 이력 API: `/runs`, `/runs/{run_id}`, `/tasks/{task_id}/runs`
- 결과물 API: `/artifacts`, `/artifacts/{artifact_id}`, `/tasks/{task_id}/artifacts`
- HTML Preview API: `/artifacts/{artifact_id}/preview`
- Dashboard API: `/dashboard/summary`, `/dashboard/jobs`, `/dashboard/html-results`
- Health API: `/health`

### 자동 실행 지원 범위
- `manual`: 스케줄러 등록 안 함
- `cron`: cron_expr 기반 자동 등록
- `interval`: interval_seconds 기반 자동 등록(최소 10초)

### 프론트엔드
- Dashboard
- Tasks
- Task Detail
- Runs
- HTML Results

## 3) 폴더 구조

```text
web_scheduler/
  app/                 # FastAPI backend
  tests/               # pytest tests
  frontend/            # React + Vite + TypeScript admin UI
  .env.example
  requirements.txt
  README.md
```

## 4) Windows CMD 기준 실행

### 4-1. 백엔드

```cmd
cd web_scheduler
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

- Backend: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

### 4-2. 프론트엔드

```cmd
cd web_scheduler\frontend
npm install
copy .env.example .env
npm run dev
```

- Frontend: `http://127.0.0.1:5173`

## 5) 환경변수

### 백엔드 `.env.example`
- `DATABASE_URL=sqlite:///./web_scheduler.db`
- `SQL_RUNNER_DATABASE_URL=` (비우면 DATABASE_URL 사용)
- `SQL_RUNNER_ALLOW_WRITE=false` (기본 write 차단)
- `DEFAULT_TIMEZONE=Asia/Seoul`
- `CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`

### 프론트엔드 `frontend/.env.example`
- `VITE_API_BASE_URL=http://127.0.0.1:8000`

## 6) Dashboard API 설명

### `GET /dashboard/summary`
- task/run/artifact 집계 요약
- 다음 실행 예정 task 목록
- 최근 실패 run 목록

### `GET /dashboard/jobs`
- 현재 스케줄러 등록 job 목록
- `job_id`, `task_id`, `task_name`, `trigger`, `next_run_time`, `is_enabled`

### `GET /dashboard/html-results`
- html task별 최신 결과 요약
- 최신 artifact id, preview_text, 최근 성공/실패 시각

## 7) CMD 기준 curl 예시

### 7-1. cron task 생성

```cmd
curl -X POST "http://127.0.0.1:8000/tasks" ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"daily_html_report\",\"task_type\":\"html\",\"schedule_type\":\"cron\",\"cron_expr\":\"0 9 * * *\",\"html_template\":\"<h1>{{ title }}</h1>\",\"params_json\":\"{\\\"title\\\":\\\"Daily Report\\\"}\",\"is_enabled\":true}"
```

### 7-2. interval task 생성

```cmd
curl -X POST "http://127.0.0.1:8000/tasks" ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"interval_python_job\",\"task_type\":\"python\",\"schedule_type\":\"interval\",\"interval_seconds\":30,\"python_code\":\"print('hello')\",\"is_enabled\":true}"
```

### 7-3. 수동 실행

```cmd
curl -X POST "http://127.0.0.1:8000/tasks/1/run"
```

### 7-4. dashboard 조회

```cmd
curl "http://127.0.0.1:8000/dashboard/summary"
curl "http://127.0.0.1:8000/dashboard/jobs"
curl "http://127.0.0.1:8000/dashboard/html-results"
```

## 8) 운영 체크리스트

- `docs/OPERATIONS_CHECKLIST.md` 참고
- API 응답 헤더 `x-request-id`로 요청 단위 추적 가능

## 9) 점검 명령

```cmd
:: backend
python -m compileall app tests
set PYTHONPATH=.
pytest -q

:: frontend
cd frontend
npm run build
```

## 9) 다음 작업 TODO

- [x] 실제 SQL DB 연결 (SQL_RUNNER_DATABASE_URL)
- [ ] delivery channel(email/knox/webhook)
- [ ] 권한관리 / 감사로그
- [ ] 코드 편집기 고도화

---

### (참고) Linux/macOS 최소 실행

```bash
python -m venv .venv
source .venv/bin/activate
cp .env.example .env
```
