# Jon's Gradebook

Jon's Gradebook is a single-instructor academic operations cockpit for professors, advisors, and teaching staff who want more control than a hosted LMS usually provides. It brings gradebook work, student follow-up, advising notes, document handling, report generation, and privacy-first LLM-assisted feedback into one local, Docker-deployable workspace.

The app is intentionally built around the daily work of teaching: find the students who need attention, understand why, act quickly, keep an audit trail, and produce useful student-facing artifacts without scattering context across Canvas, spreadsheets, shared drives, email drafts, and local notes.

## Why Use This Alongside A Hosted LMS?

Hosted LMS platforms are essential systems of record, but they are usually optimized for course delivery and institutional consistency. Jon's Gradebook is meant to complement, not replace, that LMS by giving an instructor a private operational layer.

Benefits over depending only on the LMS:

- **Instructor-owned workflow:** Keep local notes, advising context, grading decisions, intervention tasks, and reports in one place instead of forcing every workflow into LMS screens.
- **Read-only Canvas sync first:** Pull Canvas data into a safer local workspace without immediately writing changes back to the LMS.
- **Cross-workflow student view:** See grades, attendance, documents, advising notes, interactions, rubrics, tasks, and reports from a student-centered profile.
- **Faster repeated work:** Use saved views, command palette navigation, density controls, match workbenches, and inline task updates for the operational work an LMS often makes click-heavy.
- **Better auditability:** Track local grade edits, match decisions, document versions, report runs, and feedback artifacts.
- **Privacy-first AI support:** Prepare de-identified prompts, use copy/paste or local Ollama workflows, and save only instructor-approved final feedback to the student file by default.
- **Custom reporting:** Build editable PDF/PNG student report templates with section controls, theme colors, logo support, and generated artifacts linked back to Documents and Student Profile.
- **Portable deployment:** Run the app with Docker and keep storage under your control.

## Core Functions

### Action Dashboard

- Triage cards for grading, missing/late follow-up, out-of-sync overrides, alerts, and advising follow-ups.
- Top-risk student list backed by local risk signals.
- Quick entry points into the workflows that need attention.

### Canvas Sync And Gradebook

- Read-only Canvas sync with snapshots and event logs.
- Merged gradebook that combines Canvas-imported data with local assignments and local edits.
- Assignment match queue for pairing Canvas assignments with local records.
- Grade audit timeline with undo support for recent local edits.
- Keyboard-friendly grade editing, saved views, density mode, and sticky action bars.

### Student Profiles

- Student-centered view of classes, scores, attendance summaries, alerts/tags, documents, recent interactions, advising meetings, rubric evaluations, and generated reports.
- Editable student profile fields for local correction and enrichment.
- Direct links to attached and centrally managed documents.

### Advising, Interactions, And Tasks

- Advising roster and meeting timeline.
- Advising meeting capture with action items.
- Convert advising follow-ups into tasks.
- Interaction logging for individual students, course cohorts, and advisees.
- Task queue with status, priority, due date, linked student/course, and intervention-rule generation.

### Documents

- Encrypted file storage with versioning.
- Central Documents page for finding, sorting, filtering, previewing, and downloading stored documents.
- Multi-student document linking.
- Extracted text preview for supported files.
- Direct Student Profile visibility for linked student documents.

### Reports

- Structured student report template builder.
- Editable sections for profile, courses, grades, attendance, rubric evaluations, interactions, advising, tasks, and linked documents.
- Theme colors, font scale, title/footer text, header style, and logo support.
- Live preview plus PDF/PNG export.
- Report run history.
- Generated report artifacts saved as `Report` documents for Documents and Student Profile.

### LLM Workbench

- Student-feedback workflow for uploaded or existing student work.
- Saves the original paper as a linked student document.
- Extracts text, de-identifies it, and produces a reviewable prompt.
- Supports copy/paste use with any LLM and local Ollama execution for local-first workflows.
- Stores raw prompt/output in LLM history rather than student-facing Documents by default.
- Lets the instructor paste/edit output into final feedback.
- Saves only instructor-approved final feedback as a linked `Feedback` document by default.
- Can include rubric criteria as narrative context without auto-scoring or creating rubric evaluations.

## Safety And Data Handling

- Field-level encryption for sensitive values.
- Encrypted file blobs for uploaded documents.
- Encrypted backup artifacts.
- De-identification preview before LLM send.
- Encrypted de-identification replacement maps for new LLM runs.
- Read-only Canvas integration in the current phase.
- Canvas write-back remains deferred until dry-run, diff, and audit safeguards are in place.

This is still a trusted, single-user architecture. Treat it as an instructor-controlled workspace rather than a multi-user institutional LMS replacement.

## Stack

- Backend: FastAPI + SQLAlchemy + Alembic + APScheduler
- Database: PostgreSQL
- Frontend: React + Vite
- Optional local LLM runtime: Ollama
- Deployment: Docker Compose

## Quick Start With Docker

1. Export secrets or create a `.env` file used by Docker Compose:

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

3. Apply migrations if your deployment path does not run them automatically:

```bash
docker compose exec backend alembic upgrade head
```

4. Open the app:

- Frontend: `http://localhost:8080`
- Backend API docs: `http://localhost:8000/docs`

## Local Development

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

## Application Routes

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
- `/llm` LLM Workbench
- `/reports` Reports
- `/settings` Settings and operations

All API endpoints are under `/api/v1`.

## Recommended First Walkthrough

1. Configure Canvas access and run a read-only sync.
2. Open the Action Dashboard to see what needs attention.
3. Review one course gradebook and resolve assignment matches.
4. Open a student profile and review grades, attendance, documents, interactions, and reports.
5. Upload a document in Documents or from a profile and confirm it appears in both places.
6. Generate a student report from `/reports`.
7. Try the LLM Workbench with a sample paper using copy/paste or local Ollama, then save final edited feedback.
8. Create a backup before experimenting with larger workflow changes.

## Testing And Validation

Frontend:

```bash
cd frontend
npm run test
npm run build
```

Backend:

```bash
cd /Users/jon/projects/git/jons-gradebook
python3 -m compileall backend/app
cd backend
alembic upgrade head
```

See [Testing Strategy](docs/TESTING_STRATEGY.md) and [V2 Workflow QA Checklist](docs/V2_WORKFLOW_QA_CHECKLIST.md) for workflow-level validation.

## Documentation Map

- [Phased implementation plan](docs/PHASED_IMPLEMENTATION_PLAN.md)
- [Future features backlog](docs/NEXT_PHASE_FEATURE_BACKLOG.md)
- [Testing strategy](docs/TESTING_STRATEGY.md)
- [V1 baseline QA checklist](docs/V1_QA_CHECKLIST.md)
- [V2 workflow QA checklist](docs/V2_WORKFLOW_QA_CHECKLIST.md)
- [Running changelog](docs/CHANGELOG.md)

## Current Boundaries

- Single-user/trusted-user deployment is intentional for now.
- Canvas sync is read-only; write-back is deferred.
- Messaging workflows currently log outreach and candidate lists; external delivery is future-phase.
- LLM workflows are assistive. The instructor reviews and approves final feedback.
- Rubric context can guide LLM feedback, but rubric scoring remains manual in the current workbench.

## Troubleshooting

### Windows Line Endings

If backend startup fails with `env: 'sh\r': No such file or directory`, a shell script has CRLF line endings. This repo enforces LF for `*.sh` via `.gitattributes`, and the backend image build also normalizes `/docker-entrypoint.sh`.

After pulling latest changes, rebuild the backend image:

```bash
docker compose build --no-cache backend
docker compose up -d
```

### Missing Alembic Locally

If `alembic upgrade head` fails with `command not found`, install backend requirements inside the backend virtual environment or run the migration through Docker:

```bash
docker compose exec backend alembic upgrade head
```
