import { FormEvent, useEffect, useState } from 'react'
import { api } from '../api/client'
import {
  AppTheme,
  isDemoModeEnabled,
  readAppTheme,
  setAppTheme,
  setDemoModeEnabled,
} from '../utils/uiPreferences'

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

type RestorePreflight = {
  backup_id: number
  backup_generated_at?: string | null
  current_file_count: number
  backup_file_count: number
  file_delta: number
  table_deltas: {
    table: string
    current_rows: number
    backup_rows: number
    delta_rows: number
  }[]
}

type InterventionRule = {
  name: string
  min_score: number
  priority: 'low' | 'medium' | 'high'
  due_days: number
  template: string
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
  const [preflight, setPreflight] = useState<RestorePreflight | null>(null)
  const [documentCategories, setDocumentCategories] = useState<string[]>([])
  const [interactionCategories, setInteractionCategories] = useState<string[]>([])
  const [interventionRules, setInterventionRules] = useState<InterventionRule[]>([])
  const [newDocumentCategory, setNewDocumentCategory] = useState('')
  const [newInteractionCategory, setNewInteractionCategory] = useState('')
  const [ruleName, setRuleName] = useState('missing-and-low-grade')
  const [ruleMinScore, setRuleMinScore] = useState('60')
  const [rulePriority, setRulePriority] = useState<'low' | 'medium' | 'high'>('high')
  const [ruleDueDays, setRuleDueDays] = useState('2')
  const [ruleTemplate, setRuleTemplate] = useState('Follow up with student on missing work and recovery plan.')
  const [demoMode, setDemoMode] = useState(() => isDemoModeEnabled())
  const [theme, setTheme] = useState<AppTheme>(() => readAppTheme())

  async function loadBackups() {
    const data = await api.get<BackupArtifact[]>('/backup/')
    setBackups(data)
    if (data.length > 0 && selectedBackupId === null) {
      const newest = data[0].id
      setSelectedBackupId(newest)
      await loadBackupDetail(newest)
    }
  }

  async function loadOptions() {
    const options = await api.get<{
      document_categories: string[]
      interaction_categories: string[]
      intervention_rules: InterventionRule[]
    }>('/settings/options')
    setDocumentCategories(options.document_categories || [])
    setInteractionCategories(options.interaction_categories || [])
    setInterventionRules(options.intervention_rules || [])
  }

  async function loadBackupDetail(backupId: number) {
    const detail = await api.get<BackupDetail>(`/backup/${backupId}`)
    setSelectedBackup(detail)
    const preflightData = await api.get<RestorePreflight>(`/backup/${backupId}/preflight`)
    setPreflight(preflightData)
  }

  useEffect(() => {
    void Promise.all([loadBackups(), loadOptions()]).catch((err) => setError((err as Error).message))
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

  async function saveCategories(key: 'document_categories' | 'interaction_categories', values: string[]) {
    await api.put(`/settings/options/${key}`, { values })
    await loadOptions()
  }

  async function saveRules(values: InterventionRule[]) {
    await api.put('/settings/options/intervention_rules', { values })
    await loadOptions()
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

      <article className="card settings-preference-panel">
        <div>
          <h3>Interface Preferences</h3>
          <p className="subtitle">
            Adjust presentation without changing app data. Demo mode is browser-local and returns screenshot-safe sample data.
          </p>
        </div>
        <div className="settings-preference-grid">
          <label>
            Theme
            <select
              value={theme}
              onChange={(event) => {
                const nextTheme = event.target.value as AppTheme
                setTheme(nextTheme)
                setAppTheme(nextTheme)
              }}
            >
              <option value="default">Balanced</option>
              <option value="minimal">Minimal</option>
              <option value="contrast">High Contrast</option>
            </select>
          </label>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={demoMode}
              onChange={(event) => {
                const enabled = event.target.checked
                setDemoMode(enabled)
                setDemoModeEnabled(enabled)
              }}
            />
            <span>
              <strong>Demo mode</strong>
              <small>Show example student and class data for GitHub screenshots.</small>
            </span>
          </label>
        </div>
      </article>

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

        {preflight ? (
          <div className="card" style={{ marginTop: '0.75rem' }}>
            <strong>Restore Preflight Comparison</strong>
            <div>
              Files: current {preflight.current_file_count} vs backup {preflight.backup_file_count} (delta{' '}
              {preflight.file_delta >= 0 ? `+${preflight.file_delta}` : preflight.file_delta})
            </div>
            <div className="card" style={{ marginTop: '0.5rem', maxHeight: '220px', overflow: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: '0.35rem' }}>Table</th>
                    <th style={{ textAlign: 'left', padding: '0.35rem' }}>Current</th>
                    <th style={{ textAlign: 'left', padding: '0.35rem' }}>Backup</th>
                    <th style={{ textAlign: 'left', padding: '0.35rem' }}>Delta</th>
                  </tr>
                </thead>
                <tbody>
                  {preflight.table_deltas.map((row) => (
                    <tr key={row.table}>
                      <td style={{ borderTop: '1px solid #d5c8aa', padding: '0.35rem' }}>{row.table}</td>
                      <td style={{ borderTop: '1px solid #d5c8aa', padding: '0.35rem' }}>{row.current_rows}</td>
                      <td style={{ borderTop: '1px solid #d5c8aa', padding: '0.35rem' }}>{row.backup_rows}</td>
                      <td style={{ borderTop: '1px solid #d5c8aa', padding: '0.35rem' }}>
                        {row.delta_rows >= 0 ? `+${row.delta_rows}` : row.delta_rows}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}

        {lastRestoreMessage ? <p>{lastRestoreMessage}</p> : null}
        {error ? <p className="error">{error}</p> : null}
      </article>

      <article className="card" style={{ marginTop: '0.8rem' }}>
        <h3>Document Categories</h3>
        <div className="gradebook-toolbar compact-grid">
          <input
            value={newDocumentCategory}
            onChange={(event) => setNewDocumentCategory(event.target.value)}
            placeholder="Add document category"
          />
          <button
            onClick={() => {
              const value = newDocumentCategory.trim()
              if (!value) return
              void saveCategories('document_categories', [...documentCategories, value])
              setNewDocumentCategory('')
            }}
          >
            Add
          </button>
        </div>
        <ul className="list compact">
          {documentCategories.map((category) => (
            <li key={category} className="card">
              {category}{' '}
              <button onClick={() => void saveCategories('document_categories', documentCategories.filter((item) => item !== category))}>
                Remove
              </button>
            </li>
          ))}
        </ul>
      </article>

      <article className="card" style={{ marginTop: '0.8rem' }}>
        <h3>Interaction Categories</h3>
        <div className="gradebook-toolbar compact-grid">
          <input
            value={newInteractionCategory}
            onChange={(event) => setNewInteractionCategory(event.target.value)}
            placeholder="Add interaction category"
          />
          <button
            onClick={() => {
              const value = newInteractionCategory.trim()
              if (!value) return
              void saveCategories('interaction_categories', [...interactionCategories, value])
              setNewInteractionCategory('')
            }}
          >
            Add
          </button>
        </div>
        <ul className="list compact">
          {interactionCategories.map((category) => (
            <li key={category} className="card">
              {category}{' '}
              <button
                onClick={() =>
                  void saveCategories('interaction_categories', interactionCategories.filter((item) => item !== category))
                }
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      </article>

      <article className="card" style={{ marginTop: '0.8rem' }}>
        <h3>Intervention Rules</h3>
        <p className="subtitle">Rules generate tasks from student risk signals when you run the intervention engine.</p>
        <div className="gradebook-toolbar compact-grid">
          <input value={ruleName} onChange={(event) => setRuleName(event.target.value)} placeholder="Rule name" />
          <input
            type="number"
            min="1"
            max="100"
            value={ruleMinScore}
            onChange={(event) => setRuleMinScore(event.target.value)}
            placeholder="Minimum risk score"
          />
          <select value={rulePriority} onChange={(event) => setRulePriority(event.target.value as 'low' | 'medium' | 'high')}>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <input
            type="number"
            min="1"
            max="30"
            value={ruleDueDays}
            onChange={(event) => setRuleDueDays(event.target.value)}
            placeholder="Due days"
          />
          <input
            value={ruleTemplate}
            onChange={(event) => setRuleTemplate(event.target.value)}
            placeholder="Task note template"
          />
          <button
            onClick={() => {
              const nextRule: InterventionRule = {
                name: ruleName.trim() || 'custom-rule',
                min_score: Number(ruleMinScore || '60'),
                priority: rulePriority,
                due_days: Number(ruleDueDays || '2'),
                template: ruleTemplate.trim() || 'Follow up with student.',
              }
              void saveRules([nextRule, ...interventionRules.filter((rule) => rule.name !== nextRule.name)])
            }}
          >
            Add / Update Rule
          </button>
        </div>
        <ul className="list compact">
          {interventionRules.map((rule) => (
            <li key={rule.name} className="card">
              <strong>{rule.name}</strong> (min score {rule.min_score}, {rule.priority}, due +{rule.due_days}d)
              <div className="table-subtle">{rule.template}</div>
              <button
                onClick={() => {
                  void saveRules(interventionRules.filter((item) => item.name !== rule.name))
                }}
              >
                Remove
              </button>
            </li>
          ))}
        </ul>
      </article>
    </section>
  )
}
