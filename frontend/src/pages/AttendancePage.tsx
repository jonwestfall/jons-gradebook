import { FormEvent, useState } from 'react'
import { api } from '../api/client'

type Meeting = {
  id: number
  meeting_date: string
  is_generated: boolean
}

export function AttendancePage() {
  const [courseId, setCourseId] = useState('')
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [meetingId, setMeetingId] = useState('')
  const [studentId, setStudentId] = useState('')
  const [status, setStatus] = useState('present')

  async function loadMeetings(event: FormEvent) {
    event.preventDefault()
    if (!courseId) return
    const data = await api.get<Meeting[]>(`/attendance/meetings/${courseId}`)
    setMeetings(data)
  }

  async function submitAttendance(event: FormEvent) {
    event.preventDefault()
    await api.post('/attendance/records', {
      meeting_id: Number(meetingId),
      student_id: Number(studentId),
      status,
    })
  }

  return (
    <section>
      <h2>Attendance</h2>
      <form className="form" onSubmit={loadMeetings}>
        <input value={courseId} onChange={(event) => setCourseId(event.target.value)} placeholder="Course ID" required />
        <button type="submit">Load Meetings</button>
      </form>
      <ul className="list">
        {meetings.map((meeting) => (
          <li key={meeting.id} className="card">
            {meeting.id} - {meeting.meeting_date}
          </li>
        ))}
      </ul>

      <h3>Record Attendance</h3>
      <form className="form" onSubmit={submitAttendance}>
        <input value={meetingId} onChange={(event) => setMeetingId(event.target.value)} placeholder="Meeting ID" required />
        <input value={studentId} onChange={(event) => setStudentId(event.target.value)} placeholder="Student ID" required />
        <select value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="present">Present</option>
          <option value="absent">Absent</option>
          <option value="tardy">Tardy</option>
          <option value="excused">Excused</option>
        </select>
        <button type="submit">Save Attendance</button>
      </form>
    </section>
  )
}
