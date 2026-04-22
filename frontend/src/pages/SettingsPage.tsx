import { FormEvent, useEffect, useState } from 'react'
import { api } from '../api/client'

type BackupArtifact = {
  id: number
  backup_path: string
  checksum_sha256: string
  encrypted: boolean
  created_at: string
  note?: string | null
}

type BackupDetail = BackupArtifact & {
  generated_at?: string | null
  settings: Record<string, unknown>
  table_counts: Record<string, number>
  file_count: number
}

export function SettingsPage() {
  const [backups, setBackups] = useState<BackupArtifact[]>([])
  const [selectedBackupId, setSelectedBackupId] = useState<number | null>(null)
  const [selectedBackup, setSelectedBackup] = useState<BackupDetail | null>(null)
  const [backupNote, setBackupNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [lastRestoreMessage, setLastRestoreMessage] = useState<string | null>(null)
  const [restorePhrase, setRestorePhrase] = useState('')

  async function loadBackups() {
    const data = await api.get<BackupArtifact[]>('/backup/')
    setBackups(data)
    if (data.length > 0 && selectedBackupId === null) {
      const newest = data[0].id
      setSelectedBackupId(newest)
      await loadBackupDetail(newest)
    }
  }

  async function loadBackupDetail(backupId: number) {
    const detail = await api.get<BackupDetail>(`/backup/${backupId}`)
    setSelectedBackup(detail)
  }

  useEffect(() => {
    void loadBackups().catch((err) => setError((err as Error).message))
  }, [])

  useEffect(() => {
    if (!selectedBackupId) return
    void loadBackupDetail(selectedBackupId).catch((err) => setError((err as Error).message))
  }, [selectedBackupId])

  async function createBackup(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.post('/backup/', { note: backupNote.trim() || null })
      setBackupNote('')
      await loadBackups()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function restoreSelectedBackup() {
    if (!selectedBackupId) return
    if (restorePhrase.trim().toUpperCase() !== 'RESTORE') {
      setError('Type RESTORE in the confirmation box before restoring.')
      return
    }

    setBusy(true)
    setError(null)
    setLastRestoreMessage(null)
    try {
      const result = await api.post<{ restored_tables: number; restored_files: number; generated_at?: string }>(
        '/backup/restore',
        { backup_id: selectedBackupId },
      )
      setLastRestoreMessage(
        `Restore complete: ${result.restored_tables} tables and ${result.restored_files} files restored.`,
      )
      await loadBackups()
      await loadBackupDetail(selectedBackupId)
      setRestorePhrase('')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <h2>Settings and Ops</h2>
      <ul className="list">
        <li className="card">Single-user mode (V1): no auth stack enabled.</li>
        <li className="card">Data-at-rest encryption enabled for stored files and LLM payload fields.</li>
        <li className="card">Daily Canvas sync schedule is server-managed via APScheduler.</li>
        <li className="card">Daily backup schedule is server-managed via APScheduler.</li>
      </ul>

      <article className="card">
        <h3>Backups</h3>
        <form className="form" onSubmit={createBackup}>
          <input
            placeholder="Optional backup note"
            value={backupNote}
            onChange={(event) => setBackupNote(event.target.value)}
          />
          <button type="submit" disabled={busy}>
            {busy ? 'Working...' : 'Create Encrypted Backup'}
          </button>
        </form>

        <div className="form" style={{ marginTop: '0.75rem' }}>
          <label>
            Select Backup
            <select
              value={selectedBackupId ?? ''}
              onChange={(event) => setSelectedBackupId(Number(event.target.value))}
            >
              {backups.map((backup) => (
                <option key={backup.id} value={backup.id}>
                  #{backup.id} - {new Date(backup.created_at).toLocaleString()}
                </option>
              ))}
            </select>
          </label>
          <button onClick={() => void loadBackups()} disabled={busy}>
            Refresh Backups
          </button>
          <button onClick={() => void restoreSelectedBackup()} disabled={busy || !selectedBackupId}>
            Restore Selected Backup
          </button>
        </div>

        <div className="card" style={{ marginTop: '0.75rem' }}>
          <strong>Restore Safety Check</strong>
          <p>Restoring replaces current database records and stored files with artifact contents.</p>
          <input
            placeholder="Type RESTORE to enable restore"
            value={restorePhrase}
            onChange={(event) => setRestorePhrase(event.target.value)}
          />
        </div>

        {selectedBackup ? (
          <div className="card" style={{ marginTop: '0.75rem' }}>
            <div>
              <strong>Backup #{selectedBackup.id}</strong>
            </div>
            <div>Created: {new Date(selectedBackup.created_at).toLocaleString()}</div>
            <div>Artifact generated: {selectedBackup.generated_at ? new Date(selectedBackup.generated_at).toLocaleString() : 'N/A'}</div>
            <div>Encrypted: {selectedBackup.encrypted ? 'Yes' : 'No'}</div>
            <div>Files in artifact: {selectedBackup.file_count}</div>
            <div>Checksum: {selectedBackup.checksum_sha256}</div>
            <div>Path: {selectedBackup.backup_path}</div>
            <div>Note: {selectedBackup.note || 'N/A'}</div>
            <div style={{ marginTop: '0.5rem' }}>
              <strong>Table row counts</strong>
              <ul className="list" style={{ maxHeight: '180px', overflow: 'auto', marginTop: '0.4rem' }}>
                {Object.entries(selectedBackup.table_counts || {}).map(([tableName, count]) => (
                  <li key={tableName} className="card">
                    {tableName}: {count}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : null}

        {lastRestoreMessage ? <p>{lastRestoreMessage}</p> : null}
        {error ? <p className="error">{error}</p> : null}
      </article>
    </section>
  )
}
