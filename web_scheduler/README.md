# web_scheduler (Phase 4)

`dalbongscheduler`에서 분리한 웹 스케줄러 프로젝트입니다.

현재 단계는 **4단계: 관리자 프론트엔드 추가** 입니다.
- 기존 FastAPI 백엔드 API를 그대로 사용
- 운영자가 브라우저에서 Task / Run / Artifact / HTML Preview를 조회/관리

---

## 1) 현재 구현 범위

### 백엔드 (기존 유지)
- Task CRUD API: `/tasks`
- 수동 실행 API: `POST /tasks/{task_id}/run`
- 실행 이력 API: `/runs`, `/runs/{run_id}`, `/tasks/{task_id}/runs`
- 결과물 API: `/artifacts`, `/artifacts/{artifact_id}`, `/tasks/{task_id}/artifacts`
- HTML Preview API: `/artifacts/{artifact_id}/preview`
- Health API: `/health`

### 프론트엔드 (신규)
- Dashboard 페이지
- Tasks 페이지 (검색/필터, 생성/수정/삭제, 수동 실행)
- Task Detail 페이지 (task/runs/artifacts/preview)
- Runs 페이지 (필터 + 상세 모달)
- HTML Results 페이지 (artifact 조회 + preview)

---

## 2) 폴더 구조

```text
web_scheduler/
  app/                 # FastAPI backend
  tests/               # pytest tests
  frontend/            # React + Vite + TypeScript admin UI
    src/
      app/
      api/
      types/
      pages/
      components/
      styles/
  .env.example
  requirements.txt
  README.md
```

---

## 3) Windows CMD 기준 실행 방법

## 3-1. 백엔드 실행

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

## 3-2. 프론트엔드 실행

```cmd
cd web_scheduler\frontend
npm install
copy .env.example .env
npm run dev
```

- Frontend: `http://127.0.0.1:5173`

---

## 4) 프론트 환경변수

`frontend/.env.example`

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

## 5) 주요 화면 설명

### Dashboard
- `/health`, `/tasks`, `/runs`, `/artifacts`를 조합해 요약 표시
- 총 작업 수, 활성 작업 수, 최근 성공/실패, 최근 실행/HTML 결과 확인

### Tasks
- `name / task_type / is_enabled` 검색
- task 생성/수정 모달
- 수동 실행 버튼
- 삭제 전 확인 다이얼로그

### Task Detail
- 작업 기본 정보 + 코드 보기
- task별 run/artifact 목록
- HTML artifact preview

### Runs
- `task_id / status / trigger_type` 필터
- 실행 이력 상세 모달(result_summary/error_message)

### HTML Results
- artifact 목록/필터(task_id)
- html/text/json 결과 미리보기

---

## 6) CORS

프론트 로컬 개발 주소 허용:
- `http://localhost:5173`
- `http://127.0.0.1:5173`

`.env.example`:

```env
CORS_ALLOW_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

---

## 7) 품질 확인 명령

```cmd
:: backend
python -m compileall app tests
pytest -q

:: frontend
cd frontend
npm run build
```

---

## 8) 다음 단계 TODO

- [ ] APScheduler 실제 자동 등록 강화
- [ ] dashboard 전용 백엔드 집계 API 고도화
- [ ] 실제 SQL DB 연결
- [ ] delivery channel(email/knox/webhook)
- [ ] 권한관리 / 감사로그

---

## (참고) Linux/macOS 최소 실행

```bash
python -m venv .venv
source .venv/bin/activate
cp .env.example .env
```
