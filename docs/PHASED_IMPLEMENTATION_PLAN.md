# Phased Implementation Plan

This plan tracks what is shipped, what is in-flight, and what is next for Jon's Gradebook as a single-instructor, action-first cockpit. The product direction is to complement a hosted LMS with a private instructor-controlled operations layer for triage, advising, document handling, reporting, and reviewed AI-assisted feedback.

## Progress Snapshot (Updated 2026-04-24)

### Phase status
- V1 Baseline: complete (accepted)
- V2 Workflow Hardening: active, major milestones shipped
- V3+ Expansion: planned

### Newly shipped in V2 (current worktree)

#### Action workflows
- Action Dashboard (`/dashboard/summary`) with triage cards and top-risk student feed.
- Task Queue (`/tasks`) including filters, inline updates, and intervention trigger runs.

#### Gradebook speed + safety
- Match Queue Workbench route/UI for assignment matching decisions with bulk actions.
- Grade audit timeline (`/courses/{id}/grade-audits`) with undo endpoint and UI.
- "Message Students Who..." workflow:
  - candidate preview (`/courses/{id}/message-candidates`)
  - outreach logging (`/courses/{id}/message-students`)
  - optional follow-up task creation

#### Advising and case follow-up
- Advising meetings list/filter payload improvements.
- Advising meeting capture UI with timeline and "convert to task" action.

#### Document prep speed
- Document quick preview in Documents page:
  - inline PDF preview
  - extracted text side panel
- Student report template builder:
  - editable student report presets
  - live preview
  - PDF/PNG export
  - generated artifact links into Documents and Student Profile
- LLM Workbench student-feedback workflow:
  - original-paper document save
  - de-identified prompt preparation
  - copy/paste or local Ollama output capture
  - instructor-edited final feedback document save

#### Risk and intervention foundations
- Student risk service and student risk endpoint (`/students/{id}/risk`).
- Rules-based intervention task generation (`/tasks/rules/run`).
- Settings support for `intervention_rules` persistence.

#### UI acceleration improvements
- Sidebar collapse upgraded to icon+label behavior (no hidden text hack).
- Command palette (Ctrl/Cmd+K) for quick navigation.
- Saved views for gradebook/students/interactions.
- Sticky action bars and density mode.
- Mobile/tablet table behavior improved with prioritized column collapse.

#### Test harness and validation
- Frontend test harness added (Vitest + Testing Library + jsdom).
- Route/workflow smoke tests added.

## Phase 1: V1 Baseline (Complete)

- Trusted single-user/no-login architecture
- Core data model + migrations
- Dockerized deployment
- Read-only Canvas sync with snapshots and event logs
- Merged gradebook foundations (Canvas + local)
- Student/advising/attendance/interaction core models and workflows
- Rubrics and report generation
- Encrypted file/document storage and extracted text
- LLM de-identification preview-first flow
- Backup creation and restore preflight safety

## Phase 2: Workflow Hardening (Active)

### Completed (high-confidence shipped)
- Match queue workbench with bulk decisioning
- Grade audit + undo safety window
- Action dashboard and task cockpit
- Risk service + intervention triggers
- Advising meeting capture UX + task conversion
- Document quick preview
- Report template builder and generated document linking
- LLM Workbench student feedback workflow
- Saved views + command palette + density toggle
- Frontend smoke tests and build gate

### Remaining V2 scope
- Expand automated backend and workflow tests beyond the initial pytest/Vitest closeout coverage.
- Run and record a restore drill using `docs/RESTORE_RUNBOOK.md`.
- Continue UX polish on dense pages after real professor walkthroughs.

## Phase 3: Analytics + Messaging Expansion

- Workflow benchmark instrumentation for match resolution and at-risk follow-up is now available through task benchmark events.
- Case/task board foundations now include board view, bulk priority/date/outcome edits, and intervention outcome tags.

- Cross-course risk and trend analytics dashboards
- Outreach template library enhancements with richer defaults
- Cohort-level progress and completion trend views
- Intervention quality reporting (task completion outcomes)
- Report-pack expansion for cohort and advising-summary use cases beyond single-student reports

## Phase 4: LLM Productionization

- Prompt/version governance and approval review for instruction templates
- Provider routing fallback policy
- Evaluation layer for output quality and hallucination checks
- De-identification policy packs by institution
- Optional richer final-feedback document formats after the text/PDF-friendly baseline

## Phase 5: Canvas Write-Back (Deferred)

- Controlled write-capable Canvas gateway
- Dry-run + diff confirmation before write execution
- Explicit safety flags and audit trail for writes

## Architectural Guardrails

- Keep near-term scope single-owner, single-workspace.
- Favor action-driven workflows over standalone informational pages.
- Default to reversible operations where user trust can be impacted.
- Add automation/testing only when it protects core instructor journeys.

## Success Criteria for Current Direction

1. Reduce time/click cost for two core journeys by >=40%:
   - resolve assignment match suggestions for one course
   - identify at-risk student and log follow-up
2. Keep grade edit integrity with auditable and undoable operations.
3. Ensure intervention trigger outputs are predictable and deduplicated.
4. Maintain green frontend build + smoke test gate before merges.
