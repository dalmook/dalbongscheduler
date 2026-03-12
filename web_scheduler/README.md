# web_scheduler

`dalbongscheduler`에서 분리된 웹 기반 스케줄러 관리 프로젝트입니다.  
현재는 **4단계(백엔드 + 관리자 프론트엔드)** 기준으로 구현되어 있습니다.

## 1) 현재 구현 범위

### 백엔드 (FastAPI)
- Task CRUD (`/tasks`)
- 수동 실행 (`POST /tasks/{id}/run`)
- 실행 이력/결과물 조회 (`/runs`, `/artifacts`)
- APScheduler 자동 실행 (`cron`, `interval`) + startup sync
- 대시보드 API (`/dashboard/summary`, `/dashboard/jobs`, `/dashboard/html-results`)

### 프론트엔드 (React + Vite + TS)
- Dashboard / Tasks / Runs / HTML Results 화면
- Task 생성/수정/삭제/수동실행
- 실행이력 조회 및 상세 확인
- HTML 결과 preview
- 검색/필터, 로딩/에러/빈 상태 UI

---

## 2) 폴더 구조

```text
web_scheduler/
  app/                      # FastAPI backend
  tests/                    # pytest
  frontend/                 # React admin UI
    src/
      app/router.tsx
      api/
      types/
      pages/
      components/
      styles/global.css
  .env.example
  requirements.txt
  README.md
```

---

## 3) 백엔드 실행

```bash
cd web_scheduler
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

- Backend: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

### CORS
로컬 프론트 개발을 위해 기본 허용:
- `http://localhost:5173`
- `http://127.0.0.1:5173`

`.env`에서 변경 가능:
```env
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

---

## 4) 프론트엔드 실행

```bash
cd web_scheduler/frontend
npm install
cp .env.example .env
npm run dev
```

프론트 기본 주소:
- `http://localhost:5173`

### frontend 환경변수
`frontend/.env.example`:
```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

## 5) 운영자 화면 설명

### Dashboard
- 요약 카드 (total/enabled/scheduled/success/failed/html)
- scheduler jobs 테이블
- recent failed runs
- 최신 HTML 결과 카드 + preview

### Tasks
- 검색/필터(name/task_type/is_enabled)
- 테이블(상태/스케줄/next_run)
- 새 작업 등록/수정 모달
- 수동 실행/삭제/상세이동

### Task Detail
- 작업 정보 + 코드 보기
- task 기준 실행 이력
- task 기준 artifact 목록
- HTML artifact preview

### Runs
- task_id/status/trigger 필터
- 실행 이력 테이블
- run 상세(result_summary, error_message)

### HTML Results
- html task별 최신 결과 목록
- 최신 artifact preview
- 버전 목록(해당 task artifacts)

---

## 6) 스케줄 예시

### cron 예시
- `0 9 * * *`
- `*/15 * * * *`
- `30 8 * * 1-5`

### interval 예시
- `30`
- `300`

> interval 최소값은 10초입니다.

---

## 7) 주의사항

- 현재는 **단일 프로세스** 기준 scheduler 동작입니다.
- 멀티 인스턴스/분산 실행은 아직 고려하지 않았습니다.
- SQL runner는 아직 mock 실행입니다.

---

## 8) 기본 검증

```bash
# backend
python -m compileall app tests
pytest -q

# frontend
npm run build
```

---

## 9) 다음 단계 TODO

- [ ] delivery channel(email/knox/webhook)
- [ ] 권한관리 / 감사로그
- [ ] 코드 에디터 고도화
- [ ] 배포(Docker/Nginx)
