# Phased Implementation Plan (Revised & Complete)

## Progress Snapshot (Updated 2026-04-22)

### Phase Status
- V1: complete (accepted baseline)
- Active phase: V2 Workflow Hardening

### Recently Completed
- Canvas sync:
  - course discovery + selected-course sync flow (persistent allowlist + per-run selection mode)
  - student metadata mapping + metadata preview UI
  - run event pagination and event filtering
  - Canvas Sync UI reorganization with collapsible sections, course quick filter, term filter, and paging
  - clearer class selection actions (`Review / Replace Selection` vs `Discover + Add More Classes`)
- Gradebook:
  - merged gradebook sorting/search controls with last-name default student sort
  - local-first gradebook foundations (points, letter, completion grading modes)
  - completion quick-edit support and 4-state keyboard cycle (Complete -> Incomplete -> Missing -> Excused)
  - right-side collapsible grade details pane + editor options toggles
  - drag reorder support for gradebook columns
- Students:
  - student profile assignment drill-down with per-assignment percent
  - Students page converted from cards to searchable/sortable grid list
  - student list filters: all / in classes / advisees
  - student profile editor fields for first name, last name, email, phone number
- Interactions and advising:
  - targeting UX (single student, course cohort, all advisees)
  - profile-level advisee tagging
- Backup:
  - manual encrypted backup creation endpoint
  - restore preflight API + typed restore safeguard in Settings
- Documentation:
  - running commit-linked changelog
  - V1 QA checklist with repeatable test instructions

### V1 Delivery Checklist

#### Complete
- Trusted single-user/no-login architecture
- Core domain model + Alembic migrations
- Dockerized stack
- Read-only Canvas sync (manual + scheduled) with selected-course management
- Historical Canvas snapshots + per-run sync events
- Merged gradebook core with Canvas + local data
- Student profile core, advising core, attendance core, interactions core
- Student metadata mapping workflow
- Encrypted-at-rest approach for V1:
  - field-level encrypted sensitive columns
  - encrypted file blobs
- Manual backup creation and restore preflight UX

#### V1 Sign-Off Notes
- V1 is marked complete and frozen as the release baseline.
- Any remaining polish from prior notes is now tracked as V2 work unless treated as a hotfix.

### V2 Kickoff Priorities (Now Active)
- Backup/restore hardening:
  - full restore execution workflow from one artifact in UI/API
  - scheduled backup automation
  - operator restore runbook + full end-to-end validation in Docker
- Gradebook workflow hardening:
  - assignment match queue UI (approve/reject/confidence and bulk actions)
  - Canvas-authoritative decision history UI
  - conflict guidance polish for local-vs-Canvas edits
- Canvas sync hardening:
  - deleted-item edge-case handling validation (especially enrollments/submissions)
  - audit trail readability polish across event types
- Reliability + quality gates:
  - migration/API/scheduler reliability sweep
  - expanded tests and critical-flow regression checklist

## Phase 1: Foundation (Core System + V1 Non-Negotiables)

### Confirmed Planning Decisions
- Security scope for V1 encryption:
  - field-level encryption for sensitive database columns
  - encrypted file blobs for stored attachments/documents
  - this is sufficient for V1 (full physical database volume encryption is not required in-app)
- Canvas token scopes are already confirmed for read/write access to the user's classes
- Authentication mode for V1:
  - trusted single-user deployment
  - no login flow required
- Backup/restore target for V1:
  - full system restore from one artifact
- Course sync selection modes:
  - persistent allowlist
  - per-run course selection
- Reminder delivery in V1:
  - in-app only
  - SMTP outbound email support planned for a later phase
- Report template hierarchy:
  - global default template
  - per-course template overrides
- LLM audit/export defaults:
  - de-identified prompts exportable by default
  - de-identification mapping tables exportable/auditable by default

### Core Architecture
- Domain model and migration baseline
- Dockerized deployment (FastAPI + Postgres + optional Redis)
- Trusted single-user/no-login mode for V1 (no roles/permissions in V1)
- Encrypted-at-rest storage in V1 via:
  - field-level encryption for sensitive columns
  - encrypted file blobs for stored files/attachments

### Canvas Integration (Read-Only)
- Canvas read-only sync service
- Manual sync + scheduled daily sync
- Ability to sync:
  - all courses
  - selected courses via persistent allowlist
  - selected courses via per-run selection
- Snapshot system:
  - preserve all imported records
  - retain changed/deleted Canvas items as historical snapshots
- Sync logs and import audit tracking
- Canvas read/write scopes for user's classes are confirmed; write operations remain deferred to Phase 5

### Gradebook Core
- Local assignment + grade storage
- Canvas assignment import
- Merged gradebook view (Canvas + Local)
- Assignment matching engine using:
  - name similarity
  - due date proximity
  - points possible
- Match suggestion system with user approval

### Grade Authority System
- When user confirms match:
  - allow Canvas to be marked authoritative
  - archive local twin
  - hide local twin by default (toggle to reveal)
- Maintain historical trace of merge decisions

### Grade Rules Engine (V1 Required Rules)
- Drop lowest score:
  - within assignment group only
- Required assignment completion gate:
  - warning only (no automatic grade penalty)
- Rule templates reusable across courses

### Student Core System
- Global student model across courses
- Student profile includes:
  - alerts
  - attendance summary
  - recent interactions
  - flags/tags
  - notes
- Student summary prioritizes:
  1. alerts
  2. attendance
  3. recent interactions
  4. grades (drill-down)

### Attendance System
- Status types:
  - Present
  - Absent
  - Tardy
  - Excused
- Auto-generate meeting dates from weekly schedule
- Allow manual add/remove of dates
- Bulk attendance entry per session
- Link attendance into interaction log

### Interaction Logging
- Unified interaction system including:
  - attendance
  - advising meetings
  - office visits
  - manual notes
  - uploaded files
- Support:
  - timestamps
  - tags
  - reminders/follow-ups
  - in-app reminder tracking (V1)

### Advising Module (Separate from Courses)
- Separate advising records
- Support advisees not currently enrolled
- Advising records include:
  - rich text notes
  - tags
  - reminders/follow-ups
  - attachments
  - meeting logs
  - in-app reminders (V1)

### File & Document System
- Supported types:
  - PDF
  - DOCX
  - TXT
- For each document:
  - store original file
  - store extracted text
  - automatic versioning on update
- Unified attachment system usable across:
  - courses
  - students
  - advising

### Rubrics / Checklists / Scoring
- Reusable templates across courses
- Support:
  - points
  - checkboxes
  - narrative comments
- Per-assignment rubric instances
- Score report generation

### Exports (V1 Required)
- Export student feedback as:
  - PDF
  - branded PNG/image summary
- Branding configuration:
  - logo
  - footer text
  - signature block
  - global default template
  - per-course template overrides
- Report tone templates:
  - formal
  - informal (default options)

### LLM Workflow (Baseline)
- Providers:
  - OpenAI
  - Ollama
  - Google Gemini
- Workflow:
  1. extract text
  2. de-identify
  3. preview redaction (required)
  4. send to LLM
  5. store output
- De-identification targets:
  - student names
  - student IDs
  - email addresses
  - course section names
  - institution names
- Outputs:
  - stored permanently
  - editable after generation
- Auditing/export defaults:
  - de-identified prompts are exportable by default
  - de-identification mapping tables are exportable/auditable by default

### Backup System (V1 Required)
- Manual backup
- Scheduled backups
- Backup includes:
  - database
  - attachments
  - extracted text
  - templates
  - settings
- Encrypted backup artifacts
- Full system restore capability from one artifact (database + files + templates + settings)

---

## Phase 2: Workflow Hardening

- Add test coverage:
  - service layer
  - API routes
  - migration tests
- Improve validation and error handling

### Gradebook UX Improvements
- Full gradebook editing UI for local working mode
- Visual indicators for:
  - Canvas vs Local
  - authoritative vs archived
- Match queue with:
  - approve/reject
  - confidence bands

### File & Report Enhancements
- File preview support (PDF, DOCX)
- Improved export layout engine
- Custom branding templates editor
- Global default + per-course override management UI

### Backup Improvements
- Backup retention policies
- Backup restore UI (not just CLI)

### Sync Improvements
- Sync conflict handling UI
- Snapshot diff viewer
- Persistent allowlist management UI for selected-course sync
- Per-run course selection UX improvements

---

## Phase 3: Data Quality + Analytics

- Advanced reusable grade rule templates
- Student risk indicators:
  - missing assignments
  - low grades
  - attendance patterns
- Trend analysis across courses

### Dashboards
- Cross-course student dashboards
- Advising dashboards
- Attendance anomaly detection
- Assignment anomaly detection

### Interaction System
- Timeline filtering/search
- Tag-based filtering
- Reminder tracking improvements
- Prepare reminder delivery abstraction for future SMTP support

---

## Phase 4: LLM Productionization

- Policy packs for de-identification presets
- Institution-specific configurations

### LLM Enhancements
- Provider routing and fallback strategy
- Prompt template versioning
- Prompt approval workflows

### Evaluation Layer
- Output quality evaluation tools
- Hallucination detection heuristics
- Feedback comparison tools

### Advanced Privacy
- Reversible redaction tokens (optional, user-approved only)
- Audit logs for all LLM interactions
- Harden and extend default export/audit workflows for prompts and mapping tables

### Notification Expansion
- Add outbound email delivery through SMTP (opt-in)
- Map reminders/follow-ups to in-app and SMTP delivery channels

---

## Phase 5: Canvas Write-Back (Target V3)

- Introduce write-capable Canvas gateway
- Maintain strict separation from read-only client

### Safety Mechanisms
- Explicit capability flags
- Dry-run previews for all write operations
- Diff-based confirmation before submission

### Write Support
- Grade updates
- Assignment updates (limited scope)
- Comment pushback (optional)

### Audit & Recovery
- Full audit log of write actions
- Rollback metadata where possible
