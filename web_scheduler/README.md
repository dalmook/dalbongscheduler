# web_scheduler

`dalbongscheduler`의 tkinter 기반 구조와 분리된 **웹 전환 1차 백엔드 골격**입니다.
이번 단계는 웹에서 TaskDefinition을 등록/조회/수정/삭제할 수 있는 API와 DB 구조를 제공하고,
2단계에서 붙일 실제 실행 엔진(코드 실행/스케줄 실행)을 위한 준비를 목표로 합니다.

---

## 1) 프로젝트 목적

- FastAPI + SQLAlchemy + APScheduler 기반의 확장 가능한 구조 제공
- 사용자 입력 기반 `python/sql/html` 코드 저장을 위한 `TaskDefinition` 중심 모델 제공
- 실행 로직은 최소 골격으로 두고, CRUD/설정/테이블 초기화/기본 테스트를 우선 구현

---

## 2) 현재 단계(1차) 범위

포함:
- `/health` 헬스체크 API
- `/tasks` CRUD API
- SQLite 기본 DB + PostgreSQL 전환 가능한 `DATABASE_URL` 구조
- 앱 시작 시 테이블 자동 생성
- APScheduler 초기화/시작/종료 + 동기화 placeholder
- pytest 기반 최소 API 테스트

미포함:
- 실제 Python/SQL/HTML 코드 실행
- 실제 APScheduler 잡 등록/실행 동기화
- 실행 이력/아티팩트 저장

---

## 3) 폴더 구조

```text
web_scheduler/
  app/
    main.py
    core/
      config.py
      logging.py
    db/
      base.py
      session.py
      models.py
      init_db.py
    schemas/
      task.py
      common.py
    services/
      task_service.py
      scheduler_service.py
    api/
      routes_health.py
      routes_tasks.py
    utils/
      time_utils.py
  tests/
    conftest.py
    test_health.py
    test_tasks.py
  .env.example
  requirements.txt
  README.md
```

---

## 4) 설치 및 실행 방법

## 요구사항
- Python 3.11+

### 1. 프로젝트 디렉터리 이동
```bash
cd web_scheduler
```

### 2. 가상환경 생성/활성화
```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. 패키지 설치
```bash
pip install -r requirements.txt
```

### 4. 환경변수 파일 준비
```bash
cp .env.example .env
```

### 5. 서버 실행
```bash
uvicorn app.main:app --reload
```

실행 후 접속:
- Swagger: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/health`

---

## 5) 환경변수 설명

`.env.example`를 복사해서 사용하세요. 민감정보는 하드코딩하지 않습니다.

- `APP_NAME`: 앱 이름 (기본 `web_scheduler`)
- `APP_ENV`: 실행 환경 (`local`, `dev`, `prod` 등)
- `APP_HOST`: 바인딩 호스트
- `APP_PORT`: 실행 포트
- `DATABASE_URL`: 기본 SQLite URL, PostgreSQL로 교체 가능
- `LOG_LEVEL`: 로그 레벨 (`INFO`, `DEBUG` 등)
- `DEFAULT_TIMEZONE`: 기본 타임존 (`Asia/Seoul`)

PostgreSQL 전환 예시:
```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/web_scheduler
```

---

## 6) 주요 API

### GET /health
응답 예시:
```json
{
  "status": "ok",
  "service": "web_scheduler",
  "db": "ok"
}
```

### POST /tasks
TaskDefinition 생성

### GET /tasks
목록 조회 (필터 지원)
- `name` (부분 검색)
- `task_type` (`python`/`sql`/`html`)
- `is_enabled` (`true`/`false`)
- 정렬: `created_at DESC`

### GET /tasks/{task_id}
상세 조회

### PUT /tasks/{task_id}
수정

### DELETE /tasks/{task_id}
삭제

---

## 7) 샘플 POST /tasks payload

### 1) Python Task
```json
{
  "name": "python_daily_report",
  "description": "일간 리포트 생성",
  "task_type": "python",
  "schedule_type": "manual",
  "is_enabled": true,
  "python_code": "print('daily report')",
  "params_json": "{\"target_date\": \"2026-01-01\"}",
  "output_format": "json"
}
```

### 2) SQL Task
```json
{
  "name": "sql_sales_summary",
  "description": "매출 집계",
  "task_type": "sql",
  "schedule_type": "cron",
  "cron_expr": "0 9 * * *",
  "is_enabled": true,
  "sql_code": "SELECT date(order_time) AS d, SUM(amount) AS total FROM orders GROUP BY date(order_time);",
  "output_format": "csv"
}
```

### 3) HTML Task
```json
{
  "name": "html_notice_template",
  "description": "공지 템플릿 생성",
  "task_type": "html",
  "schedule_type": "interval",
  "interval_seconds": 3600,
  "is_enabled": false,
  "html_template": "<html><body><h1>{{ title }}</h1><p>{{ body }}</p></body></html>",
  "params_json": "{\"title\": \"Hello\", \"body\": \"World\"}",
  "output_format": "html"
}
```

---

## 8) 테스트 실행

```bash
pytest -q
```

테스트 항목:
- `/health` 200 응답
- task 생성
- task 목록 조회
- task 수정
- task 삭제

---

## 9) 2단계에서 붙일 기능 (TODO)

- [ ] 수동 실행 API
- [ ] APScheduler 실제 동기화
- [ ] `RunHistory` / `Artifact` 테이블
- [ ] HTML 결과 미리보기
- [ ] Dashboard API
