# Jon's Gradebook

Single-user, Docker-deployable instructor/advisor cockpit for gradebook operations, student follow-up, advising workflows, document handling, and de-identified LLM analysis.

## Stack

- Backend: FastAPI + SQLAlchemy + Alembic + APScheduler
- Database: PostgreSQL
- Frontend: React + Vite
- Optional local LLM runtime: Ollama

## Quick Start (Docker)

1. Export secrets (or create a `.env` file used by Docker Compose):

```bash
export SECRET_KEY='replace-me-with-real-secret'
export ENCRYPTION_KEY='replace-with-fernet-key'
export CANVAS_BASE_URL='https://canvas.yourschool.edu'
export CANVAS_API_TOKEN='your-token'
```

2. Start services:

```bash
docker compose up --build
```

3. Open app: `http://localhost:8080`
4. Backend API docs: `http://localhost:8000/docs`

## Local Dev (without Docker)

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Current Product Capabilities (V2 Workflow Hardening)

### Instructor triage + operations

- Action Dashboard with operational cards and top-risk students
- Task Queue with filters, inline status/priority updates, and intervention rule execution
- Rules-based intervention task generation from student risk signals

### Gradebook workflow

- Merged gradebook (Canvas + local) with local-first editing
- Assignment match queue workbench (`suggest/list/confirm/reject/bulk/history`)
- Grade audit timeline with undo support for recent edits
- "Message Students Who..." workflow (not submitted, not graded, missing, score bands)
- Saved gradebook views, keyboard-first editing, and density mode

### Advising + interactions

- Advisee roster plus meeting timeline
- Advising meeting capture with action items and quick convert-to-task
- Interaction logging across student, course cohort, and advisee scopes
- Saved interaction views

### Documents + reporting

- Encrypted document storage with extracted text and versioning
- Document quick preview (inline PDF + extracted text side panel)
- PDF/PNG report generation with branding templates

### Platform + safety

- Read-only Canvas sync with historical snapshots and run events
- Encrypted backup artifacts with restore preflight safety checks
- Field-level sensitive data encryption + encrypted file blobs
- De-identification preview-first LLM workflow

## Application Routes (Frontend)

- `/` Action Dashboard
- `/tasks` Task Queue
- `/canvas-sync` Canvas sync operations
- `/courses` Courses list
- `/courses/:courseId/gradebook` Gradebook workbench
- `/courses/:courseId/matches` Match Queue Workbench
- `/students` Students
- `/students/:studentId` Student profile
- `/advising` Advising + meetings
- `/attendance` Attendance
- `/interactions` Interactions
- `/documents` Documents
- `/reports` Reports
- `/settings` Settings and operations

## API Prefix

All endpoints are under `/api/v1`.

## Testing + Validation

### Frontend

```bash
cd frontend
npm run test
npm run build
```

- Uses Vitest + Testing Library smoke tests for key route/workflow load.

### Backend

```bash
cd /Users/jon/projects/git/jons-gradebook
python3 -m compileall backend/app
```

- Compile check is currently the lightweight gate in-repo.
- Expanded backend automated tests are tracked in `docs/TESTING_STRATEGY.md`.

## Documentation Map

- [Phased implementation plan](docs/PHASED_IMPLEMENTATION_PLAN.md)
- [Future features backlog](docs/NEXT_PHASE_FEATURE_BACKLOG.md)
- [Testing strategy](docs/TESTING_STRATEGY.md)
- [V1 baseline QA checklist](docs/V1_QA_CHECKLIST.md)
- [V2 workflow QA checklist](docs/V2_WORKFLOW_QA_CHECKLIST.md)
- [Running changelog](docs/CHANGELOG.md)

## Notes

- Trusted single-user architecture is intentional for near-term velocity.
- Canvas write-back remains deferred to later phases.
- In-app workflows are primary; external messaging delivery is future-phase.
- Run `alembic upgrade head` after pulling new backend changes (includes task + grade audit tables).

## Troubleshooting (Windows)

- If backend fails with `env: 'sh\\r': No such file or directory`, it means a shell script has CRLF line endings.
- This repo enforces LF for `*.sh` via `.gitattributes`, and backend image build also normalizes `/docker-entrypoint.sh`.
- After pulling latest changes, rebuild backend image:

```bash
docker compose build --no-cache backend
docker compose up -d
```
