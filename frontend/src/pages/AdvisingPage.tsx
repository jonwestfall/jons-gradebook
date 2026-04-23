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

export function AdvisingPage() {
  const [advisees, setAdvisees] = useState<Advisee[]>([])
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState<'last_name' | 'recent_meeting'>('last_name')

  async function load() {
    setAdvisees(await api.get<Advisee[]>('/advising/advisees'))
  }

  async function create(event: FormEvent) {
    event.preventDefault()
    await api.post('/advising/advisees', {
      first_name: firstName,
      last_name: lastName,
      email: email || null,
    })
    setFirstName('')
    setLastName('')
    setEmail('')
    await load()
  }

  useEffect(() => {
    void load()
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
      <form className="form gradebook-toolbar" onSubmit={create}>
        <input placeholder="First name" value={firstName} onChange={(event) => setFirstName(event.target.value)} required />
        <input placeholder="Last name" value={lastName} onChange={(event) => setLastName(event.target.value)} required />
        <input placeholder="Email" value={email} onChange={(event) => setEmail(event.target.value)} />
        <button type="submit">Add Advisee</button>
      </form>

      <article className="card">
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

      <article className="card students-grid-wrap">
        <table className="students-grid-table">
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
    </section>
  )
}
