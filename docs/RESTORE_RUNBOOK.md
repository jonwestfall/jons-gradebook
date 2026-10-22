# Restore Execution Runbook

Use this runbook to restore Jon's Gradebook from an encrypted backup: either rolling back on the same machine, or recovering onto a new machine after the original database or volume is lost.

## How Restore Works

- A backup is one encrypted file containing every database table (except the list of backups itself) and every stored file (documents, report files, logos). It also records the database schema revision it was taken at.
- Restore replaces **all** current records and stored files with the backup's contents.
- Before changing anything, restore verifies the file's checksum, that it decrypts with the current `ENCRYPTION_KEY`, that its schema revision matches the running database, and that every file path is safe.
- Restore takes an **automatic safety backup** of the current state first (listed as "Automatic safety backup before restoring #N"), so a restore can itself be undone.
- The database rewrite and the stored-file swap succeed or fail together. If anything fails, the database is rolled back and the original files are put back; the error message says so.

## Safety Rules

- Restore needs the same `ENCRYPTION_KEY` that created the backup. Keep a copy of the key somewhere safe and separate from the backups. Without it, backups cannot be read.
- Download backups regularly (Settings, then **Download Selected Backup**) and keep copies off this machine. Backups on the same volume as the data are lost together with it.
- A backup can only be restored into a database at the same schema revision. To restore an older backup, run the application version that created it, restore, then upgrade the application.
- Keep Canvas write-back disabled; restore is local state recovery only.

## Scenario A: Roll Back on the Same Machine

1. Open **Settings → Backups** and choose the backup in **Select Backup**.
2. Review the **Restore Preflight Comparison**:
   - schema revision: backup vs current (must match)
   - warnings (restore is disabled when the backup cannot be restored)
   - table row counts and stored-file counts, current vs backup
3. Type `RESTORE` in the confirmation box and click **Restore Selected Backup**.
4. Note the safety backup number in the result message. To undo the restore, restore that backup the same way.
5. Validate the restored state (see the checklist below).

## Scenario B: Recover onto a New Machine

1. Install the same application version that created the backup, with the same `ENCRYPTION_KEY`, and start it with an empty database and storage volume (`docker compose up`; migrations run automatically).
2. Open **Settings → Backups → Import backup file**, choose the downloaded `.json.enc` file, and click **Import Backup**. Import fails if the file is not a backup or was encrypted with a different key.
3. Select the imported backup ("Imported from ..."), review the preflight, type `RESTORE`, and restore.
4. Validate the restored state.

The same steps work through the API:

```bash
curl -F file=@gradebook-backup.json.enc http://localhost:8000/api/v1/backup/import   # returns {"id": N, ...}
curl http://localhost:8000/api/v1/backup/N/preflight                                   # check can_restore and warnings
curl -H 'content-type: application/json' -d '{"backup_id": N}' http://localhost:8000/api/v1/backup/restore
```

## Post-Restore Validation Checklist

- Dashboard loads without API errors.
- Students, Courses, Documents, Reports, LLM Workbench, and Settings routes load.
- At least one stored document downloads or previews with the expected content.
- A new upload or record can be created (confirms database sequences were reset).
- Report history and generated document links remain intact.
- LLM Workbench jobs retain prompt/output history and final feedback links.

Automated checks:

```bash
cd backend
pytest                    # add TEST_DATABASE_URL=... to include the PostgreSQL restore tests

cd ../frontend
npm run test
npm run build
```

## Evidence Record

### Drill 2026-10-22: disaster recovery onto a new database

Environment: application at the commit that closed issue #2, run with `uvicorn app.main:app` against PostgreSQL 16; machine A and machine B were separate databases with separate, empty storage and backup directories and the same `ENCRYPTION_KEY`. All steps used the HTTP API only.

Backup: #1 on machine A, note "restore drill", downloaded as a 9,316-byte file.

Preflight on machine B after import:
- Schema revision: backup `20261022_0018`, current `20261022_0018`
- `can_restore`: true; warnings: none
- Files in backup: 1

Restore result:
- Restored tables: 48; restored files: 1
- Safety backup: #2 ("Automatic safety backup before restoring #1")

Post-restore validation:
- Students via API: Ada, Grace (machine B had 0 before)
- Stored document download: matches the original content
- New document upload after restore: succeeded with a new id (2)
- New row insert into `student_profiles`: succeeded (sequences reset)
- Dashboard summary: HTTP 200
- Undo: restoring safety backup #2 returned machine B to its pre-restore state (0 students, 0 files)
- Server log errors: none

Automated checks: `pytest` with PostgreSQL (17 passed at the time of the drill, including the disaster-recovery and foreign-key restore tests), `npm run test`, `npm run build`: all passed.

Critical issues: none.

### Template for future drills

Date:

Environment:

Backup ID / file:

Preflight summary:
- Schema revision (backup vs current):
- Tables changed:
- File delta:
- Warnings:

Restore result:
- Restored tables:
- Restored files:
- Safety backup ID:

Post-restore validation:
- Dashboard:
- Students/Courses:
- Documents (download + new upload):
- Reports:
- LLM Workbench:
- Settings:

Critical issues:
1.
