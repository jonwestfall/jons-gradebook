# Next-Phase Feature Backlog

Prioritized future feature list after the current V2 hardening work.

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

## 5) Outreach template library v2

- Template categories by scenario (missing work, low grade, advising follow-up).
- Tokenized template variables (student name, assignment title, due date).
- Saved draft and quick-send shortcuts.

## 6) Risk panel transparency controls

- Instructor-configurable weighting by signal.
- "Why flagged" drill-down with editable thresholds.
- Course-scoped risk view and trend sparkline.

## 7) Case/task board enhancements

- Kanban view for task statuses.
- Bulk re-prioritize and due-date shifts.
- Task completion outcome tags for intervention effectiveness reporting.

## 8) Advanced advising lifecycle

- Structured advising action items with status tracking.
- Meeting agenda templates.
- Follow-up completion loop inside advising timeline.

## P2: Strategic Expansion

## 9) Multi-channel delivery (deferred)

- Optional SMTP delivery for outreach/reminders.
- Delivery state tracking (queued/sent/failed).
- Keep in-app logging as source of truth.

## 10) Cross-course analytics workspace

- Cohort trends and completion heatmaps.
- Intervention-to-outcome correlation views.
- Filter by term/course/advisor tags.

## 11) Canvas write-back safety model

- Dry-run diff previews before write actions.
- Explicit write-capability flags and rollback framing.
- Maintain strict audit trails for all outbound changes.

## 12) Multi-user readiness (future architecture)

- Assignment/ownership model for shared advising teams.
- Permission boundaries and audit ownership metadata.
- Keep single-user mode supported as first-class deployment option.

## De-prioritized for now

- Full enterprise CRM workflow emulation.
- Complex role hierarchy and approval chains.
- External integrations that bypass core instructor workflows.
