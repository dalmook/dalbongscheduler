# web_scheduler 운영 체크리스트 (Phase 3)

## 1) 기본 헬스체크
- `GET /health` → `{"status":"ok"}`
- `GET /dashboard/summary`
- `GET /dashboard/jobs`
- `GET /dashboard/html-results`

## 2) 스케줄러 등록 확인
1. cron task 1개 생성
2. interval task 1개 생성
3. `/dashboard/jobs`에서 `job_id=task:{id}` 확인
4. 앱 재시작 후 `/dashboard/jobs` 동일 확인 (sync_enabled_tasks 동작 확인)

## 3) 실행 실패 시 점검 순서
1. `/runs?status=failed` 조회
2. 실패 `run_id`로 `/runs/{run_id}` 조회
3. `error_message` 확인
4. task 설정 확인 (`/tasks/{task_id}`)
5. schedule_type/cron_expr/interval_seconds/timezone 확인

## 4) 관측 포인트 (로그)
- request 단위 추적: `x-request-id`
- 주요 로그 키워드:
  - `run_task task_id=...`
  - `dashboard_summary`
  - `dashboard_jobs`
  - `dashboard_html_results`
  - `Scheduler sync completed`

## 5) 신규 환경 부트스트랩
1. `POST /tasks/bootstrap-defaults`
2. `GET /tasks`로 기본 템플릿 3종 확인
3. 필요 없는 샘플 disable 처리

## 6) 장애 시 임시 우회
- 스케줄러 문제 시 해당 task를 `is_enabled=false`로 비활성
- 수동 실행은 `POST /tasks/{task_id}/run`으로 대체
