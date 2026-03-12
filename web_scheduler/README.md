# web_scheduler (Phase 3)

`dalbongscheduler`의 tkinter 코드와 분리된 FastAPI 기반 백엔드 프로젝트입니다.

현재 단계는 **3단계: 자동 스케줄 등록(APScheduler) + 대시보드 API** 입니다.

---

## 1. 3단계 목표

- `manual / cron / interval` 스케줄 타입을 지원
- `cron/interval + enabled=true` 작업을 APScheduler에 자동 등록
- 작업 생성/수정/삭제 시 scheduler 상태 즉시 반영
- 운영자가 상태를 확인할 수 있는 대시보드 API 제공

---

## 2. 현재 구현 범위

### 포함
- Task CRUD: `POST/GET/GET{id}/PUT/DELETE /tasks`
- 수동 실행: `POST /tasks/{task_id}/run`
- 실행 이력: `GET /runs`, `GET /runs/{run_id}`, `GET /tasks/{task_id}/runs`
- 결과물 조회/미리보기:
  - `GET /artifacts`
  - `GET /artifacts/{artifact_id}`
  - `GET /tasks/{task_id}/artifacts`
  - `GET /artifacts/{artifact_id}/preview`
- 자동 스케줄 등록/동기화:
  - startup sync
  - task 기반 register/update/remove
- Dashboard API:
  - `GET /dashboard/summary`
  - `GET /dashboard/jobs`
  - `GET /dashboard/html-results`

### 제외
- 프론트엔드 관리자 화면
- 실제 외부 SQL DB 실행 연결(현재 SQL runner는 mock)
- 메일/메신저 등 delivery 연동

---

## 3. 자동 실행 지원 범위

- `manual`: 스케줄러 등록 안 함 (수동 실행 전용)
- `cron`: 크론 표현식 기반 등록
- `interval`: 초 단위 간격 등록 (최소 10초)

### 등록 규칙
- `is_enabled=true` + `schedule_type in (cron, interval)` -> 등록
- `is_enabled=false` 또는 `schedule_type=manual` -> 제거
- startup 시 DB task 전체와 scheduler job 동기화
- job id 형식: `task:{task_id}`

---

## 4. 대시보드 API 설명

### `GET /dashboard/summary`
- 총 task 수, enabled 수, scheduled 수
- 최근 24시간 success/failed run 수
- 최근 html artifact 수
- 다음 예정 실행 목록
- 최근 실패 실행 목록

### `GET /dashboard/jobs`
- 현재 scheduler 등록 job 목록
- `job_id`, `task_id`, `task_name`, `trigger`, `next_run_time`, `is_enabled`

### `GET /dashboard/html-results`
- html task 기준 최신 결과 요약
- `preview_text`(HTML 태그 제거 후 축약)
- 최근 성공/실패 시각

---

## 5. 실행 방법 (Windows CMD 기준)

```cmd
cd web_scheduler
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload
```

접속:
- Swagger: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

---

## 6. 환경 변수

`.env.example`:

```env
APP_NAME=web_scheduler
APP_ENV=local
APP_HOST=0.0.0.0
APP_PORT=8000
DATABASE_URL=sqlite:///./web_scheduler.db
LOG_LEVEL=INFO
DEFAULT_TIMEZONE=Asia/Seoul
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

> CORS는 추후 프론트 개발을 위한 기본값입니다.

---

## 7. cron / interval 예시

### cron 예시 3개
- `0 9 * * *` (매일 09:00)
- `*/15 * * * *` (15분마다)
- `30 8 * * 1-5` (평일 08:30)

### interval 예시 2개
- `30` (30초마다)
- `300` (5분마다)

---

## 8. Windows CMD용 샘플 curl

### 8-1) cron task 생성
```cmd
curl -X POST "http://127.0.0.1:8000/tasks" ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"daily_html_report\",\"task_type\":\"html\",\"schedule_type\":\"cron\",\"cron_expr\":\"*/15 * * * *\",\"html_template\":\"<h1>Hello</h1>\",\"is_enabled\":true}"
```

### 8-2) interval task 생성
```cmd
curl -X POST "http://127.0.0.1:8000/tasks" ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"interval_python_report\",\"task_type\":\"python\",\"schedule_type\":\"interval\",\"interval_seconds\":30,\"python_code\":\"print('hi')\",\"is_enabled\":true}"
```

### 8-3) 수동 실행
```cmd
curl -X POST "http://127.0.0.1:8000/tasks/1/run"
```

### 8-4) 대시보드 조회
```cmd
curl "http://127.0.0.1:8000/dashboard/summary"
curl "http://127.0.0.1:8000/dashboard/jobs"
curl "http://127.0.0.1:8000/dashboard/html-results"
```

---

## 9. 테스트

```cmd
pytest -q
```

테스트 포함 항목:
- health
- task CRUD
- manual run / artifact
- scheduler job 등록/미등록/갱신/제거
- dashboard summary/jobs/html-results

---

## 10. 다음 단계 TODO

- [ ] 프론트엔드 관리자 화면
- [ ] 실제 SQL DB 연결
- [ ] delivery channel(email/knox/webhook)
- [ ] 권한관리 / 감사로그

---

## (참고) Linux/macOS 최소 실행 명령

```bash
python -m venv .venv
source .venv/bin/activate
cp .env.example .env
```
