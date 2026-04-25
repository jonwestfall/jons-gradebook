import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api } from '../api/client'

type Course = {
  id: number
  name: string
  section_name?: string | null
}

type MatchStatus = 'suggested' | 'confirmed' | 'rejected'

type MatchSuggestion = {
  id: number
  course_id: number
  canvas_assignment_title?: string | null
  local_assignment_title?: string | null
  confidence: number
  name_score: number
  due_date_score: number
  points_score: number
  status: MatchStatus
  rationale?: string | null
  updated_at: string
}

type MatchDecision = {
  id: number
  suggestion_id: number
  action: string
  note?: string | null
  created_at: string
  canvas_assignment_title?: string | null
  local_assignment_title?: string | null
}

function confidenceBand(confidence: number): 'high' | 'medium' | 'low' {
  if (confidence >= 0.85) return 'high'
  if (confidence >= 0.65) return 'medium'
  return 'low'
}

export function CourseMatchWorkbenchPage() {
  const { courseId } = useParams<{ courseId: string }>()

  const [courses, setCourses] = useState<Course[]>([])
  const [selectedCourseId, setSelectedCourseId] = useState<number | null>(courseId ? Number(courseId) : null)
  const [matches, setMatches] = useState<MatchSuggestion[]>([])
  const [history, setHistory] = useState<MatchDecision[]>([])
  const [selectedIds, setSelectedIds] = useState<number[]>([])

  const [statusFilter, setStatusFilter] = useState<string>('suggested')
  const [bandFilter, setBandFilter] = useState<'all' | 'high' | 'medium' | 'low'>('all')
  const [search, setSearch] = useState('')

  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const workflowStartedAt = useMemo(() => Date.now(), [])

  async function loadCourses() {
    const rows = await api.get<Course[]>('/courses/')
    setCourses(rows)
    if (!selectedCourseId && rows.length > 0) {
      setSelectedCourseId(rows[0].id)
    }
  }

  async function loadCourseData(nextCourseId?: number | null) {
    const id = nextCourseId ?? selectedCourseId
    if (!id) return

    const statusQuery = statusFilter ? `?status=${encodeURIComponent(statusFilter)}` : ''
    const [matchRows, historyRows] = await Promise.all([
      api.get<MatchSuggestion[]>(`/courses/${id}/matches${statusQuery}`),
      api.get<MatchDecision[]>(`/courses/${id}/matches/history`),
    ])
    setMatches(matchRows)
    setHistory(historyRows)
    setSelectedIds([])
  }

  useEffect(() => {
    void loadCourses().catch((err) => setError((err as Error).message))
  }, [])

  useEffect(() => {
    if (!selectedCourseId) return
    void loadCourseData(selectedCourseId).catch((err) => setError((err as Error).message))
  }, [selectedCourseId, statusFilter])

  const visibleMatches = useMemo(() => {
    const query = search.trim().toLowerCase()
    return matches.filter((match) => {
      if (bandFilter !== 'all' && confidenceBand(match.confidence) !== bandFilter) return false
      if (!query) return true
      const haystack = `${match.canvas_assignment_title || ''} ${match.local_assignment_title || ''} ${match.rationale || ''}`.toLowerCase()
      return haystack.includes(query)
    })
  }, [matches, bandFilter, search])

  const stats = useMemo(() => {
    const byBand = { high: 0, medium: 0, low: 0 }
    for (const row of matches) {
      byBand[confidenceBand(row.confidence)] += 1
    }
    return byBand
  }, [matches])

  function toggleSelect(id: number) {
    setSelectedIds((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]))
  }

  async function suggestMatches() {
    if (!selectedCourseId) return
    setBusy(true)
    setError(null)
    try {
      await api.post(`/courses/${selectedCourseId}/matches/suggest`)
      await loadCourseData(selectedCourseId)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function applyBulk(action: 'confirm_canvas' | 'reject') {
    if (!selectedCourseId || selectedIds.length === 0) return
    setBusy(true)
    setError(null)
    try {
      await api.post('/courses/matches/bulk', {
        action,
        suggestion_ids: selectedIds,
        note: action === 'reject' ? 'Rejected from instructor workbench.' : null,
      })
      await api.post('/tasks/benchmarks', {
        workflow: 'match_resolution',
        action: `bulk_${action}`,
        duration_ms: Date.now() - workflowStartedAt,
        context_json: { course_id: selectedCourseId, count: selectedIds.length },
      })
      await loadCourseData(selectedCourseId)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function decideSingle(suggestionId: number, action: 'confirm_canvas' | 'reject') {
    setBusy(true)
    setError(null)
    try {
      if (action === 'confirm_canvas') {
        await api.post(`/courses/matches/${suggestionId}/confirm-canvas`)
      } else {
        await api.post(`/courses/matches/${suggestionId}/reject`)
      }
      await api.post('/tasks/benchmarks', {
        workflow: 'match_resolution',
        action,
        duration_ms: Date.now() - workflowStartedAt,
        context_json: { course_id: selectedCourseId, suggestion_id: suggestionId },
      })
      await loadCourseData(selectedCourseId)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <h2>Match Queue Workbench</h2>
      <p className="subtitle">Resolve Canvas-vs-local assignment matches with confidence bands and bulk actions.</p>

      <article className="card action-bar">
        <div className="gradebook-toolbar compact-grid">
          <select
            value={selectedCourseId ?? ''}
            onChange={(event) => {
              const nextId = Number(event.target.value)
              setSelectedCourseId(nextId)
            }}
          >
            {(courses || []).map((course) => (
              <option key={course.id} value={course.id}>
                {course.name}
                {course.section_name ? ` (${course.section_name})` : ''}
              </option>
            ))}
          </select>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="suggested">Suggested</option>
            <option value="confirmed">Confirmed Canvas</option>
            <option value="rejected">Rejected</option>
            <option value="">All statuses</option>
          </select>
          <select value={bandFilter} onChange={(event) => setBandFilter(event.target.value as typeof bandFilter)}>
            <option value="all">All confidence bands</option>
            <option value="high">High confidence</option>
            <option value="medium">Medium confidence</option>
            <option value="low">Low confidence</option>
          </select>
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search assignment names" />
          <button type="button" onClick={() => void suggestMatches()} disabled={busy || !selectedCourseId}>
            {busy ? 'Working...' : 'Refresh Suggestions'}
          </button>
          <button type="button" onClick={() => void applyBulk('confirm_canvas')} disabled={busy || selectedIds.length === 0}>
            Bulk Confirm ({selectedIds.length})
          </button>
          <button type="button" onClick={() => void applyBulk('reject')} disabled={busy || selectedIds.length === 0}>
            Bulk Reject ({selectedIds.length})
          </button>
          {selectedCourseId ? (
            <Link to={`/courses/${selectedCourseId}/gradebook`} className="nav-link" style={{ display: 'inline-block' }}>
              Open Gradebook
            </Link>
          ) : null}
        </div>
        <div className="chip-row" style={{ marginTop: '0.5rem' }}>
          <span className="chip">High: {stats.high}</span>
          <span className="chip">Medium: {stats.medium}</span>
          <span className="chip">Low: {stats.low}</span>
        </div>
      </article>

      <article className="card students-grid-wrap" style={{ marginTop: '0.8rem' }}>
        <table className="students-grid-table">
          <thead>
            <tr>
              <th>Select</th>
              <th>Confidence</th>
              <th>Canvas Assignment</th>
              <th>Local Assignment</th>
              <th>Status</th>
              <th>Rationale</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {visibleMatches.map((match) => (
              <tr key={match.id}>
                <td>
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(match.id)}
                    onChange={() => toggleSelect(match.id)}
                    disabled={match.status !== 'suggested'}
                  />
                </td>
                <td>
                  {(match.confidence * 100).toFixed(1)}%
                  <div className="table-subtle">{confidenceBand(match.confidence)} confidence</div>
                </td>
                <td>{match.canvas_assignment_title || '—'}</td>
                <td>{match.local_assignment_title || '—'}</td>
                <td>{match.status.replace('_', ' ')}</td>
                <td>{match.rationale || '—'}</td>
                <td>
                  <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap' }}>
                    <button
                      type="button"
                      onClick={() => void decideSingle(match.id, 'confirm_canvas')}
                      disabled={busy || match.status !== 'suggested'}
                    >
                      Confirm
                    </button>
                    <button
                      type="button"
                      onClick={() => void decideSingle(match.id, 'reject')}
                      disabled={busy || match.status !== 'suggested'}
                    >
                      Reject
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {visibleMatches.length === 0 ? <p>No suggestions found for current filters.</p> : null}
      </article>

      <article className="card" style={{ marginTop: '0.8rem' }}>
        <h3>Decision History</h3>
        <ul className="list compact">
          {history.map((item) => (
            <li key={item.id} className="card">
              <strong>{item.action.replace('_', ' ')}</strong> · {new Date(item.created_at).toLocaleString()}
              <div className="table-subtle">
                Canvas: {item.canvas_assignment_title || '—'} | Local: {item.local_assignment_title || '—'}
              </div>
              {item.note ? <div className="table-subtle">{item.note}</div> : null}
            </li>
          ))}
        </ul>
        {history.length === 0 ? <p>No decisions yet.</p> : null}
      </article>

      {error ? <p className="error">{error}</p> : null}
    </section>
  )
}
