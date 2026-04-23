import { FormEvent, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'

type AttendanceCourse = {
  id: number
  name: string
  section_name?: string | null
  term_name?: string | null
}

type RollCallMeeting = {
  id: number
  meeting_date: string
  is_generated: boolean
  is_canceled: boolean
}

type RollCallStudent = {
  student_id: number
  name: string
  email?: string | null
  status: 'present' | 'absent' | 'tardy' | 'excused' | 'unmarked'
  note?: string | null
  counts: {
    present: number
    absent: number
    tardy: number
    excused: number
    unmarked: number
  }
  attendance_percent?: number | null
}

type RollCallPayload = {
  course: {
    id: number
    name: string
    section_name?: string | null
    term_name?: string | null
    attendance_lateness_weight: number
    attendance_excluded_from_final_grade: boolean
  }
  lateness_weight: number
  meetings: RollCallMeeting[]
  active_meeting_id?: number | null
  students: RollCallStudent[]
}

function nextStatus(current: RollCallStudent['status']): RollCallStudent['status'] {
  if (current === 'unmarked') return 'present'
  if (current === 'present') return 'absent'
  if (current === 'absent') return 'tardy'
  if (current === 'tardy') return 'excused'
  return 'unmarked'
}

function statusLabel(status: RollCallStudent['status']) {
  if (status === 'present') return 'Present'
  if (status === 'absent') return 'Absent'
  if (status === 'tardy') return 'Tardy'
  if (status === 'excused') return 'Excused'
  return 'Unmarked'
}

function statusIcon(status: RollCallStudent['status']) {
  if (status === 'present') return '✓'
  if (status === 'absent') return '✕'
  if (status === 'tardy') return '◷'
  if (status === 'excused') return 'E'
  return '∅'
}

export function AttendancePage() {
  const [courses, setCourses] = useState<AttendanceCourse[]>([])
  const [courseId, setCourseId] = useState('')
  const [rollCall, setRollCall] = useState<RollCallPayload | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const [meetingDate, setMeetingDate] = useState('')
  const [generateStart, setGenerateStart] = useState('')
  const [generateEnd, setGenerateEnd] = useState('')
  const [search, setSearch] = useState('')
  const [noteDrafts, setNoteDrafts] = useState<Record<number, string>>({})
  const [savingKey, setSavingKey] = useState<string | null>(null)
  const [latenessWeightPercent, setLatenessWeightPercent] = useState(80)
  const [excludeFromFinalGrade, setExcludeFromFinalGrade] = useState(false)

  async function loadCourses() {
    const data = await api.get<AttendanceCourse[]>('/attendance/courses')
    setCourses(data)
    if (!courseId && data.length > 0) {
      setCourseId(String(data[0].id))
    }
  }

  async function loadRollCall(targetCourseId: string, targetMeetingId?: number) {
    if (!targetCourseId) return
    setLoading(true)
    setError(null)
    try {
      const query = targetMeetingId ? `?meeting_id=${targetMeetingId}` : ''
      const data = await api.get<RollCallPayload>(`/attendance/rollcall/${targetCourseId}${query}`)
      setRollCall(data)
      setNoteDrafts(Object.fromEntries(data.students.map((student) => [student.student_id, student.note || ''])))
      setLatenessWeightPercent(Math.round((data.lateness_weight || 0.8) * 100))
      setExcludeFromFinalGrade(data.course.attendance_excluded_from_final_grade || false)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadCourses()
  }, [])

  useEffect(() => {
    if (courseId) {
      void loadRollCall(courseId)
    }
  }, [courseId])

  const activeMeetingIndex = useMemo(() => {
    if (!rollCall || rollCall.active_meeting_id === null || rollCall.active_meeting_id === undefined) return -1
    return rollCall.meetings.findIndex((meeting) => meeting.id === rollCall.active_meeting_id)
  }, [rollCall])

  const filteredStudents = useMemo(() => {
    if (!rollCall) return []
    const query = search.trim().toLowerCase()
    if (!query) return rollCall.students
    return rollCall.students.filter((student) => {
      return `${student.name} ${student.email || ''}`.toLowerCase().includes(query)
    })
  }, [rollCall, search])

  async function chooseMeeting(meetingId: number) {
    if (!courseId) return
    await loadRollCall(courseId, meetingId)
  }

  async function changeStudentStatus(student: RollCallStudent) {
    if (!rollCall?.active_meeting_id) return
    const next = nextStatus(student.status)
    const key = `status-${student.student_id}`
    setSavingKey(key)
    setError(null)
    try {
      if (next === 'unmarked') {
        await api.delete(`/attendance/records/${rollCall.active_meeting_id}/${student.student_id}`)
      } else {
        await api.post('/attendance/records', {
          meeting_id: rollCall.active_meeting_id,
          student_id: student.student_id,
          status: next,
          note: noteDrafts[student.student_id] || null,
        })
      }
      await loadRollCall(courseId, rollCall.active_meeting_id)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSavingKey(null)
    }
  }

  async function saveNote(student: RollCallStudent) {
    if (!rollCall?.active_meeting_id || student.status === 'unmarked') return
    const key = `note-${student.student_id}`
    setSavingKey(key)
    setError(null)
    try {
      await api.post('/attendance/records', {
        meeting_id: rollCall.active_meeting_id,
        student_id: student.student_id,
        status: student.status,
        note: noteDrafts[student.student_id] || null,
      })
      await loadRollCall(courseId, rollCall.active_meeting_id)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSavingKey(null)
    }
  }

  async function markAllPresent() {
    if (!rollCall?.active_meeting_id) return
    setSavingKey('mark-all')
    try {
      await api.post(`/attendance/meetings/${rollCall.active_meeting_id}/mark-all-present`)
      await loadRollCall(courseId, rollCall.active_meeting_id)
    } finally {
      setSavingKey(null)
    }
  }

  async function unmarkAll() {
    if (!rollCall?.active_meeting_id) return
    setSavingKey('unmark-all')
    try {
      await api.post(`/attendance/meetings/${rollCall.active_meeting_id}/unmark-all`)
      await loadRollCall(courseId, rollCall.active_meeting_id)
    } finally {
      setSavingKey(null)
    }
  }

  async function createMeeting(event: FormEvent) {
    event.preventDefault()
    if (!courseId || !meetingDate) return
    setSavingKey('create-meeting')
    try {
      await api.post('/attendance/meetings', {
        course_id: Number(courseId),
        meeting_date: meetingDate,
      })
      setMeetingDate('')
      await loadRollCall(courseId)
    } finally {
      setSavingKey(null)
    }
  }

  async function generateMeetings(event: FormEvent) {
    event.preventDefault()
    if (!courseId || !generateStart || !generateEnd) return
    setSavingKey('generate-meetings')
    try {
      await api.post('/courses/meetings/generate', {
        course_id: Number(courseId),
        start_date: generateStart,
        end_date: generateEnd,
      })
      await loadRollCall(courseId)
    } finally {
      setSavingKey(null)
    }
  }

  async function deleteActiveMeeting() {
    if (!rollCall?.active_meeting_id) return
    setSavingKey('delete-meeting')
    try {
      await api.delete(`/attendance/meetings/${rollCall.active_meeting_id}`)
      await loadRollCall(courseId)
    } finally {
      setSavingKey(null)
    }
  }

  async function saveSettings() {
    if (!courseId) return
    setSavingKey('save-settings')
    try {
      await api.put(`/attendance/courses/${courseId}/settings`, {
        lateness_weight: Math.max(0, Math.min(1, latenessWeightPercent / 100)),
        excluded_from_final_grade: excludeFromFinalGrade,
      })
      await loadRollCall(courseId, rollCall?.active_meeting_id || undefined)
    } finally {
      setSavingKey(null)
    }
  }

  return (
    <section>
      <h2>Attendance</h2>
      <p className="subtitle">
        Roll Call style workflow: choose course and day, click status to cycle attendance, mark all present, and review
        running totals.
      </p>

      <article className="card">
        <div className="gradebook-toolbar compact-grid">
          <select value={courseId} onChange={(event) => setCourseId(event.target.value)}>
            <option value="">Select Course</option>
            {courses.map((course) => (
              <option key={course.id} value={course.id}>
                {course.name} {course.section_name ? `(${course.section_name})` : ''}
              </option>
            ))}
          </select>
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search student" />
          <button
            onClick={() => {
              if (!rollCall || activeMeetingIndex <= 0) return
              void chooseMeeting(rollCall.meetings[activeMeetingIndex - 1].id)
            }}
            disabled={!rollCall || activeMeetingIndex <= 0}
          >
            Previous Date
          </button>
          <button
            onClick={() => {
              if (!rollCall || activeMeetingIndex < 0 || activeMeetingIndex >= rollCall.meetings.length - 1) return
              void chooseMeeting(rollCall.meetings[activeMeetingIndex + 1].id)
            }}
            disabled={!rollCall || activeMeetingIndex < 0 || activeMeetingIndex >= (rollCall?.meetings.length || 0) - 1}
          >
            Next Date
          </button>
          <select
            value={rollCall?.active_meeting_id ? String(rollCall.active_meeting_id) : ''}
            onChange={(event) => {
              const value = Number(event.target.value)
              if (value) void chooseMeeting(value)
            }}
            disabled={!rollCall || rollCall.meetings.length === 0}
          >
            {!rollCall || rollCall.meetings.length === 0 ? <option value="">No meetings</option> : null}
            {rollCall?.meetings.map((meeting) => (
              <option key={meeting.id} value={meeting.id}>
                {new Date(`${meeting.meeting_date}T00:00:00`).toLocaleDateString()} {meeting.is_generated ? '• generated' : '• manual'}
              </option>
            ))}
          </select>
        </div>

        <div className="gradebook-toolbar compact-grid" style={{ marginTop: '0.55rem' }}>
          <button onClick={() => void markAllPresent()} disabled={!rollCall?.active_meeting_id || savingKey === 'mark-all'}>
            {savingKey === 'mark-all' ? 'Saving...' : 'Mark All Present'}
          </button>
          <button onClick={() => void unmarkAll()} disabled={!rollCall?.active_meeting_id || savingKey === 'unmark-all'}>
            {savingKey === 'unmark-all' ? 'Saving...' : 'Unmark All'}
          </button>
          <button onClick={() => void deleteActiveMeeting()} disabled={!rollCall?.active_meeting_id || savingKey === 'delete-meeting'}>
            {savingKey === 'delete-meeting' ? 'Deleting...' : 'Delete Active Meeting'}
          </button>
          <div className="table-subtle">Late weight: {rollCall ? Math.round(rollCall.lateness_weight * 100) : 80}% of present</div>
        </div>
      </article>

      <div className="gradebook-layout">
        <article className="card">
          <h3>Add Manual Meeting</h3>
          <form className="form gradebook-toolbar" onSubmit={createMeeting}>
            <input type="date" value={meetingDate} onChange={(event) => setMeetingDate(event.target.value)} required />
            <button type="submit" disabled={!courseId || savingKey === 'create-meeting'}>
              {savingKey === 'create-meeting' ? 'Adding...' : 'Add Date'}
            </button>
          </form>
        </article>

        <article className="card">
          <h3>Generate Meetings from Schedule</h3>
          <form className="form gradebook-toolbar" onSubmit={generateMeetings}>
            <input type="date" value={generateStart} onChange={(event) => setGenerateStart(event.target.value)} required />
            <input type="date" value={generateEnd} onChange={(event) => setGenerateEnd(event.target.value)} required />
            <button type="submit" disabled={!courseId || savingKey === 'generate-meetings'}>
              {savingKey === 'generate-meetings' ? 'Generating...' : 'Generate'}
            </button>
          </form>
        </article>
      </div>

      <article className="card" style={{ marginTop: '0.8rem' }}>
        <h3>Roll Call Settings</h3>
        <div className="gradebook-toolbar compact-grid" style={{ alignItems: 'end' }}>
          <label>
            Lateness %
            <input
              type="number"
              min={0}
              max={100}
              value={latenessWeightPercent}
              onChange={(event) => setLatenessWeightPercent(Number(event.target.value))}
            />
          </label>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <input
              type="checkbox"
              checked={excludeFromFinalGrade}
              onChange={(event) => setExcludeFromFinalGrade(event.target.checked)}
            />
            Do not count attendance toward final grade
          </label>
          <button type="button" onClick={() => void saveSettings()} disabled={!courseId || savingKey === 'save-settings'}>
            {savingKey === 'save-settings' ? 'Saving...' : 'Save Settings'}
          </button>
        </div>
      </article>

      {error ? <p className="error">{error}</p> : null}
      {loading ? <p>Loading roll call...</p> : null}

      {rollCall ? (
        <article className="card students-grid-wrap">
          <table className="students-grid-table">
            <thead>
              <tr>
                <th>Student</th>
                <th>Status (Active Date)</th>
                <th>Note</th>
                <th>Present</th>
                <th>Absent</th>
                <th>Tardy</th>
                <th>Excused</th>
                <th>Unmarked</th>
                <th>Attendance %</th>
              </tr>
            </thead>
            <tbody>
              {filteredStudents.map((student) => (
                <tr key={student.student_id}>
                  <td>{student.name}</td>
                  <td>
                    <button
                      type="button"
                      className={`attendance-status-chip status-${student.status}`}
                      onClick={() => void changeStudentStatus(student)}
                      disabled={!rollCall.active_meeting_id || savingKey === `status-${student.student_id}`}
                    >
                      {savingKey === `status-${student.student_id}` ? 'Saving...' : `${statusIcon(student.status)} ${statusLabel(student.status)}`}
                    </button>
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '0.35rem' }}>
                      <input
                        value={noteDrafts[student.student_id] || ''}
                        onChange={(event) =>
                          setNoteDrafts((prev) => ({ ...prev, [student.student_id]: event.target.value }))
                        }
                        placeholder="Optional note"
                      />
                      <button
                        type="button"
                        onClick={() => void saveNote(student)}
                        disabled={student.status === 'unmarked' || savingKey === `note-${student.student_id}`}
                      >
                        {savingKey === `note-${student.student_id}` ? '...' : 'Save'}
                      </button>
                    </div>
                  </td>
                  <td>{student.counts.present}</td>
                  <td>{student.counts.absent}</td>
                  <td>{student.counts.tardy}</td>
                  <td>{student.counts.excused}</td>
                  <td>{student.counts.unmarked}</td>
                  <td>{student.attendance_percent === null || student.attendance_percent === undefined ? 'N/A' : `${student.attendance_percent}%`}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredStudents.length === 0 ? <p>No students found.</p> : null}
        </article>
      ) : null}
    </section>
  )
}
