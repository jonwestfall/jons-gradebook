import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'

type Advisee = {
  id: number
  first_name: string
  last_name: string
  email?: string | null
  student_profile_id?: number | null
  latest_meeting_at?: string | null
  meeting_count?: number
}

type Meeting = {
  id: number
  advisee_id: number
  advisee_name?: string | null
  student_profile_id?: number | null
  meeting_at: string
  mode: 'in_person' | 'virtual' | 'phone' | 'other'
  summary?: string | null
  action_items?: string | null
}

export function AdvisingPage() {
  const [advisees, setAdvisees] = useState<Advisee[]>([])
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState<'last_name' | 'recent_meeting'>('last_name')
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const [meetingAdviseeId, setMeetingAdviseeId] = useState('')
  const [meetingAt, setMeetingAt] = useState('')
  const [meetingMode, setMeetingMode] = useState<'in_person' | 'virtual' | 'phone' | 'other'>('in_person')
  const [meetingSummary, setMeetingSummary] = useState('')
  const [meetingActions, setMeetingActions] = useState('')
  const [followupDays, setFollowupDays] = useState('7')

  async function load() {
    const [adviseeRows, meetingRows] = await Promise.all([
      api.get<Advisee[]>('/advising/advisees'),
      api.get<Meeting[]>('/advising/meetings?limit=500'),
    ])
    setAdvisees(adviseeRows)
    setMeetings(meetingRows)

    if (!meetingAdviseeId && adviseeRows.length > 0) {
      setMeetingAdviseeId(String(adviseeRows[0].id))
    }
  }

  async function createAdvisee(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await api.post('/advising/advisees', {
        first_name: firstName,
        last_name: lastName,
        email: email || null,
      })
      setFirstName('')
      setLastName('')
      setEmail('')
      await load()
      setMessage('Advisee added.')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function createMeeting(event: FormEvent) {
    event.preventDefault()
    if (!meetingAdviseeId || !meetingAt) return

    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      const meeting = await api.post<Meeting>('/advising/meetings', {
        advisee_id: Number(meetingAdviseeId),
        meeting_at: new Date(meetingAt).toISOString(),
        mode: meetingMode,
        summary: meetingSummary.trim() || null,
        action_items: meetingActions.trim() || null,
      })

      const days = Number(followupDays)
      if (days > 0) {
        await api.post('/tasks/', {
          title: `Follow up after advising meeting: ${meeting.advisee_name || 'Advisee'}`,
          status: 'open',
          priority: 'medium',
          due_at: new Date(Date.now() + days * 24 * 60 * 60 * 1000).toISOString(),
          note: meeting.action_items || meeting.summary || 'Review action items from advising meeting.',
          linked_student_id: meeting.student_profile_id || null,
          linked_advising_meeting_id: meeting.id,
          source: 'advising_meeting',
        })
      }

      setMeetingAt('')
      setMeetingMode('in_person')
      setMeetingSummary('')
      setMeetingActions('')
      await load()
      setMessage('Meeting logged and follow-up task created.')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function convertToTask(meeting: Meeting) {
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      await api.post('/tasks/', {
        title: `Advising next-step: ${meeting.advisee_name || 'Advisee'}`,
        status: 'open',
        priority: 'medium',
        due_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
        note: meeting.action_items || meeting.summary || 'No action items captured in meeting note.',
        linked_student_id: meeting.student_profile_id || null,
        linked_advising_meeting_id: meeting.id,
        source: 'advising_meeting_manual',
      })
      setMessage('Meeting converted to a task.')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => {
    void load().catch((err) => setError((err as Error).message))
  }, [])

  const visibleAdvisees = useMemo(() => {
    const query = search.trim().toLowerCase()
    let rows = advisees.filter((advisee) => {
      if (!query) return true
      const haystack = `${advisee.first_name} ${advisee.last_name} ${advisee.email || ''}`.toLowerCase()
      return haystack.includes(query)
    })

    rows = [...rows].sort((a, b) => {
      if (sortBy === 'last_name') {
        const byLast = a.last_name.localeCompare(b.last_name)
        if (byLast !== 0) return byLast
        return a.first_name.localeCompare(b.first_name)
      }
      const aTs = a.latest_meeting_at ? Date.parse(a.latest_meeting_at) : 0
      const bTs = b.latest_meeting_at ? Date.parse(b.latest_meeting_at) : 0
      return bTs - aTs
    })

    return rows
  }, [advisees, search, sortBy])

  return (
    <section>
      <h2>Advising</h2>
      <p className="subtitle">Capture meetings, track action items, and convert advising conversations into follow-up tasks.</p>

      <article className="card action-bar">
        <div className="gradebook-toolbar compact-grid">
          <button type="button" onClick={() => void load()} disabled={busy}>Refresh</button>
          <Link className="nav-link" to="/tasks">Open Task Queue</Link>
          <div className="muted-badge">Meetings logged: {meetings.length}</div>
        </div>
      </article>

      <div className="gradebook-layout" style={{ marginTop: '0.8rem' }}>
        <article className="card">
          <h3>Add Advisee</h3>
          <form className="form gradebook-toolbar" onSubmit={createAdvisee}>
            <input placeholder="First name" value={firstName} onChange={(event) => setFirstName(event.target.value)} required />
            <input placeholder="Last name" value={lastName} onChange={(event) => setLastName(event.target.value)} required />
            <input placeholder="Email" value={email} onChange={(event) => setEmail(event.target.value)} />
            <button type="submit" disabled={busy}>Add Advisee</button>
          </form>
        </article>

        <article className="card">
          <h3>Log Advising Meeting</h3>
          <form className="form" onSubmit={createMeeting}>
            <select value={meetingAdviseeId} onChange={(event) => setMeetingAdviseeId(event.target.value)} required>
              {advisees.map((advisee) => (
                <option key={advisee.id} value={advisee.id}>{advisee.last_name}, {advisee.first_name}</option>
              ))}
            </select>
            <input type="datetime-local" value={meetingAt} onChange={(event) => setMeetingAt(event.target.value)} required />
            <select value={meetingMode} onChange={(event) => setMeetingMode(event.target.value as typeof meetingMode)}>
              <option value="in_person">In Person</option>
              <option value="virtual">Virtual</option>
              <option value="phone">Phone</option>
              <option value="other">Other</option>
            </select>
            <input value={meetingSummary} onChange={(event) => setMeetingSummary(event.target.value)} placeholder="Summary" />
            <textarea value={meetingActions} onChange={(event) => setMeetingActions(event.target.value)} placeholder="Action items" />
            <input
              type="number"
              min="0"
              max="60"
              value={followupDays}
              onChange={(event) => setFollowupDays(event.target.value)}
              placeholder="Follow-up task due in days"
            />
            <button type="submit" disabled={busy}>{busy ? 'Saving...' : 'Save Meeting + Follow-up'}</button>
          </form>
        </article>
      </div>

      <article className="card" style={{ marginTop: '0.8rem' }}>
        <div className="gradebook-toolbar compact-grid">
          <input
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search advisee name or email"
          />
          <select value={sortBy} onChange={(event) => setSortBy(event.target.value as typeof sortBy)}>
            <option value="last_name">Sort: Last Name</option>
            <option value="recent_meeting">Sort: Most Recent Meeting</option>
          </select>
        </div>
      </article>

      <article className="card students-grid-wrap" style={{ marginTop: '0.8rem' }}>
        <table className="students-grid-table prioritize-mobile">
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Linked Student Profile</th>
              <th>Meetings</th>
              <th>Latest Meeting/Visit</th>
            </tr>
          </thead>
          <tbody>
            {visibleAdvisees.map((advisee) => (
              <tr key={advisee.id}>
                <td>
                  {advisee.student_profile_id ? (
                    <Link to={`/students/${advisee.student_profile_id}`}>{advisee.last_name}, {advisee.first_name}</Link>
                  ) : (
                    `${advisee.last_name}, ${advisee.first_name}`
                  )}
                </td>
                <td>{advisee.email || '—'}</td>
                <td>{advisee.student_profile_id || 'None'}</td>
                <td>{advisee.meeting_count ?? 0}</td>
                <td>{advisee.latest_meeting_at ? new Date(advisee.latest_meeting_at).toLocaleString() : '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {visibleAdvisees.length === 0 ? <p>No advisees found for current filters.</p> : null}
      </article>

      <article className="card" style={{ marginTop: '0.8rem' }}>
        <h3>Meeting Timeline</h3>
        <ul className="list compact">
          {meetings.map((meeting) => (
            <li key={meeting.id} className="card">
              <strong>{meeting.advisee_name || `Advisee #${meeting.advisee_id}`}</strong> · {new Date(meeting.meeting_at).toLocaleString()} · {meeting.mode}
              {meeting.summary ? <div className="table-subtle">Summary: {meeting.summary}</div> : null}
              {meeting.action_items ? <div className="table-subtle">Action items: {meeting.action_items}</div> : null}
              <div style={{ display: 'flex', gap: '0.45rem', marginTop: '0.4rem', flexWrap: 'wrap' }}>
                {meeting.student_profile_id ? <Link to={`/students/${meeting.student_profile_id}`}>Open Student</Link> : null}
                <button type="button" onClick={() => void convertToTask(meeting)} disabled={busy}>Convert to Task</button>
              </div>
            </li>
          ))}
        </ul>
        {meetings.length === 0 ? <p>No meetings logged yet.</p> : null}
      </article>

      {message ? <p>{message}</p> : null}
      {error ? <p className="error">{error}</p> : null}
    </section>
  )
}
