# web_scheduler (Phase 5)

`dalbongscheduler`에서 분리한 웹 스케줄러 프로젝트입니다.

현재 단계는 **5단계: 자동 스케줄 등록 + 대시보드 API + 관리자 프론트 연동** 입니다.

---

## 1) 지금 상태 요약

### 백엔드
- Task CRUD API: `/tasks`
- Task preset API: `GET /tasks/presets`, `POST /tasks/bootstrap-defaults`
- 수동 실행 API: `POST /tasks/{task_id}/run`
- 실행 이력 API: `/runs`, `/runs/{run_id}`, `/tasks/{task_id}/runs`
- 결과물 API: `/artifacts`, `/artifacts/{artifact_id}`, `/tasks/{task_id}/artifacts`
- HTML Preview API: `/artifacts/{artifact_id}/preview`
- 파일 업로드 API: `POST /files/upload`, `GET /files`
- SQL 결과 엑셀 다운로드 API: `GET /artifacts/{artifact_id}/download.xlsx`
- Dashboard API: `/dashboard/summary`, `/dashboard/jobs`, `/dashboard/html-results`
- Health API: `/health`

### 자동 실행 지원
- `manual`: 스케줄러 등록 안 함
- `cron`: cron_expr 기반 자동 등록
- `interval`: interval_seconds 기반 자동 등록(최소 10초)

### 프론트엔드
- Dashboard
- Tasks (한글 UI, 비개발자용 스케줄 입력: 수동/매일/매주/매월/간격)
- Task Detail
- Runs
- HTML Results

---

## 2) 폴더 구조

```text
web_scheduler/
  app/                 # FastAPI backend
  tests/               # pytest tests
  frontend/            # React + Vite + TypeScript admin UI
  docs/
    OPERATIONS_CHECKLIST.md
  .env.example
  requirements.txt
  README.md
```

---

## 3) "uvicorn은 했는데 접속은 어떻게?" (가장 많이 묻는 케이스)

### A. 백엔드만 띄운 상태
아래 명령으로 백엔드만 실행하면:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

접속 가능 URL은:
- API Root/Health: `http://<서버IP>:8000/health`
- Swagger: `http://<서버IP>:8000/docs`
- Dashboard API(JSON):
  - `http://<서버IP>:8000/dashboard/summary`
  - `http://<서버IP>:8000/dashboard/jobs`
  - `http://<서버IP>:8000/dashboard/html-results`

> 즉, **웹 관리 화면(React UI)** 은 아직 안 뜹니다. (백엔드 API만 뜬 상태)

### B. 웹 관리 화면까지 보려면
프론트도 따로 실행해야 합니다.

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

그다음 접속:
- Frontend: `http://<서버IP>:5173`

`frontend/.env`의 `VITE_API_BASE_URL`이 백엔드 주소를 가리켜야 합니다.
예:
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

## 4) Windows CMD 기준 실행

### 4-1. 백엔드

```cmd
cd web_scheduler
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
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

---

## 5) 환경변수

### 백엔드 `.env.example`
- `DATABASE_URL=sqlite:///./web_scheduler.db`
- `SQL_RUNNER_DATABASE_URL=` (비우면 `DATABASE_URL` 사용)
- `SQL_RUNNER_ALLOW_WRITE=false` (기본 write 차단)
- `UPLOADS_DIR=./uploads`
- `MAIL_ENABLED=false`
- `MAIL_API_URL=`
- `MAIL_SYSTEM_ID=`
- `MAIL_TOKEN=`
- `MAIL_SENDER_ID=`
- `DEFAULT_TIMEZONE=Asia/Seoul`
- `CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`

### 프론트엔드 `frontend/.env.example`
- `VITE_API_BASE_URL=http://127.0.0.1:8000`

---

## 6) API 빠른 확인 순서

### 6-1. 헬스체크
```bash
curl http://127.0.0.1:8000/health
```

### 6-2. 기본 Task 템플릿 자동 생성
```bash
curl -X POST http://127.0.0.1:8000/tasks/bootstrap-defaults
```

### 6-3. Task 목록 조회
```bash
curl http://127.0.0.1:8000/tasks
```

### 6-4. Task 수동 실행
```bash
curl -X POST http://127.0.0.1:8000/tasks/1/run
```

### 6-5. Dashboard 조회
```bash
curl http://127.0.0.1:8000/dashboard/summary
curl http://127.0.0.1:8000/dashboard/jobs
curl http://127.0.0.1:8000/dashboard/html-results
```

---

## 7) SQL Runner 사용법

- SQL task 실행 후 Task 상세 > 결과물에서 `엑셀` 버튼으로 다운로드 가능합니다.
- 메일 제목 템플릿은 `{md}`(예: 3/13), `{today}`, `{ymd}` 치환을 지원합니다.
- 수신자 입력은 `sungmook.cho, user2` 형식으로 넣으면 도메인 없는 경우 `@samsung.com` 자동 보정됩니다.

SQL task 생성 시 `task_type=sql`, `sql_code`를 넣으면 실행됩니다.

- 읽기 쿼리(`SELECT`)는 기본 허용
- 쓰기 쿼리(`INSERT/UPDATE/DELETE/...`)는 기본 차단
- 쓰기 허용하려면:

```env
SQL_RUNNER_ALLOW_WRITE=true
```

실제 별도 DB를 붙이려면:

```env
SQL_RUNNER_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/dbname
```

---

## 8) 관측성/운영 포인트

- API 응답 헤더 `x-request-id` 제공 (요청 추적)
- 주요 라우트 로그에 request_id 포함
- 운영 절차는 `docs/OPERATIONS_CHECKLIST.md` 참고

---

## 9) 점검 명령

```bash
# backend
python -m compileall app tests
PYTHONPATH=. pytest -q

# frontend
cd frontend
npm run build
```

---

## 10) 현재 TODO

- [x] 실제 SQL DB 연결 (`SQL_RUNNER_DATABASE_URL`)
- [ ] delivery channel(email/knox/webhook)
- [ ] 권한관리 / 감사로그
- [ ] 코드 편집기 고도화

---

## (참고) Linux/macOS 최소 실행

```bash
cd web_scheduler
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

cd frontend
npm install
cp .env.example .env
npm run dev
```
