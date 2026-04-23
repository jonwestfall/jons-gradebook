import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import { readLocalStorage, writeLocalStorage } from '../utils/storage'

type Student = {
  id: number
  first_name: string
  last_name: string
  email?: string | null
  phone_number?: string | null
  student_number?: string | null
  has_class_enrollment: boolean
  is_advisee: boolean
  latest_interaction_at?: string | null
}

type SavedStudentView = {
  name: string
  search: string
  scope: 'all' | 'in_classes' | 'advisees'
  sortBy: 'last_name' | 'recent_interactions'
}

export function StudentsPage() {
  const [students, setStudents] = useState<Student[]>([])
  const [search, setSearch] = useState('')
  const [scope, setScope] = useState<'all' | 'in_classes' | 'advisees'>('all')
  const [sortBy, setSortBy] = useState<'last_name' | 'recent_interactions'>('last_name')
  const [savedViews, setSavedViews] = useState<SavedStudentView[]>([])
  const [viewName, setViewName] = useState('')

  const storageKey = 'students_saved_views'

  useEffect(() => {
    api.get<Student[]>('/students/').then(setStudents).catch(console.error)
    const raw = readLocalStorage(storageKey)
    if (raw) {
      try {
        const parsed = JSON.parse(raw) as SavedStudentView[]
        if (Array.isArray(parsed)) setSavedViews(parsed)
      } catch {
        // ignore parse errors
      }
    }
  }, [])

  function persistViews(next: SavedStudentView[]) {
    setSavedViews(next)
    writeLocalStorage(storageKey, JSON.stringify(next))
  }

  function saveView() {
    const name = viewName.trim()
    if (!name) return
    const next: SavedStudentView = { name, search, scope, sortBy }
    const merged = [next, ...savedViews.filter((view) => view.name.toLowerCase() !== name.toLowerCase())].slice(0, 12)
    persistViews(merged)
    setViewName('')
  }

  function applyView(view: SavedStudentView) {
    setSearch(view.search)
    setScope(view.scope)
    setSortBy(view.sortBy)
  }

  function deleteView(name: string) {
    persistViews(savedViews.filter((view) => view.name !== name))
  }

  const visibleStudents = useMemo(() => {
    const term = search.trim().toLowerCase()

    let rows = students.filter((student) => {
      const fullName = `${student.first_name} ${student.last_name}`.toLowerCase()
      const haystack = [fullName, student.email || '', student.student_number || '', student.phone_number || ''].join(' ').toLowerCase()
      if (term && !haystack.includes(term)) return false
      if (scope === 'in_classes' && !student.has_class_enrollment) return false
      if (scope === 'advisees' && !student.is_advisee) return false
      return true
    })

    rows = [...rows].sort((a, b) => {
      if (sortBy === 'last_name') {
        const byLast = a.last_name.localeCompare(b.last_name)
        if (byLast !== 0) return byLast
        return a.first_name.localeCompare(b.first_name)
      }
      const aTs = a.latest_interaction_at ? Date.parse(a.latest_interaction_at) : 0
      const bTs = b.latest_interaction_at ? Date.parse(b.latest_interaction_at) : 0
      return bTs - aTs
    })

    return rows
  }, [scope, search, sortBy, students])

  return (
    <section>
      <h2>Students</h2>
      <article className="card">
        <div className="gradebook-toolbar compact-grid">
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search name, email, student number, or phone"
          />
          <select value={scope} onChange={(event) => setScope(event.target.value as typeof scope)}>
            <option value="all">All Students</option>
            <option value="in_classes">Students in Classes</option>
            <option value="advisees">Advisees</option>
          </select>
          <select value={sortBy} onChange={(event) => setSortBy(event.target.value as typeof sortBy)}>
            <option value="last_name">Sort: Last Name</option>
            <option value="recent_interactions">Sort: Most Recent Interactions</option>
          </select>
        </div>
        <div className="gradebook-toolbar compact-grid" style={{ marginTop: '0.5rem' }}>
          <input
            value={viewName}
            onChange={(event) => setViewName(event.target.value)}
            placeholder="Save this student view as..."
          />
          <button type="button" onClick={saveView}>Save View</button>
        </div>
        <div className="chip-row" style={{ marginTop: '0.5rem' }}>
          {savedViews.map((view) => (
            <span key={view.name} className="chip">
              <button type="button" onClick={() => applyView(view)}>{view.name}</button>
              <button type="button" onClick={() => deleteView(view.name)} title={`Delete view ${view.name}`}>x</button>
            </span>
          ))}
          {savedViews.length === 0 ? <span className="table-subtle">No saved views yet.</span> : null}
        </div>
      </article>

      <article className="card students-grid-wrap">
        <table className="students-grid-table prioritize-mobile">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Student #</th>
              <th>In Class</th>
              <th>Advisee</th>
              <th>Recent Interaction</th>
            </tr>
          </thead>
          <tbody>
            {visibleStudents.map((student) => (
              <tr key={student.id}>
                <td><Link to={`/students/${student.id}`}>{student.last_name}, {student.first_name}</Link></td>
                <td>{student.email || '—'}</td>
                <td>{student.phone_number || '—'}</td>
                <td>{student.student_number || '—'}</td>
                <td>{student.has_class_enrollment ? 'Yes' : 'No'}</td>
                <td>{student.is_advisee ? 'Yes' : 'No'}</td>
                <td>{student.latest_interaction_at ? new Date(student.latest_interaction_at).toLocaleString() : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {visibleStudents.length === 0 ? <p>No students found for current filters.</p> : null}
      </article>
    </section>
  )
}
