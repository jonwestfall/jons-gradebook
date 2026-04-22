import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'

type AssignmentMeta = {
  id: number
  title: string
  source: string
  due_at?: string | null
  points_possible?: number | null
}

type StudentAssignment = {
  assignment_id: number
  status: string
  score?: number | null
}

type GradebookPayload = {
  course: { id: number; name: string; section_name?: string | null }
  assignments: AssignmentMeta[]
  students: {
    student_id: number
    name: string
    totals: { earned: number; possible: number; percent?: number | null }
    warnings: string[]
    assignments: StudentAssignment[]
  }[]
}

type MatchSuggestion = {
  id: number
  canvas_assignment_title?: string | null
  local_assignment_title?: string | null
  confidence: number
  name_score: number
  due_date_score: number
  points_score: number
  status: 'suggested' | 'confirmed' | 'rejected'
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

function displayScore(entry?: StudentAssignment): string {
  if (!entry) return '—'
  if (entry.score !== null && entry.score !== undefined) return String(entry.score)
  if (entry.status === 'excused') return 'EX'
  if (entry.status === 'missing') return 'M'
  return '—'
}

export function CourseGradebookPage() {
  const { courseId } = useParams<{ courseId: string }>()
  const [gradebook, setGradebook] = useState<GradebookPayload | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [studentSearch, setStudentSearch] = useState('')
  const [assignmentSearch, setAssignmentSearch] = useState('')
  const [rowSortColumn, setRowSortColumn] = useState<string>('student_lastname')
  const [rowSortDirection, setRowSortDirection] = useState<'asc' | 'desc'>('asc')
  const [assignmentSort, setAssignmentSort] = useState<'title_asc' | 'title_desc' | 'due_asc' | 'due_desc' | 'points_desc' | 'points_asc'>('title_asc')
  const [suggestions, setSuggestions] = useState<MatchSuggestion[]>([])
  const [decisions, setDecisions] = useState<MatchDecision[]>([])
  const [matchStatusFilter, setMatchStatusFilter] = useState<'all' | 'suggested' | 'confirmed' | 'rejected'>('all')
  const [matchBusy, setMatchBusy] = useState<number | null>(null)
  const [runningSuggest, setRunningSuggest] = useState(false)
  const [selectedSuggestionIds, setSelectedSuggestionIds] = useState<Set<number>>(new Set())

  async function loadGradebook() {
    if (!courseId) return
    try {
      const data = await api.get<GradebookPayload>(`/courses/${courseId}/gradebook`)
      setGradebook(data)
      setError(null)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  async function loadMatchData() {
    if (!courseId) return
    const statusQuery = matchStatusFilter === 'all' ? '' : `?status=${matchStatusFilter}`
    const [matchRows, decisionRows] = await Promise.all([
      api.get<MatchSuggestion[]>(`/courses/${courseId}/matches${statusQuery}`),
      api.get<MatchDecision[]>(`/courses/${courseId}/matches/history`),
    ])
    setSuggestions(matchRows)
    setDecisions(decisionRows)
  }

  useEffect(() => {
    void loadGradebook()
    void loadMatchData().catch((err) => setError((err as Error).message))
  }, [courseId, matchStatusFilter])

  async function runSuggestions() {
    if (!courseId) return
    setRunningSuggest(true)
    try {
      await api.post(`/courses/${courseId}/matches/suggest`)
      await loadMatchData()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setRunningSuggest(false)
    }
  }

  async function confirmSuggestion(suggestionId: number) {
    setMatchBusy(suggestionId)
    try {
      await api.post(`/courses/matches/${suggestionId}/confirm-canvas`)
      await Promise.all([loadGradebook(), loadMatchData()])
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setMatchBusy(null)
    }
  }

  async function rejectSuggestion(suggestionId: number) {
    setMatchBusy(suggestionId)
    try {
      await api.post(`/courses/matches/${suggestionId}/reject`)
      await loadMatchData()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setMatchBusy(null)
    }
  }

  async function bulkMatchAction(action: 'confirm_canvas' | 'reject') {
    if (selectedSuggestionIds.size === 0) return
    setMatchBusy(-1)
    try {
      await api.post('/courses/matches/bulk', {
        suggestion_ids: Array.from(selectedSuggestionIds),
        action,
      })
      setSelectedSuggestionIds(new Set())
      await Promise.all([loadGradebook(), loadMatchData()])
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setMatchBusy(null)
    }
  }

  const filteredAssignments = useMemo(() => {
    if (!gradebook) return []

    const search = assignmentSearch.trim().toLowerCase()
    let rows = gradebook.assignments.filter((assignment) => assignment.title.toLowerCase().includes(search))

    rows = [...rows].sort((a, b) => {
      if (assignmentSort === 'title_asc') return a.title.localeCompare(b.title)
      if (assignmentSort === 'title_desc') return b.title.localeCompare(a.title)
      if (assignmentSort === 'due_asc') return (a.due_at || '').localeCompare(b.due_at || '')
      if (assignmentSort === 'due_desc') return (b.due_at || '').localeCompare(a.due_at || '')
      if (assignmentSort === 'points_desc') return (b.points_possible || 0) - (a.points_possible || 0)
      return (a.points_possible || 0) - (b.points_possible || 0)
    })

    return rows
  }, [gradebook, assignmentSearch, assignmentSort])

  const filteredStudents = useMemo(() => {
    if (!gradebook) return []

    const search = studentSearch.trim().toLowerCase()
    let rows = gradebook.students.filter((student) => student.name.toLowerCase().includes(search))

    const parseName = (fullName: string) => {
      const parts = fullName.trim().split(/\s+/)
      const first = parts[0] || ''
      const last = parts.length > 1 ? parts[parts.length - 1] : first
      return { first, last }
    }

    const assignmentSortValue = (student: GradebookPayload['students'][number], assignmentId: number): number => {
      const entry = student.assignments.find((item) => item.assignment_id === assignmentId)
      if (!entry) return -4
      if (entry.score !== null && entry.score !== undefined) return entry.score
      if (entry.status === 'excused') return -1
      if (entry.status === 'missing') return -2
      return -3
    }

    rows = [...rows].sort((a, b) => {
      let cmp = 0

      if (rowSortColumn === 'student_lastname') {
        const aName = parseName(a.name)
        const bName = parseName(b.name)
        cmp = aName.last.localeCompare(bName.last) || aName.first.localeCompare(bName.first)
      } else if (rowSortColumn === 'student_name') {
        cmp = a.name.localeCompare(b.name)
      } else if (rowSortColumn === 'percent') {
        cmp = (a.totals.percent ?? -1) - (b.totals.percent ?? -1)
      } else if (rowSortColumn.startsWith('assignment:')) {
        const assignmentId = Number(rowSortColumn.split(':')[1])
        cmp = assignmentSortValue(a, assignmentId) - assignmentSortValue(b, assignmentId)
      } else {
        const aName = parseName(a.name)
        const bName = parseName(b.name)
        cmp = aName.last.localeCompare(bName.last) || aName.first.localeCompare(bName.first)
      }

      return rowSortDirection === 'asc' ? cmp : -cmp
    })

    return rows
  }, [gradebook, studentSearch, rowSortColumn, rowSortDirection])

  if (!gradebook) {
    return (
      <section>
        <h2>Merged Gradebook</h2>
        {error ? <p className="error">{error}</p> : <p>Loading...</p>}
      </section>
    )
  }

  return (
    <section>
      <h2>Merged Gradebook</h2>
      <p>
        Course: <strong>{gradebook.course.name}</strong>
      </p>
      {error ? <p className="error">{error}</p> : null}

      <div className="grid">
        <article className="card">
          <h3>Assignment Match Queue</h3>
          <button onClick={() => void runSuggestions()} disabled={runningSuggest}>
            {runningSuggest ? 'Computing...' : 'Run Match Suggestions'}
          </button>
          <select
            value={matchStatusFilter}
            onChange={(event) => setMatchStatusFilter(event.target.value as 'all' | 'suggested' | 'confirmed' | 'rejected')}
            style={{ marginTop: '0.6rem' }}
          >
            <option value="all">All statuses</option>
            <option value="suggested">Suggested only</option>
            <option value="confirmed">Confirmed only</option>
            <option value="rejected">Rejected only</option>
          </select>
          <div className="list" style={{ maxHeight: '280px', overflow: 'auto', marginTop: '0.6rem' }}>
            {suggestions.length === 0 ? <p>No suggestions yet.</p> : null}
            {suggestions.some((item) => item.status === 'suggested') ? (
              <div className="card">
                <div>Selected: {selectedSuggestionIds.size}</div>
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.35rem' }}>
                  <button onClick={() => void bulkMatchAction('confirm_canvas')} disabled={selectedSuggestionIds.size === 0 || matchBusy !== null}>
                    Confirm Selected
                  </button>
                  <button onClick={() => void bulkMatchAction('reject')} disabled={selectedSuggestionIds.size === 0 || matchBusy !== null}>
                    Reject Selected
                  </button>
                </div>
              </div>
            ) : null}
            {suggestions.map((suggestion) => (
              <div key={suggestion.id} className="card">
                {suggestion.status === 'suggested' ? (
                  <label style={{ display: 'block', marginBottom: '0.35rem' }}>
                    <input
                      type="checkbox"
                      checked={selectedSuggestionIds.has(suggestion.id)}
                      onChange={(event) => {
                        setSelectedSuggestionIds((prev) => {
                          const next = new Set(prev)
                          if (event.target.checked) next.add(suggestion.id)
                          else next.delete(suggestion.id)
                          return next
                        })
                      }}
                    />{' '}
                    Select
                  </label>
                ) : null}
                <div>
                  <strong>{suggestion.canvas_assignment_title || 'Canvas Assignment'}</strong> vs{' '}
                  <strong>{suggestion.local_assignment_title || 'Local Assignment'}</strong>
                </div>
                <div>
                  Confidence {(suggestion.confidence * 100).toFixed(1)}% | Name {(suggestion.name_score * 100).toFixed(0)}% |
                  Due {(suggestion.due_date_score * 100).toFixed(0)}% | Points {(suggestion.points_score * 100).toFixed(0)}%
                </div>
                <div>Status: {suggestion.status}</div>
                {suggestion.status === 'suggested' ? (
                  <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.4rem' }}>
                    <button onClick={() => void confirmSuggestion(suggestion.id)} disabled={matchBusy !== null && matchBusy !== suggestion.id}>
                      Confirm Canvas Authoritative
                    </button>
                    <button onClick={() => void rejectSuggestion(suggestion.id)} disabled={matchBusy !== null && matchBusy !== suggestion.id}>
                      Reject
                    </button>
                  </div>
                ) : null}
              </div>
            ))}
          </div>
        </article>

        <article className="card">
          <h3>Canvas Authority Decision History</h3>
          <div className="list" style={{ maxHeight: '280px', overflow: 'auto' }}>
            {decisions.length === 0 ? <p>No decisions logged yet.</p> : null}
            {decisions.map((decision) => (
              <div key={decision.id} className="card">
                <div>
                  {decision.action}: <strong>{decision.canvas_assignment_title || 'Canvas Assignment'}</strong> vs{' '}
                  <strong>{decision.local_assignment_title || 'Local Assignment'}</strong>
                </div>
                <div>{new Date(decision.created_at).toLocaleString()}</div>
              </div>
            ))}
          </div>
        </article>

        <article className="card">
          <h3>Student Controls</h3>
          <input
            placeholder="Search students"
            value={studentSearch}
            onChange={(event) => setStudentSearch(event.target.value)}
          />
          <select value={rowSortColumn} onChange={(event) => setRowSortColumn(event.target.value)}>
            <option value="student_lastname">Student Last Name</option>
            <option value="student_name">Student Full Name</option>
            <option value="percent">Percent</option>
            {filteredAssignments.map((assignment) => (
              <option key={`sort-${assignment.id}`} value={`assignment:${assignment.id}`}>
                {assignment.title}
              </option>
            ))}
          </select>
          <select
            value={rowSortDirection}
            onChange={(event) => setRowSortDirection(event.target.value as 'asc' | 'desc')}
          >
            <option value="asc">Ascending</option>
            <option value="desc">Descending</option>
          </select>
        </article>

        <article className="card">
          <h3>Assignment Controls</h3>
          <input
            placeholder="Search assignments"
            value={assignmentSearch}
            onChange={(event) => setAssignmentSearch(event.target.value)}
          />
          <select
            value={assignmentSort}
            onChange={(event) => setAssignmentSort(event.target.value as typeof assignmentSort)}
          >
            <option value="title_asc">Title A-Z</option>
            <option value="title_desc">Title Z-A</option>
            <option value="due_asc">Due Date Oldest-Newest</option>
            <option value="due_desc">Due Date Newest-Oldest</option>
            <option value="points_desc">Points High-Low</option>
            <option value="points_asc">Points Low-High</option>
          </select>
        </article>
      </div>

      <div className="card" style={{ overflow: 'auto', maxHeight: '72vh' }}>
        <table style={{ borderCollapse: 'collapse', minWidth: 1000, width: '100%' }}>
          <thead>
            <tr>
              <th
                style={{
                  textAlign: 'left',
                  padding: '0.4rem',
                  position: 'sticky',
                  left: 0,
                  zIndex: 4,
                  background: '#fffaf0',
                }}
              >
                Student
              </th>
              <th style={{ textAlign: 'left', padding: '0.4rem' }}>Percent</th>
              {filteredAssignments.map((assignment) => (
                <th key={assignment.id} style={{ textAlign: 'left', padding: '0.4rem', whiteSpace: 'nowrap' }}>
                  {assignment.title}
                  <div style={{ fontWeight: 400, fontSize: '0.8rem' }}>
                    {assignment.due_at ? new Date(assignment.due_at).toLocaleDateString() : 'No due date'}
                  </div>
                </th>
              ))}
            </tr>
            <tr>
              <th
                style={{
                  textAlign: 'left',
                  padding: '0.4rem',
                  position: 'sticky',
                  left: 0,
                  zIndex: 4,
                  background: '#fffaf0',
                }}
              >
                MaxScore
              </th>
              <th style={{ textAlign: 'left', padding: '0.4rem' }}> </th>
              {filteredAssignments.map((assignment) => (
                <th key={`max-${assignment.id}`} style={{ textAlign: 'left', padding: '0.4rem' }}>
                  {assignment.points_possible ?? 'N/A'}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filteredStudents.map((student) => {
              const byAssignment = new Map(student.assignments.map((entry) => [entry.assignment_id, entry]))
              return (
                <tr key={student.student_id}>
                  <td
                    style={{
                      padding: '0.4rem',
                      borderTop: '1px solid #d5c8aa',
                      position: 'sticky',
                      left: 0,
                      zIndex: 3,
                      background: '#fffaf0',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {student.name}
                  </td>
                  <td style={{ padding: '0.4rem', borderTop: '1px solid #d5c8aa' }}>
                    {student.totals.percent ?? 'N/A'}%
                  </td>
                  {filteredAssignments.map((assignment) => (
                    <td key={`${student.student_id}-${assignment.id}`} style={{ padding: '0.4rem', borderTop: '1px solid #d5c8aa' }}>
                      {displayScore(byAssignment.get(assignment.id))}
                    </td>
                  ))}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}
