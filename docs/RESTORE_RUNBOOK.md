# Restore Execution Runbook

Use this runbook to prove that encrypted backup artifacts can restore the database and stored files for a single-owner Jon's Gradebook deployment.

## Safety Rules

- Run restore drills against a disposable local or staging environment first.
- Confirm `SECRET_KEY` and `ENCRYPTION_KEY` match the environment that created the backup.
- Create a fresh backup immediately before any restore attempt.
- Keep Canvas write-back disabled; restore is local state recovery only.
- Keep the backend process running as a single instance during restore and do not interrupt it.

## Built-In Restore Safeguards

Before live data is changed, the backend now:

- requires the exact server-side confirmation value `RESTORE`
- verifies the encrypted artifact SHA-256 checksum and decryptability
- validates the backup format, table names, columns, file sizes, and per-file checksums for newly created artifacts
- rejects absolute, traversal, duplicate, or otherwise unsafe storage paths
- stages every restored file beside the live storage directory

Database rows are then replaced in foreign-key-safe order, PostgreSQL identity sequences are reset, and the staged storage directory is swapped into place. If an error occurs before the database commit completes, the database transaction is rolled back and the previous storage directory is restored.

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
   - Create one disposable task after restore and confirm its ID does not conflict with restored records.
9. Run automated checks:

```bash
cd frontend
npm run test
npm run build

cd ..
python3 -m compileall backend/app

cd backend
pytest tests/test_backup_restore.py
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
- `pytest tests/test_backup_restore.py`:

Critical issues:
1.
2.
3.

## Completed Drill: 2026-07-24

Environment:
- isolated disposable `postgres:16` container on localhost
- clean migration from an empty database through `20260425_0017` (head)
- temporary storage and backup directories created by pytest and removed afterward

Preflight evidence:
- tasks: 2 current rows vs 1 backup row (`-1` restore delta)
- stored files: 2 current files vs 1 backup file (`-1` restore delta)
- lowercase confirmation was rejected with HTTP 422 before restore

Restore result:
- all 48 restorable mapped tables were processed; `backup_artifacts` remained available
- the original linked student/course task was restored and the post-backup task was removed
- the encrypted document was restored, decrypted, and downloaded with its original content
- the post-backup extra file was removed
- a new task inserted successfully after restore, proving the PostgreSQL task identity sequence was reset beyond restored IDs

Post-restore validation:
- Dashboard, Students, Courses, Documents, Reports, LLM Workbench, and Settings API routes returned HTTP 200
- full backend suite with PostgreSQL drill: 9 passed
- frontend Vitest suite: 8 passed
- frontend production build: passed

Issue found and corrected during the drill:
- clean migration initially failed in `20260424_0016` because its instruction-template seed omitted non-null governance columns already present when the metadata-backed initial migration created the current schema
- the seed now detects those columns and supplies compatible values while retaining the historical `0015 -> 0016` upgrade path
