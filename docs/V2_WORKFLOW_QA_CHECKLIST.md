# V2 Workflow QA Checklist

Use this checklist to validate the V2 action-first workflows (match queue, tasks, audits, advising meetings, and quick preview).

## How To Use

- Mark each check `PASS`, `FAIL`, or `BLOCKED`.
- Capture API errors and browser console output for failures.
- Record final results in the run record at the bottom.

## 1) Environment + Startup

- [ ] `docker compose up --build -d` (or local backend/frontend) starts cleanly.
- [ ] Backend docs reachable at `http://localhost:8000/docs`.
- [ ] Frontend app reachable at `http://localhost:8080` (or local Vite URL).
- [ ] Latest migration (`20260424_0015`) is applied successfully.

## 2) Action Dashboard

- [ ] Dashboard loads card counts from `/dashboard/summary`.
- [ ] Top risk students list renders with links to student profiles.
- [ ] "Run Intervention Triggers" creates tasks and returns success feedback.
- [ ] Latest sync card renders without crash when no sync exists.

## 3) Task Queue

- [ ] Task page loads tasks and targets.
- [ ] Create task with linked student and linked course.
- [ ] Inline status update persists after refresh.
- [ ] Inline priority update persists after refresh.
- [ ] Due date update persists after refresh.
- [ ] Delete task removes row.
- [ ] URL filters (`status`, `student_id`, `course_id`, `search`) apply correctly.

## 4) Match Queue Workbench

- [ ] Route `/courses/:courseId/matches` loads without error.
- [ ] `Refresh Suggestions` updates list.
- [ ] Confidence band filtering works (high/medium/low).
- [ ] Single confirm updates status/history.
- [ ] Single reject updates status/history.
- [ ] Bulk confirm updates selected suggestions.
- [ ] Bulk reject updates selected suggestions.
- [ ] Decision history panel reflects actions.

## 5) Gradebook Messaging + Audit/Undo

### 5.1 Message Students Workflow
- [ ] Candidate preview loads for `not_submitted`.
- [ ] Candidate preview loads for score threshold filters.
- [ ] Send/log outreach creates interaction logs.
- [ ] Optional follow-up task creation works when enabled.

### 5.2 Grade Audit + Undo
- [ ] Editing a grade creates an audit entry.
- [ ] Audit row includes student + assignment context.
- [ ] Undo applies previous grade state.
- [ ] Undone row is marked and cannot be undone twice.

## 6) Advising Meetings

- [ ] Create advising meeting with mode + summary + action items.
- [ ] Meeting appears in timeline.
- [ ] Save meeting with follow-up creates task.
- [ ] "Convert to Task" from existing meeting creates linked task.

## 7) Document Quick Preview

- [ ] Selecting `Preview` on PDF opens inline PDF frame.
- [ ] Extracted text panel loads for previewed document.
- [ ] Non-PDF preview fallback message is shown correctly.
- [ ] Download and text links still function.

## 8) Report Template Builder

- [ ] `/reports` loads templates, student targets, preview data, and report history without errors.
- [ ] Create or duplicate a report template.
- [ ] Edit template name, title, footer, colors, font scale, and header style.
- [ ] Enable/disable sections and reorder them; live preview updates immediately.
- [ ] Upload a logo and confirm it appears in the preview and generated export.
- [ ] Generate a single-student PDF/PNG report.
- [ ] Generated report run appears in Report History.
- [ ] Generated PDF and PNG appear as `Report` documents in Documents and Student Profile.
- [ ] Archive a non-default template without breaking existing report history links.

## 9) UX Speed Improvements

- [ ] Sidebar collapse retains icon recognizability and route tooltips.
- [ ] Command palette opens with Ctrl/Cmd+K and navigates.
- [ ] Density toggle changes table spacing.
- [ ] Sticky action bars remain visible while scrolling dense pages.
- [ ] Saved views function on:
  - [ ] gradebook
  - [ ] students
  - [ ] interactions
- [ ] Mobile/tablet table behavior hides lower-priority columns for marked tables.

## 10) Automated Frontend Validation

- [ ] `npm run test` passes.
- [ ] `npm run build` passes.

## QA Run Record

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
