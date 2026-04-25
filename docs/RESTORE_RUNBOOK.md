# Restore Execution Runbook

Use this runbook to prove that encrypted backup artifacts can restore the database and stored files for a single-owner Jon's Gradebook deployment.

## Safety Rules

- Run restore drills against a disposable local or staging environment first.
- Confirm `SECRET_KEY` and `ENCRYPTION_KEY` match the environment that created the backup.
- Create a fresh backup immediately before any restore attempt.
- Keep Canvas write-back disabled; restore is local state recovery only.

## Drill Checklist

1. Start the target environment and confirm the app loads.
2. Open Settings and create a manual backup with a drill note.
3. Select the backup artifact and review the preflight comparison:
   - current table row counts
   - backup table row counts
   - current vs backup stored-file counts
4. Record preflight results in the evidence section below.
5. Type `RESTORE` in the confirmation field.
6. Execute restore from the selected backup.
7. Restart backend and frontend services.
8. Validate the restored state:
   - Dashboard loads without API errors.
   - Students, Courses, Documents, Reports, LLM Workbench, and Settings routes load.
   - At least one stored document downloads or previews.
   - Report history and generated document links remain intact.
   - LLM Workbench jobs retain prompt/output history and final feedback links.
9. Run automated checks:

```bash
cd frontend
npm run test
npm run build

cd /Users/jon/projects/git/jons-gradebook
python3 -m compileall backend/app
```

10. Log the result in the evidence record.

## Evidence Record

Date:

Environment:

Backup ID:

Backup path:

Preflight summary:
- Tables changed:
- File delta:
- Warnings:

Restore result:
- Restored tables:
- Restored files:
- Backend restart:
- Frontend restart:

Post-restore validation:
- Dashboard:
- Students/Courses:
- Documents:
- Reports:
- LLM Workbench:
- Settings:

Automated checks:
- `npm run test`:
- `npm run build`:
- `python3 -m compileall backend/app`:

Critical issues:
1.
2.
3.
