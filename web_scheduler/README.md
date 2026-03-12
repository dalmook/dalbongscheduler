# web_scheduler

`dalbongscheduler`의 tkinter 코드와 분리된 웹 백엔드 프로젝트입니다.  
현재는 **3단계(APScheduler 자동 실행 + 대시보드 API)** 기준으로 구현되어 있습니다.

## 1. 3단계 목표

- 기존 수동 실행(2단계)을 유지하면서 자동 실행(cron/interval)을 실제 동작 상태로 확장
- TaskDefinition 수정/삭제 시 scheduler 상태가 즉시 반영되도록 동기화
- 운영 관리를 위한 대시보드 API 제공
  - 전체 요약
  - 현재 등록 job 목록
  - HTML 결과 요약

---

## 2. 현재 지원 범위

### 스케줄 타입
- `manual`: APScheduler 등록 안 함, 수동 실행만 가능
- `cron`: APScheduler에 cron trigger로 등록
- `interval`: APScheduler에 interval trigger로 등록

### 자동 실행 등록 규칙
- `is_enabled=true` + `schedule_type in (cron, interval)` → 등록
- `is_enabled=false` 또는 `schedule_type=manual` → 제거
- task 수정 시 스케줄 변경 자동 반영
- task 삭제 시 scheduler job 제거

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
      routes_dashboard.py
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
      dashboard.py
    services/
      task_service.py
      execution_service.py
      artifact_service.py
      scheduler_service.py
      dashboard_service.py
      exceptions.py
    utils/
      time_utils.py
    main.py
  tests/
    conftest.py
    test_health.py
    test_tasks.py
    test_runs_and_artifacts.py
    test_scheduler_dashboard.py
  .env.example
  requirements.txt
  README.md
```

---

## 4. 주요 데이터 모델

### TaskDefinition
핵심 필드:
- `schedule_type`, `cron_expr`, `interval_seconds`, `is_enabled`
- `timezone` (기본 Asia/Seoul)
- `next_run_at`
- `scheduler_job_id`
- `last_run_status`, `last_run_at`

### TaskRun
- 수동/자동 실행 이력 저장 (`trigger_type=manual|scheduled`)
- 상태(`queued/running/success/failed`)와 실행 시간 정보 저장

### TaskArtifact
- 실행 결과물 버전 관리
- 신규 artifact 저장 시 기존 latest 해제 + version 증가

---

## 5. Scheduler 동작 구조

1. 앱 시작 시 `init_scheduler()` → `start_scheduler()` → `sync_enabled_tasks()`
2. DB의 task를 읽어 등록/제거 동기화
3. job id는 `task:{task_id}` 형식
4. 스케줄 트리거 시 내부적으로 `run_task(..., trigger_type="scheduled")` 호출
5. 실행 성공/실패와 관계없이 scheduler thread는 계속 동작 (예외는 로그 처리)

> 현재 구조는 단일 프로세스 기준입니다.

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

## 7. API 요약

### 기본/작업
- `GET /health`
- `POST /tasks`
- `GET /tasks`
- `GET /tasks/{task_id}` (`include_recent_runs=true` 지원)
- `PUT /tasks/{task_id}`
- `DELETE /tasks/{task_id}`

### 실행/결과
- `POST /tasks/{task_id}/run`
- `GET /runs`
- `GET /runs/{run_id}`
- `GET /tasks/{task_id}/runs`
- `GET /artifacts`
- `GET /artifacts/{artifact_id}`
- `GET /tasks/{task_id}/artifacts`
- `GET /artifacts/{artifact_id}/preview`

### 대시보드
- `GET /dashboard/summary`
- `GET /dashboard/jobs`
- `GET /dashboard/html-results`

---

## 8. Cron/Interval 예시

### Cron 예시 3개
- `0 9 * * *` : 매일 09:00
- `*/15 * * * *` : 15분마다
- `30 8 * * 1-5` : 평일 08:30

### Interval 예시 2개
- `30` : 30초마다
- `300` : 5분마다

> interval 최소값은 10초로 제한합니다.

---

## 9. task 생성 후 자동 등록 흐름

1. `POST /tasks` 호출
2. `schedule_type`이 `cron/interval`이고 `is_enabled=true`이면
3. task 저장 직후 scheduler에 즉시 등록
4. `TaskDefinition.next_run_at`, `scheduler_job_id` 갱신
5. `/dashboard/jobs`에서 즉시 확인 가능

---

## 10. 주의사항

- 현재 scheduler는 **단일 프로세스** 기준입니다.
- 멀티 인스턴스/분산 실행(리더 선출, 중복 실행 방지)은 아직 미구현입니다.
- SQL runner는 현재 외부 DB 연결 없는 **mock 실행기**입니다.

---

## 11. 테스트

```bash
pytest -q
```

검증 항목:
- health endpoint
- task CRUD
- 수동 실행 + run/artifact 저장
- scheduler job 등록/수정/제거
- dashboard summary/jobs/html-results

---

## 12. 다음 단계 TODO

- [ ] 관리자 프론트엔드
- [ ] delivery channel(email/knox/webhook)
- [ ] 권한관리 / 감사로그
- [ ] persistent job store / distributed worker
