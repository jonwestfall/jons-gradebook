# Changelog

This changelog tracks product and implementation changes for Jon's Gradebook.

## Entry Format

Each entry should include:
- date (YYYY-MM-DD)
- git commit hash (short SHA)
- area(s) changed
- concise summary

Template:

```md
## YYYY-MM-DD
- [commit abc1234] [area: canvas-sync] Summary of change.
- [commit def5678] [area: gradebook] Summary of change.
```

If work is not committed yet, use `commit WORKTREE` temporarily and replace it after commit.

---

## 2026-04-27
- [commit WORKTREE] [area: frontend/ui] Added Settings-controlled Interface Preferences with Balanced, Minimal, and High Contrast themes.
- [commit WORKTREE] [area: frontend/demo] Added browser-local Demo mode with screenshot-safe student, course, task, document, dashboard, and gradebook sample data plus global "Demo mode" labeling.
- [commit WORKTREE] [area: frontend/demo] Expanded Demo mode with example rubrics, rubric evaluations, attendance roll-call records, report templates, report preview content, report history, and demo export results.
- [commit WORKTREE] [area: frontend/demo] Fixed demo-mode Advising and Documents fixture shapes so the public walkthrough routes render without live backend data.
- [commit WORKTREE] [area: docs] Added a screenshot gallery, reusable demo screenshot capture script, and README screenshot previews for social sharing.
- [commit WORKTREE] [area: frontend/ui] Refreshed core UI tokens, card/control radius, focus states, dashboard metric cards, course card grid, and neutral/minimal theme styling for readability and themeability.
- [commit WORKTREE] [area: docs] Added UI/UX audit with external LMS/advising pattern notes and updated README/testing/roadmap docs for demo mode and theme validation.

## 2026-04-25
- [commit WORKTREE] [area: canvas-sync] Added Canvas local-override conflict capture, conflict resolution endpoints, and sync-run snapshot diff API/UI.
- [commit WORKTREE] [area: tasks] Added task board view, bulk priority/due-date/outcome updates, outcome tags, and workflow benchmark event capture.
- [commit WORKTREE] [area: llm] Added instruction template governance fields for version, approval status, approval notes, and policy packs.
- [commit WORKTREE] [area: docs/testing] Added restore execution runbook and expanded V2 QA/testing docs for conflict, benchmark, backend, and restore-drill validation.

## 2026-04-24
- [commit WORKTREE] [area: docs] Rewrote README as a professor-facing introduction covering core functions, hosted-LMS companion benefits, safety boundaries, setup, walkthrough, and validation guidance.
- [commit WORKTREE] [area: docs/testing] Updated roadmap, backlog, testing strategy, and QA checklists to reflect the current Reports and LLM Workbench workflows and new-user evaluation path.
- [commit WORKTREE] [area: backend] Added report template, template asset, and report run persistence with migration `20260424_0015`.
- [commit WORKTREE] [area: backend] Refactored student report generation to use editable template config, theme/logo rendering, and generated PDF/PNG document linking.
- [commit WORKTREE] [area: frontend] Rebuilt `/reports` as a structured report template builder with live preview, section controls, branding controls, export actions, and report history.
- [commit WORKTREE] [area: docs/testing] Updated README, roadmap, testing strategy, QA checklist, and smoke coverage for templated reports.
- [commit WORKTREE] [area: backend] Added LLM instruction templates, workbench jobs, encrypted de-identification maps, upload/existing-document job creation, local Ollama send, pasted output capture, and final feedback document persistence with migration `20260424_0016`.
- [commit WORKTREE] [area: frontend] Rebuilt `/llm` as a privacy-first student feedback workflow with source selection, prompt preview/copy, output capture, final feedback editing, job history, and template inspector controls.
- [commit WORKTREE] [area: docs/testing] Updated README, roadmap, testing strategy, QA checklists, and smoke coverage for the LLM Workbench student feedback workflow.

## 2026-04-23
- [commit WORKTREE] [area: backend] Added new dashboard router and summary endpoint for action-first triage cards and top-risk students.
- [commit WORKTREE] [area: backend] Added task model, schemas, migration, and task API (`list/create/update/delete/targets/rules-run`).
- [commit WORKTREE] [area: backend] Added student risk service and student risk endpoint.
- [commit WORKTREE] [area: backend] Added grade audit model plus course endpoints for audit listing and undo.
- [commit WORKTREE] [area: backend] Added course messaging workflow endpoints for candidate preview and outreach logging with optional follow-up tasks.
- [commit WORKTREE] [area: backend] Expanded advising meetings endpoint payloads for richer advising timeline UX.
- [commit WORKTREE] [area: backend] Added settings support for `intervention_rules`.
- [commit WORKTREE] [area: frontend] Added Task Queue page and route with filtering, inline updates, and intervention execution.
- [commit WORKTREE] [area: frontend] Added Match Queue Workbench page and route with confidence bands, single/bulk actions, and decision history.
- [commit WORKTREE] [area: frontend] Replaced static dashboard module list with action dashboard backed by live data.
- [commit WORKTREE] [area: frontend] Enhanced gradebook with saved views, message-students workflow, grade audit panel, and undo actions.
- [commit WORKTREE] [area: frontend] Enhanced advising with meeting capture, timeline, and convert-to-task flow.
- [commit WORKTREE] [area: frontend] Added document quick preview (inline PDF + extracted text panel).
- [commit WORKTREE] [area: frontend] Added saved views for students/interactions and URL-driven task filters.
- [commit WORKTREE] [area: frontend] Added global UX speed features: icon-aware collapsed sidebar, command palette, density mode, sticky action bars, and mobile table-priority behavior.
- [commit WORKTREE] [area: frontend/testing] Added Vitest test harness, setup files, and route/workflow smoke tests.
- [commit WORKTREE] [area: docs] Refreshed README, phased plan, and testing/QA documentation for current and future scope.

## 2026-04-22
- [commit 0b34447] [area: backup] Added backup restore preflight comparison endpoint and related restore-safety workflow support.
- [commit 0b34447] [area: migrations] Fixed calculated column migration conflict by avoiding duplicate PostgreSQL enum type creation.
- [commit 2344148] [area: gradebook] Added right-side collapsible details pane and editor options toggles.
- [commit d146e49] [area: gradebook] Added completion quick edits and 4-state keyboard cycle (Complete -> Incomplete -> Missing -> Excused).
- [commit d146e49] [area: gradebook] Added drag-and-drop column reordering with optional arrow controls.
- [commit d146e49] [area: students] Replaced Students card list with searchable/sortable grid and all/in-classes/advisees filters.
- [commit d146e49] [area: students] Added editable profile fields for first name, last name, email, and phone number.
- [commit fb8a39f] [area: canvas-sync] Reorganized page into collapsible sections and added class picker filter/paging controls.
- [commit fb8a39f] [area: canvas-sync] Clarified class selection actions: replace allowlist vs add-to-allowlist.
- [commit 33c9031] [area: docs] Added V1 QA checklist and updated implementation/README docs for current V1 status tracking.
- [commit WORKTREE] [area: docs] Marked V1 complete and set V2 workflow hardening as active phase in plan/README.
