import { FormEvent, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'

type Profile = {
  student: {
    id: number
    name: string
    email?: string | null
    student_number?: string | null
    notes?: string | null
  }
  priority_sections: string[]
  alerts: {
    id: number
    title: string
    message: string
    severity: string
    status: string
    is_pinned: boolean
    created_at: string
  }[]
  flags_tags: { id: number; name: string }[]
  attendance_summary: {
    present: number
    absent: number
    tardy: number
    excused: number
    total_records: number
  }
  courses: {
    course_id: number
    name: string
    section_name?: string | null
    totals: { earned: number; possible: number; percent?: number | null }
    assignments: {
      assignment_id: number
      title: string
      source: string
      due_at?: string | null
      points_possible?: number | null
      score?: number | null
      status: string
      percent?: number | null
    }[]
  }[]
  grade_overview: {
    course_id: number
    course_name: string
    earned: number
    possible: number
    percent?: number | null
  }[]
  recent_interactions: { id: number; type: string; summary: string; occurred_at: string }[]
  advising_meetings: { id: number; meeting_at: string; mode: string; summary?: string | null }[]
}

export function StudentProfilePage() {
  const { studentId } = useParams<{ studentId: string }>()
  const [profile, setProfile] = useState<Profile | null>(null)
  const [notesDraft, setNotesDraft] = useState('')
  const [newTag, setNewTag] = useState('')
  const [alertTitle, setAlertTitle] = useState('')
  const [alertMessage, setAlertMessage] = useState('')
  const [alertSeverity, setAlertSeverity] = useState('medium')

  async function loadProfile() {
    if (!studentId) return
    const data = await api.get<Profile>(`/students/${studentId}/profile`)
    setProfile(data)
    setNotesDraft(data.student.notes || '')
  }

  useEffect(() => {
    void loadProfile()
  }, [studentId])

  async function saveNotes(event: FormEvent) {
    event.preventDefault()
    if (!studentId) return
    await api.patch(`/students/${studentId}/notes`, { notes: notesDraft })
    await loadProfile()
  }

  async function addTag(event: FormEvent) {
    event.preventDefault()
    if (!studentId || !newTag.trim()) return
    await api.post(`/students/${studentId}/tags`, { name: newTag.trim() })
    setNewTag('')
    await loadProfile()
  }

  async function removeTag(tagId: number) {
    if (!studentId) return
    await api.delete(`/students/${studentId}/tags/${tagId}`)
    await loadProfile()
  }

  async function addAlert(event: FormEvent) {
    event.preventDefault()
    if (!studentId || !alertTitle.trim() || !alertMessage.trim()) return
    await api.post(`/students/${studentId}/alerts`, {
      title: alertTitle.trim(),
      message: alertMessage.trim(),
      severity: alertSeverity,
      is_pinned: false,
    })
    setAlertTitle('')
    setAlertMessage('')
    setAlertSeverity('medium')
    await loadProfile()
  }

  async function resolveAlert(alertId: number) {
    if (!studentId) return
    await api.patch(`/students/${studentId}/alerts/${alertId}`, { status: 'resolved' })
    await loadProfile()
  }

  if (!profile) {
    return <p>Loading profile...</p>
  }

  return (
    <section>
      <h2>{profile.student.name}</h2>
      <p>Email: {profile.student.email || 'N/A'}</p>
      <p>Student number: {profile.student.student_number || 'N/A'}</p>
      <p>Priority order: {profile.priority_sections.join(' > ')}</p>

      <div className="grid">
        <article className="card">
          <h3>Alerts</h3>
          <form className="form" onSubmit={addAlert}>
            <input placeholder="Alert title" value={alertTitle} onChange={(e) => setAlertTitle(e.target.value)} required />
            <textarea
              placeholder="Alert message"
              value={alertMessage}
              onChange={(e) => setAlertMessage(e.target.value)}
              required
            />
            <select value={alertSeverity} onChange={(e) => setAlertSeverity(e.target.value)}>
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
            <button type="submit">Add Alert</button>
          </form>
          <ul className="list">
            {profile.alerts.map((alert) => (
              <li key={alert.id} className="card">
                <strong>{alert.title}</strong>
                <div>{alert.message}</div>
                <div>
                  {alert.severity} / {alert.status}
                </div>
                {alert.status !== 'resolved' ? <button onClick={() => resolveAlert(alert.id)}>Resolve</button> : null}
              </li>
            ))}
          </ul>
        </article>

        <article className="card">
          <h3>Flags / Tags</h3>
          <form className="form" onSubmit={addTag}>
            <input placeholder="Add tag" value={newTag} onChange={(e) => setNewTag(e.target.value)} required />
            <button type="submit">Add Tag</button>
          </form>
          <ul className="list">
            {profile.flags_tags.map((tag) => (
              <li key={tag.id} className="card">
                {tag.name} <button onClick={() => removeTag(tag.id)}>Remove</button>
              </li>
            ))}
          </ul>
        </article>

        <article className="card">
          <h3>Attendance Summary</h3>
          <div>Present: {profile.attendance_summary.present}</div>
          <div>Absent: {profile.attendance_summary.absent}</div>
          <div>Tardy: {profile.attendance_summary.tardy}</div>
          <div>Excused: {profile.attendance_summary.excused}</div>
          <div>Total: {profile.attendance_summary.total_records}</div>
        </article>
      </div>

      <h3>Notes</h3>
      <form className="form" onSubmit={saveNotes}>
        <textarea value={notesDraft} onChange={(event) => setNotesDraft(event.target.value)} placeholder="Student notes" />
        <button type="submit">Save Notes</button>
      </form>

      <h3>Grade Overview</h3>
      <ul className="list">
        {profile.grade_overview.map((course) => (
          <li key={course.course_id} className="card">
            <strong>{course.course_name}</strong> - {course.earned}/{course.possible} ({course.percent ?? 'N/A'}%)
          </li>
        ))}
      </ul>

      <h3>Courses</h3>
      <ul className="list">
        {profile.courses.map((course) => (
          <li key={course.course_id} className="card">
            <strong>
              {course.name} ({course.section_name || 'No section'})
            </strong>
            <div>
              Course Total: {course.totals.earned}/{course.totals.possible} ({course.totals.percent ?? 'N/A'}%)
            </div>
            <div className="card" style={{ marginTop: '0.6rem', overflowX: 'auto' }}>
              <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 720 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: '0.35rem' }}>Assignment</th>
                    <th style={{ textAlign: 'left', padding: '0.35rem' }}>Due</th>
                    <th style={{ textAlign: 'left', padding: '0.35rem' }}>Score</th>
                    <th style={{ textAlign: 'left', padding: '0.35rem' }}>Points</th>
                    <th style={{ textAlign: 'left', padding: '0.35rem' }}>Percent</th>
                    <th style={{ textAlign: 'left', padding: '0.35rem' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {course.assignments.map((assignment) => (
                    <tr key={assignment.assignment_id}>
                      <td style={{ borderTop: '1px solid #d5c8aa', padding: '0.35rem' }}>{assignment.title}</td>
                      <td style={{ borderTop: '1px solid #d5c8aa', padding: '0.35rem' }}>
                        {assignment.due_at ? new Date(assignment.due_at).toLocaleDateString() : 'N/A'}
                      </td>
                      <td style={{ borderTop: '1px solid #d5c8aa', padding: '0.35rem' }}>
                        {assignment.score ?? '—'}
                      </td>
                      <td style={{ borderTop: '1px solid #d5c8aa', padding: '0.35rem' }}>
                        {assignment.points_possible ?? 'N/A'}
                      </td>
                      <td style={{ borderTop: '1px solid #d5c8aa', padding: '0.35rem' }}>
                        {assignment.percent ?? 'N/A'}%
                      </td>
                      <td style={{ borderTop: '1px solid #d5c8aa', padding: '0.35rem' }}>{assignment.status}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </li>
        ))}
      </ul>

      <h3>Recent Interactions</h3>
      <ul className="list">
        {profile.recent_interactions.map((interaction) => (
          <li key={interaction.id} className="card">
            {interaction.type} - {interaction.summary}
          </li>
        ))}
      </ul>
    </section>
  )
}
