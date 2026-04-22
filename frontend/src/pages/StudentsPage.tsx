import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

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

export function StudentsPage() {
  const [students, setStudents] = useState<Student[]>([])
  const [search, setSearch] = useState('')
  const [scope, setScope] = useState<'all' | 'in_classes' | 'advisees'>('all')
  const [sortBy, setSortBy] = useState<'last_name' | 'recent_interactions'>('last_name')

  useEffect(() => {
    api.get<Student[]>('/students/').then(setStudents).catch(console.error)
  }, [])

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
      </article>

      <article className="card students-grid-wrap">
        <table className="students-grid-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Phone</th>
              <th>Student #</th>
              <th>In Class</th>
              <th>Advisee</th>
              <th>Recent Interaction</th>
              <th>Profile</th>
            </tr>
          </thead>
          <tbody>
            {visibleStudents.map((student) => (
              <tr key={student.id}>
                <td>{student.last_name}, {student.first_name}</td>
                <td>{student.email || '—'}</td>
                <td>{student.phone_number || '—'}</td>
                <td>{student.student_number || '—'}</td>
                <td>{student.has_class_enrollment ? 'Yes' : 'No'}</td>
                <td>{student.is_advisee ? 'Yes' : 'No'}</td>
                <td>{student.latest_interaction_at ? new Date(student.latest_interaction_at).toLocaleString() : '—'}</td>
                <td><Link to={`/students/${student.id}`}>Open</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
        {visibleStudents.length === 0 ? <p>No students found for current filters.</p> : null}
      </article>
    </section>
  )
}
