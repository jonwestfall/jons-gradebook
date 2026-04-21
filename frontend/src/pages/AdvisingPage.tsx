import { FormEvent, useEffect, useState } from 'react'
import { api } from '../api/client'

type Advisee = {
  id: number
  first_name: string
  last_name: string
  email?: string | null
  student_profile_id?: number | null
}

export function AdvisingPage() {
  const [advisees, setAdvisees] = useState<Advisee[]>([])
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')

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

  return (
    <section>
      <h2>Advising</h2>
      <form className="form" onSubmit={create}>
        <input placeholder="First name" value={firstName} onChange={(event) => setFirstName(event.target.value)} required />
        <input placeholder="Last name" value={lastName} onChange={(event) => setLastName(event.target.value)} required />
        <input placeholder="Email" value={email} onChange={(event) => setEmail(event.target.value)} />
        <button type="submit">Add Advisee</button>
      </form>
      <ul className="list">
        {advisees.map((advisee) => (
          <li key={advisee.id} className="card">
            <h3>
              {advisee.first_name} {advisee.last_name}
            </h3>
            <div>{advisee.email || 'No email'}</div>
            <div>Linked profile: {advisee.student_profile_id || 'None'}</div>
          </li>
        ))}
      </ul>
    </section>
  )
}
