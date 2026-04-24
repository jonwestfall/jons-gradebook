# Testing Strategy

This document defines current quality gates and the planned expansion path for Jon's Gradebook. The goal is to protect the workflows a professor would trust day to day: Canvas sync, grade review, advising follow-up, document storage, report generation, and privacy-first LLM-assisted feedback.

## Current Test Gates (as of 2026-04-24)

## Frontend

### 1) Unit/smoke test gate

```bash
cd frontend
npm run test
```

- Framework: Vitest + Testing Library + jsdom
- Current scope:
  - route-level smoke coverage for key pages
  - verifies app shell + primary workflow routes render under mocked API
  - includes LLM Workbench smoke coverage for templates, job history, and inspector surfaces

### 2) Type/build gate

```bash
cd frontend
npm run build
```

- Runs `tsc -b` followed by production Vite build.
- Prevents merge of broken route/page wiring and TS regressions.

## Backend

### 1) Compile/syntax gate

```bash
cd /Users/jon/projects/git/jons-gradebook
python3 -m compileall backend/app
```

- Lightweight syntax/integrity guard for router/model/schema/service changes.

### 2) Migration integrity (manual today)

```bash
cd backend
alembic upgrade head
```

- Required after backend model changes.
- Must be validated in local/dev DB before deployment.

## Workflow QA

- Baseline V1: `docs/V1_QA_CHECKLIST.md`
- Active workflow hardening QA: `docs/V2_WORKFLOW_QA_CHECKLIST.md`

Manual QA remains important because many workflows are visual and operational: a route can compile while still being awkward for repeated instructor use or cramped on a laptop display.

## Target Coverage Expansion (Next)

## Backend test expansion

1. Add API route tests (pytest + test DB) for:
- `/dashboard/summary`
- `/tasks/*`
- `/courses/{id}/grade-audits` and undo
- `/courses/{id}/message-candidates` and `/message-students`
- `/students/{id}/risk`
- `/advising/meetings`
- `/reports/templates`, `/reports/students/{id}/preview`, `/reports/students/{id}`, and `/reports/runs`
- `/llm/instructions`, `/llm/workbench/jobs`, prompt preparation, output capture, and finalization

2. Add service tests for:
- risk scoring edge cases (no grades, no attendance, no interactions)
- intervention trigger deduplication behavior
- report renderer config normalization and document artifact creation
- LLM de-identification map encryption and source-document ownership/link checks

3. Add migration tests:
- upgrade from previous head to latest
- downgrade/upgrade sanity for newly introduced tables

## Frontend test expansion

1. Add component/workflow tests for:
- Match Queue bulk approve/reject behavior
- Gradebook message preview + send path
- Grade audit undo path
- Task queue inline status/priority edits
- Advising meeting create -> task conversion path
- Document preview loading and fallback behaviors
- Report builder section/theme edits and generation history
- LLM Workbench upload/existing source, prompt preparation, output paste, and final feedback save

2. Add persistence tests:
- saved views in students/interactions/gradebook
- density mode persistence

3. Add keyboard interaction tests:
- command palette open/execute/close
- gradebook keyboard edit navigation regression

## Manual Regression Matrix (per release candidate)

1. Grade entry save/edit integrity across points/letter/completion
2. Match decision correctness and decision history timeline
3. Task creation from:
- intervention rules
- advising meeting conversion
- message follow-up options
4. Report template editing, PDF/PNG generation, generated artifact links in Documents/Profile, and document preview integrity
5. LLM Workbench upload/existing-document source selection, de-identification review, copy/local output path, final feedback save, and Documents/Profile visibility
6. Sync event pagination/filtering and no-crash UI behavior

## Professor-Evaluation Smoke Path

Use this when introducing the app to a new faculty user:

1. Start the app and explain that Canvas sync is read-only in the current phase.
2. Show the dashboard and how it gathers actionable work into one page.
3. Open a course gradebook, demonstrate a local edit, and show the audit/undo trail.
4. Open a student profile and show grades, attendance, interactions, documents, reports, and feedback artifacts together.
5. Upload or preview a document.
6. Generate a student report and confirm it appears in Documents/Profile.
7. Prepare an LLM Workbench prompt from sample student work, show de-identification, paste or run local output, and save edited final feedback.

## Release Validation Recommendation

For each release candidate:

1. Run frontend test + build gates
2. Run backend compile + migration upgrade
3. Execute high-priority V2 checklist scenarios
4. Log outcome in changelog and QA run record
