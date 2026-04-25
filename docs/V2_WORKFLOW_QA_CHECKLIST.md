# V2 Workflow QA Checklist

Use this checklist to validate the V2 action-first workflows for a professor-facing deployment: match queue, tasks, audits, advising meetings, document preview, report templates, and the LLM Workbench.

## How To Use

- Mark each check `PASS`, `FAIL`, or `BLOCKED`.
- Capture API errors and browser console output for failures.
- Record final results in the run record at the bottom.

## 1) Environment + Startup

- [ ] `docker compose up --build -d` (or local backend/frontend) starts cleanly.
- [ ] Backend docs reachable at `http://localhost:8000/docs`.
- [ ] Frontend app reachable at `http://localhost:8080` (or local Vite URL).
- [ ] Latest migration (`20260424_0016`) is applied successfully.
- [ ] README first-time setup instructions are accurate for the chosen environment.
- [ ] A new evaluator can identify the difference between Canvas-synced data, local-only data, and student-facing generated artifacts.

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
- [ ] Board view groups tasks by status.
- [ ] Bulk priority changes apply to selected tasks.
- [ ] Bulk due-date shifts apply to selected tasks.
- [ ] Outcome tags persist after refresh and support intervention reporting.
- [ ] At-risk follow-up benchmark events are recorded after rule runs and task completion.

## 4) Match Queue Workbench

- [ ] Route `/courses/:courseId/matches` loads without error.
- [ ] `Refresh Suggestions` updates list.
- [ ] Confidence band filtering works (high/medium/low).
- [ ] Single confirm updates status/history.
- [ ] Single reject updates status/history.
- [ ] Bulk confirm updates selected suggestions.
- [ ] Bulk reject updates selected suggestions.
- [ ] Decision history panel reflects actions.
- [ ] Match resolution benchmark events are recorded after single and bulk decisions.

## 4.1) Canvas Conflict + Snapshot Diff

- [ ] Sync run diff viewer loads submission, assignment, enrollment, and course changes.
- [ ] Local override conflicts appear when Canvas has an incoming value that was retained.
- [ ] `Keep Local Override` resolves a conflict with rationale.
- [ ] `Accept Canvas Value` updates the local grade, records grade audit, and resolves the conflict.
- [ ] `Ignore` resolves a conflict without changing the grade.
- [ ] Resolved conflict rationale remains visible in the conflict UI.

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

## 9) LLM Workbench Student Feedback

- [ ] `/llm` loads students, source documents, instruction templates, rubric context, providers, and recent jobs.
- [ ] Uploading a student paper creates a `Student Work` document linked to the selected student.
- [ ] Creating a job from an existing student document works without uploading a new file.
- [ ] Preparing the job extracts text and shows a de-identified prompt before any send.
- [ ] Replacement map is visible in the inspector and does not appear in student-facing final feedback.
- [ ] Copy prompt works for manual copy/paste mode.
- [ ] Local Ollama run stores output in LLM history when Ollama is available; unavailable Ollama returns a clear error.
- [ ] Pasted LLM output is saved to the job and can be used as the final feedback draft.
- [ ] Edited final feedback saves and finalizes into a `Feedback` document.
- [ ] Only the original paper and final feedback appear in Documents and Student Profile by default.
- [ ] Selected rubric criteria can be included as narrative context without auto-scoring or creating evaluations.

## 10) UX Speed Improvements

- [ ] Sidebar collapse retains icon recognizability and route tooltips.
- [ ] Command palette opens with Ctrl/Cmd+K and navigates.
- [ ] Density toggle changes table spacing.
- [ ] Sticky action bars remain visible while scrolling dense pages.
- [ ] Saved views function on:
  - [ ] gradebook
  - [ ] students
  - [ ] interactions
- [ ] Mobile/tablet table behavior hides lower-priority columns for marked tables.

## 11) Automated Frontend Validation

- [ ] `npm run test` passes.
- [ ] `npm run build` passes.

## 11.1) Backend Validation

- [ ] `pytest` passes from `backend/`.
- [ ] `python3 -m compileall backend/app` passes.
- [ ] Latest migration (`20260425_0017`) applies cleanly.

## 11.2) Restore Drill

- [ ] `docs/RESTORE_RUNBOOK.md` is followed in a disposable environment.
- [ ] Preflight evidence is captured.
- [ ] Restore execution completes.
- [ ] Post-restore route/document/report/LLM validation is recorded.

## 12) Professor Walkthrough Readiness

- [ ] README explains the purpose of the app without requiring implementation-history context.
- [ ] README clearly positions the app as a hosted-LMS companion, not a replacement.
- [ ] A professor can identify the main routes and what each workflow is for.
- [ ] Safety boundaries are clear: read-only Canvas sync, reviewed LLM feedback, manual rubric scoring, and deferred write-back.
- [ ] Documentation map points to roadmap, testing, QA, backlog, and changelog.

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
