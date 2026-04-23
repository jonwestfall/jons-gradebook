import { FormEvent, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { api } from '../api/client'

type Profile = {
  student: {
    id: number
    name: string
    first_name: string
    last_name: string
    email?: string | null
    phone_number?: string | null
    student_number?: string | null
    notes?: string | null
    is_advisee?: boolean
    advisee_id?: number | null
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
  student_documents: {
    id: number
    title: string
    category?: string | null
    document_type: string
    current_version: number
    updated_at?: string | null
    latest_filename?: string | null
    latest_size_bytes?: number | null
  }[]
  recent_interactions: { id: number; type: string; summary: string; occurred_at: string }[]
  advising_meetings: { id: number; meeting_at: string; mode: string; summary?: string | null }[]
}

export function StudentProfilePage() {
  const { studentId } = useParams<{ studentId: string }>()
  const [profile, setProfile] = useState<Profile | null>(null)
  const [notesDraft, setNotesDraft] = useState('')
  const [firstNameDraft, setFirstNameDraft] = useState('')
  const [lastNameDraft, setLastNameDraft] = useState('')
  const [emailDraft, setEmailDraft] = useState('')
  const [phoneDraft, setPhoneDraft] = useState('')
  const [newTag, setNewTag] = useState('')
  const [alertTitle, setAlertTitle] = useState('')
  const [alertMessage, setAlertMessage] = useState('')
  const [alertSeverity, setAlertSeverity] = useState('medium')
  const [markingAdvisee, setMarkingAdvisee] = useState(false)
  const [unmarkingAdvisee, setUnmarkingAdvisee] = useState(false)
  const [documentTitle, setDocumentTitle] = useState('')
  const [documentFile, setDocumentFile] = useState<File | null>(null)
  const [documentLinkStudentIds, setDocumentLinkStudentIds] = useState<string[]>([])
  const [documentTargets, setDocumentTargets] = useState<{ id: number; name: string; email?: string | null }[]>([])

  async function loadProfile() {
    if (!studentId) return
    const data = await api.get<Profile>(`/students/${studentId}/profile`)
    setProfile(data)
    setNotesDraft(data.student.notes || '')
    setFirstNameDraft(data.student.first_name || '')
    setLastNameDraft(data.student.last_name || '')
    setEmailDraft(data.student.email || '')
    setPhoneDraft(data.student.phone_number || '')
    setDocumentLinkStudentIds((current) => (current.length > 0 ? current : [String(data.student.id)]))
  }

  async function loadDocumentTargets() {
    const response = await api.get<{ students: { id: number; name: string; email?: string | null }[] }>('/documents/targets')
    setDocumentTargets(response.students)
  }

  useEffect(() => {
    void loadProfile()
  }, [studentId])

  useEffect(() => {
    void loadDocumentTargets()
  }, [])

  async function saveNotes(event: FormEvent) {
    event.preventDefault()
    if (!studentId) return
    await api.patch(`/students/${studentId}/notes`, { notes: notesDraft })
    await loadProfile()
  }

  async function saveProfileFields(event: FormEvent) {
    event.preventDefault()
    if (!studentId) return
    await api.patch(`/students/${studentId}/profile-fields`, {
      first_name: firstNameDraft.trim(),
      last_name: lastNameDraft.trim(),
      email: emailDraft.trim() || null,
      phone_number: phoneDraft.trim() || null,
    })
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

  async function markAsAdvisee() {
    if (!studentId) return
    setMarkingAdvisee(true)
    try {
      await api.post(`/students/${studentId}/mark-advisee`)
      await loadProfile()
    } finally {
      setMarkingAdvisee(false)
    }
  }

  async function unmarkAsAdvisee() {
    if (!studentId) return
    setUnmarkingAdvisee(true)
    try {
      await api.post(`/students/${studentId}/unmark-advisee`)
      await loadProfile()
    } finally {
      setUnmarkingAdvisee(false)
    }
  }

  async function uploadDocument(event: FormEvent) {
    event.preventDefault()
    if (!studentId || !documentFile) return

    const form = new FormData()
    form.append('owner_type', 'student')
    form.append('owner_id', studentId)
    form.append('title', documentTitle || documentFile.name)
    form.append('linked_student_ids', documentLinkStudentIds.join(','))
    form.append('file', documentFile)

    await api.post('/documents/upload', form)
    setDocumentTitle('')
    setDocumentFile(null)
    await loadProfile()
  }

  if (!profile) {
    return <p>Loading profile...</p>
  }

  return (
    <section>
      <h2>{profile.student.name}</h2>
      <article className="card">
        <h3>Student Info</h3>
        <form className="form gradebook-toolbar" onSubmit={saveProfileFields}>
          <input value={firstNameDraft} onChange={(event) => setFirstNameDraft(event.target.value)} placeholder="First name" required />
          <input value={lastNameDraft} onChange={(event) => setLastNameDraft(event.target.value)} placeholder="Last name" required />
          <input value={emailDraft} onChange={(event) => setEmailDraft(event.target.value)} placeholder="Email address" />
          <input value={phoneDraft} onChange={(event) => setPhoneDraft(event.target.value)} placeholder="Phone number" />
          <button type="submit">Save Student Info</button>
        </form>
        <p>Student number: {profile.student.student_number || 'N/A'}</p>
      </article>
      <p>
        Advisee status:{' '}
        {profile.student.is_advisee ? `Yes (Advisee #${profile.student.advisee_id})` : 'Not currently marked as advisee'}
      </p>
      {!profile.student.is_advisee ? (
        <button onClick={() => void markAsAdvisee()} disabled={markingAdvisee}>
          {markingAdvisee ? 'Marking...' : 'Mark as Advisee'}
        </button>
      ) : (
        <div className="gradebook-toolbar compact-grid" style={{ marginTop: '0.5rem' }}>
          <button onClick={() => void unmarkAsAdvisee()} disabled={unmarkingAdvisee}>
            {unmarkingAdvisee ? 'Removing...' : 'Remove as Advisee'}
          </button>
          <div className="table-subtle">
            Advising history is preserved; this only removes the active advisee link for this student profile.
          </div>
        </div>
      )}
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

      <h3>Student Documents</h3>
      <article className="card">
        <form className="form" onSubmit={uploadDocument}>
          <input
            value={documentTitle}
            onChange={(event) => setDocumentTitle(event.target.value)}
            placeholder="Document title"
          />
          <label>
            Link to students (multi-select)
            <select
              multiple
              size={7}
              value={documentLinkStudentIds}
              onChange={(event) => {
                const values = Array.from(event.target.selectedOptions).map((option) => option.value)
                setDocumentLinkStudentIds(values)
              }}
            >
              {documentTargets.map((student) => (
                <option key={student.id} value={student.id}>
                  {student.name}
                  {student.email ? ` (${student.email})` : ''}
                </option>
              ))}
            </select>
          </label>
          <input
            type="file"
            onChange={(event) => {
              const selected = event.target.files?.[0]
              if (selected) setDocumentFile(selected)
            }}
            required
          />
          <button type="submit">Attach Document</button>
        </form>
      </article>
      <ul className="list">
        {profile.student_documents.map((document) => (
          <li key={document.id} className="card">
            <strong>{document.title}</strong>
            <div>Category: {document.category || 'Other'}</div>
            <div>Type: {document.document_type}</div>
            <div>Version: {document.current_version}</div>
            <div>Filename: {document.latest_filename || 'N/A'}</div>
            <div>Size: {document.latest_size_bytes ? `${document.latest_size_bytes.toLocaleString()} B` : 'N/A'}</div>
            <div>Updated: {document.updated_at ? new Date(document.updated_at).toLocaleString() : 'N/A'}</div>
            <div style={{ marginTop: '0.35rem' }}>
              <a href={`/api/v1/documents/${document.id}/download`} target="_blank" rel="noreferrer">
                Download
              </a>{' '}
              |{' '}
              <a href={`/api/v1/documents/${document.id}/text`} target="_blank" rel="noreferrer">
                View Extracted Text
              </a>
            </div>
          </li>
        ))}
        {profile.student_documents.length === 0 ? <li className="card">No documents linked.</li> : null}
      </ul>
    </section>
  )
}
