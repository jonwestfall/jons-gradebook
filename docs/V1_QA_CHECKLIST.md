# V1 QA Checklist

Use this checklist to validate V1 end-to-end before release or major merge.

## How To Use

- Run checks in order.
- Mark each step `PASS`, `FAIL`, or `BLOCKED`.
- Capture notes/screenshots for failures.
- If a step fails, log repro steps and stop only that section; continue other sections.

## 1) Environment + Startup

- [X] `docker compose up --build -d` completes without container crash loops.
- [X] `docker compose ps` shows `db`, `backend`, `frontend` healthy/up.
- [X] App loads at `http://localhost:8080` without 502/blank page.
- [ ] Backend docs load at `http://localhost:8000/docs`.
- [ ] No migration errors in `docker compose logs backend`.

## 2) Canvas Sync

### 2.1 Course Discovery + Selection UX
- [ ] Open **Canvas Sync** page successfully.
- [ ] Click `Review / Replace Selection` and verify course picker opens.
- [ ] Course picker filters work:
  - [ ] keyword filter (title/code/term/ID)
  - [ ] term filter
  - [ ] paging next/previous
- [ ] `Save Exact Selection (Replace)` replaces allowlist as expected.
- [ ] `Discover + Add More Classes` mode opens and explains additive behavior.
- [ ] `Add Checked Classes (Keep Existing)` preserves existing selections and adds checked courses.

### 2.2 Manual Sync + Run Audit
- [ ] `Run Manual Sync` creates a new run.
- [ ] New run appears in run list with status and timestamps.
- [ ] Selecting a run shows snapshot counts and event counts.
- [ ] Event filters work:
  - [ ] action (`created/updated/deleted`)
  - [ ] entity (`course/enrollment/assignment/submission`)
- [ ] Event paging (`Newer/Older`) works.
- [ ] Deleted-item guidance is visible and understandable.

### 2.3 Student Metadata Mapping
- [ ] Mapping panel loads target fields and default paths.
- [ ] Mapping field save works for each target:
  - [ ] `first_name`
  - [ ] `last_name`
  - [ ] `email`
  - [ ] `student_number`
  - [ ] `institution_name`
- [ ] Metadata preview loads for selected course.
- [ ] Quick-mapping buttons apply preview labels to target fields and persist.

## 3) Courses + Merged Gradebook

### 3.1 Gradebook Load + Navigation
- [ ] Open a synced course gradebook.
- [ ] Student sort defaults to last name.
- [ ] Student search and assignment search both work.
- [ ] Grid scrolls both directions and frozen student-name column remains visible.

### 3.2 Local Assignment Creation
- [ ] Create local assignment with grading type `points`.
- [ ] Create local assignment with grading type `letter`.
- [ ] Create local assignment with grading type `completion`.
- [ ] New assignments appear as columns.

### 3.3 Cell Editing + Keyboard
- [ ] Clicking an assignment cell opens details pane editor for that exact student/assignment.
- [ ] Points edit saves and persists after refresh.
- [ ] Letter edit saves and persists after refresh.
- [ ] Completion edit saves and persists after refresh.
- [ ] Keyboard movement works (`arrows`, `tab`, `enter`/`F2`).
- [ ] Completion 4-state cycle works via keyboard `Space`:
  - [ ] Complete -> Incomplete -> Missing -> Excused -> Complete

### 3.4 Column Reordering + Calculated Columns
- [ ] Drag/drop assignment columns reorders and persists.
- [ ] Drag/drop calculated columns reorders and persists.
- [ ] Editor option toggle controls visibility of reorder arrows.
- [ ] Create calculated column.
- [ ] Edit calculated column.
- [ ] Delete calculated column.

### 3.5 Local-vs-Canvas Overrides
- [ ] Edit a Canvas-imported assignment grade locally.
- [ ] Cell indicates out-of-sync/local override state.
- [ ] Override remains after refresh and after sync.

## 4) Students

### 4.1 Students Grid
- [ ] Students page renders grid (not cards).
- [ ] Search filter works on name/email/student number/phone.
- [ ] Scope filters work:
  - [ ] all students
  - [ ] students in classes
  - [ ] advisees
- [ ] Sorting works:
  - [ ] by last name
  - [ ] by most recent interactions

### 4.2 Student Profile Editing
- [ ] Open a student profile from grid.
- [ ] Update and save:
  - [ ] first name
  - [ ] last name
  - [ ] email
  - [ ] phone number
- [ ] Reload profile and confirm values persist.
- [ ] Return to Students grid and confirm updated values display.

### 4.3 Student Profile Academic View
- [ ] Profile shows classes and nested assignment rows.
- [ ] Assignment rows include score and percent fields when applicable.

## 5) Interactions + Advising + Attendance

- [ ] Interactions page can target:
  - [ ] one student
  - [ ] all students in a class
  - [ ] all advisees
- [ ] Creating interaction logs produces visible entries in recent interactions.
- [ ] Student can be marked as advisee from profile.
- [ ] Attendance statuses (Present/Absent/Tardy/Excused) can be recorded.

## 6) Backup + Restore

### 6.1 Backup
- [ ] Manual backup creation succeeds.
- [ ] Backup artifact appears in Settings/backup list.

### 6.2 Restore Safety
- [ ] Restore preflight shows comparison summary.
- [ ] Typed confirmation gate (`RESTORE`) is required.

### 6.3 Restore Execution (when implemented)
- [ ] Full restore from one artifact completes.
- [ ] System state (DB + files + settings/templates) reflects artifact.

## 7) Security + Data Handling (V1 Scope)

- [ ] Sensitive field encryption path works (no plaintext leak in API payloads where not intended).
- [ ] File uploads are stored encrypted at rest.
- [ ] De-identification preview required before LLM send.
- [ ] De-identified prompts and mapping exports/audit views are accessible.

## 8) Final Regression Sweep

- [ ] API smoke: core endpoints return expected status codes.
- [ ] Migrations from clean DB to head succeed.
- [ ] Existing seeded/demo data upgrades without migration failure.
- [ ] Scheduler starts without crashing backend.
- [ ] No major console/runtime errors in frontend during normal use.

---

## QA Run Record (Copy Per Run)

Date:

Environment:

Build/Commit:

Tester:

Summary:
- Passed:
- Failed:
- Blocked:

Critical Issues:
1.
2.
3.
