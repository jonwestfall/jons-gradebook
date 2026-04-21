# Jon's Gradebook

Single-user Docker-deployable web application for gradebook operations, advising, attendance, document workflows, and de-identified LLM analysis.

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

## Key Features Included in This Scaffold

- Read-only Canvas sync (manual + daily scheduled)
- Historical snapshots of Canvas payloads
- Course-level merged gradebook (Canvas + local assignments)
- Assignment match suggestions (name + due date + points)
- Canvas-authoritative confirm flow archives and hides local twin
- Reusable grade rules (`drop_lowest_in_group`, `required_completion_gate` warning)
- Student profile across classes
- Separate advising entities (including non-enrolled advisees)
- Attendance with generated class meetings from weekly schedules
- Interaction logs across attendance/advising/office/manual/email/file contexts
- Rubrics/checklists/scoring guides and evaluations
- PDF + PNG student report generation
- Document storage with original encrypted file + extracted text + versioning
- LLM workflow with OpenAI/Ollama/Gemini via de-identification preview-first flow
- Persistent editable LLM outputs
- Encrypted backup artifact generation

## API Prefix

All endpoints are under `/api/v1`.

## Notes

- V1 is trusted single-user/no-login by design; there is no multi-user auth subsystem yet.
- V1 encryption scope is field-level encryption for sensitive columns plus encrypted file blobs for stored attachments/documents.
- Canvas token scopes for the user's classes are confirmed for read/write, but Canvas write-back remains deferred to V3.
- V1 backup/restore target is full system restore from one artifact.
- Selected-course sync supports both persistent allowlists and per-run course selection.
- Reminders are in-app only in V1; outbound email via SMTP is planned for a later phase.
- Report branding supports a global default template with per-course overrides.
- De-identified prompts and de-identification mapping tables are exportable/auditable by default.
- The Alembic initial migration creates the full metadata model for rapid iteration.
- Canvas write-back is intentionally not implemented yet, but provider boundaries are set up for V3.
