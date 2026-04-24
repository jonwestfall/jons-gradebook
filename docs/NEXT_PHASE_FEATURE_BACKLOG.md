# Next-Phase Feature Backlog

Prioritized future feature list after the current V2 hardening work. The backlog assumes Jon's Gradebook remains an instructor-owned companion to the hosted LMS: Canvas stays the external course system of record, while this app focuses on local workflow speed, evidence, advising context, reporting, and privacy-first AI assistance.

## Priority Definitions

- P0: Protect reliability and core instructor workflows
- P1: High-value UX and analytics expansion
- P2: Platform and scale enhancements

## P0: Immediate Next (post-current worktree)

## 1) Sync conflict + snapshot diff UX

- Build conflict-focused resolution UI for local override vs incoming Canvas values.
- Add clear side-by-side diff for changed snapshots.
- Expose decision rationale capture for auditability.

## 2) Hard backend test coverage

- Add pytest suite for new routes/services:
  - tasks, dashboard, risk, grade-audit undo, message workflows
  - report templates/runs and generated document links
  - LLM instruction templates, workbench jobs, de-identification, and final feedback documents
- Add migration test lane for upgrade integrity.

## 3) Restore execution runbook + drill

- Document and dry-run full restore execution from one artifact.
- Add explicit operator checklist and post-restore validation steps.

## 4) Workflow benchmark instrumentation

- Track click/time metrics for:
  - match resolution per course
  - at-risk student follow-up logging
- Verify >=40% reduction target against baseline flow.

## P1: High-Impact Product Extensions

## 5) Professor onboarding and first-run guide

- Add a first-run checklist for Canvas connection, sync, backup, document categories, reports, and LLM provider choices.
- Add sample demo data or a guided demo mode for interested faculty evaluating the app.
- Add concise in-app explanations for what is local, what syncs from Canvas, and what is student-facing.

## 6) Outreach template library v2

- Template categories by scenario (missing work, low grade, advising follow-up).
- Tokenized template variables (student name, assignment title, due date).
- Saved draft and quick-send shortcuts.

## 7) Risk panel transparency controls

- Instructor-configurable weighting by signal.
- "Why flagged" drill-down with editable thresholds.
- Course-scoped risk view and trend sparkline.

## 8) Case/task board enhancements

- Kanban view for task statuses.
- Bulk re-prioritize and due-date shifts.
- Task completion outcome tags for intervention effectiveness reporting.

## 9) Advanced advising lifecycle

- Structured advising action items with status tracking.
- Meeting agenda templates.
- Follow-up completion loop inside advising timeline.

## 10) LLM Workbench v2

- Add prompt version history and approval status for instruction templates.
- Add optional institution-specific de-identification policy packs.
- Add side-by-side final-feedback comparison before saving.
- Add richer final output formats after the baseline text feedback document.

## P2: Strategic Expansion

## 11) Multi-channel delivery (deferred)

- Optional SMTP delivery for outreach/reminders.
- Delivery state tracking (queued/sent/failed).
- Keep in-app logging as source of truth.

## 12) Cross-course analytics workspace

- Cohort trends and completion heatmaps.
- Intervention-to-outcome correlation views.
- Filter by term/course/advisor tags.

## 13) Canvas write-back safety model

- Dry-run diff previews before write actions.
- Explicit write-capability flags and rollback framing.
- Maintain strict audit trails for all outbound changes.

## 14) Multi-user readiness (future architecture)

- Assignment/ownership model for shared advising teams.
- Permission boundaries and audit ownership metadata.
- Keep single-user mode supported as first-class deployment option.

## De-prioritized for now

- Full enterprise CRM workflow emulation.
- Complex role hierarchy and approval chains.
- External integrations that bypass core instructor workflows.
