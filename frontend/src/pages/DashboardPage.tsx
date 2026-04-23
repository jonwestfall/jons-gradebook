import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

type DashboardSummary = {
  cards: {
    needs_grading: number
    missing_late_followup: number
    out_of_sync_overrides: number
    unread_alerts: number
    upcoming_advising_followups: number
  }
  top_risk_students: {
    student_id: number
    student_name: string
    risk_score: number
    level: string
    missing_assignments: number
    current_percent?: number | null
    days_since_interaction?: number | null
    reasons: string[]
  }[]
  latest_sync?: {
    id: number
    status: string
    started_at: string
    finished_at?: string | null
  } | null
}

type RuleRunResult = {
  created_count: number
  skipped_count: number
  evaluated_students: number
}

const cardConfig = [
  {
    key: 'needs_grading' as const,
    title: 'Needs Grading / Match Review',
    description: 'Unresolved assignment matching work.',
    href: '/courses',
    cta: 'Open Courses',
  },
  {
    key: 'missing_late_followup' as const,
    title: 'Missing / Late Follow-up',
    description: 'Students at medium/high risk requiring outreach.',
    href: '/tasks?status=open',
    cta: 'Open Tasks',
  },
  {
    key: 'out_of_sync_overrides' as const,
    title: 'Out-of-sync Overrides',
    description: 'Local grade overrides that differ from Canvas source.',
    href: '/courses',
    cta: 'Review Gradebooks',
  },
  {
    key: 'unread_alerts' as const,
    title: 'Unread Alerts',
    description: 'Active student alerts requiring review.',
    href: '/students',
    cta: 'Open Students',
  },
  {
    key: 'upcoming_advising_followups' as const,
    title: 'Upcoming Advising Follow-ups',
    description: 'Tasks due soon for advising workflows.',
    href: '/advising',
    cta: 'Open Advising',
  },
]

export function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function loadSummary() {
    const data = await api.get<DashboardSummary>('/dashboard/summary')
    setSummary(data)
  }

  useEffect(() => {
    void loadSummary().catch((err) => setError((err as Error).message))
  }, [])

  async function runInterventions() {
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      const result = await api.post<RuleRunResult>('/tasks/rules/run')
      await loadSummary()
      setMessage(
        `Intervention rules evaluated ${result.evaluated_students} students and created ${result.created_count} tasks (${result.skipped_count} skipped).`,
      )
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const sortedRisk = useMemo(() => {
    return [...(summary?.top_risk_students || [])].sort((a, b) => b.risk_score - a.risk_score)
  }, [summary])

  if (!summary) {
    return (
      <section>
        <h2>Action Dashboard</h2>
        {error ? <p className="error">{error}</p> : <p>Loading dashboard...</p>}
      </section>
    )
  }

  return (
    <section>
      <h2>Action Dashboard</h2>
      <p className="subtitle">Prioritized queues for grading, outreach, sync cleanup, and advising follow-ups.</p>

      <article className="card action-bar">
        <div className="gradebook-toolbar compact-grid">
          <button type="button" onClick={() => void loadSummary()} disabled={busy}>Refresh Dashboard</button>
          <button type="button" onClick={() => void runInterventions()} disabled={busy}>
            {busy ? 'Running...' : 'Run Intervention Triggers'}
          </button>
          {summary.latest_sync ? (
            <div className="muted-badge">
              Latest Sync: {summary.latest_sync.status} @ {new Date(summary.latest_sync.started_at).toLocaleString()}
            </div>
          ) : (
            <div className="muted-badge">No sync history yet</div>
          )}
        </div>
      </article>

      <div className="grid" style={{ marginTop: '0.8rem' }}>
        {cardConfig.map((card) => (
          <article key={card.key} className="card">
            <h3>{card.title}</h3>
            <p className="subtitle">{card.description}</p>
            <p style={{ fontSize: '1.45rem', fontWeight: 700 }}>{summary.cards[card.key]}</p>
            <Link to={card.href}>{card.cta}</Link>
          </article>
        ))}
      </div>

      <article className="card" style={{ marginTop: '0.8rem' }}>
        <h3>Top Risk Students</h3>
        <table className="students-grid-table prioritize-mobile">
          <thead>
            <tr>
              <th>Student</th>
              <th>Risk</th>
              <th>Missing</th>
              <th>Current %</th>
              <th>Days Since Interaction</th>
              <th>Signals</th>
            </tr>
          </thead>
          <tbody>
            {sortedRisk.map((row) => (
              <tr key={row.student_id}>
                <td><Link to={`/students/${row.student_id}`}>{row.student_name}</Link></td>
                <td>{row.level} ({row.risk_score})</td>
                <td>{row.missing_assignments}</td>
                <td>{row.current_percent ?? 'N/A'}</td>
                <td>{row.days_since_interaction ?? 'N/A'}</td>
                <td>{row.reasons.join(', ') || 'No risk flags'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {sortedRisk.length === 0 ? <p>No risk signals available yet.</p> : null}
      </article>

      {message ? <p>{message}</p> : null}
      {error ? <p className="error">{error}</p> : null}
    </section>
  )
}
