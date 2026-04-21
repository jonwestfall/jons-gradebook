import { FormEvent, useEffect, useState } from 'react'
import { api } from '../api/client'

type Interaction = {
  id: number
  interaction_type: string
  summary: string
  occurred_at: string
}

export function InteractionsPage() {
  const [interactions, setInteractions] = useState<Interaction[]>([])
  const [summary, setSummary] = useState('')

  async function load() {
    setInteractions(await api.get<Interaction[]>('/interactions/'))
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    await api.post('/interactions/', {
      interaction_type: 'manual_note',
      occurred_at: new Date().toISOString(),
      summary,
      notes: summary,
    })
    setSummary('')
    await load()
  }

  useEffect(() => {
    void load()
  }, [])

  return (
    <section>
      <h2>Recent Interactions</h2>
      <form className="form" onSubmit={submit}>
        <input value={summary} onChange={(event) => setSummary(event.target.value)} placeholder="Interaction summary" required />
        <button type="submit">Add Note</button>
      </form>
      <ul className="list">
        {interactions.map((interaction) => (
          <li key={interaction.id} className="card">
            <strong>{interaction.interaction_type}</strong>
            <div>{interaction.summary}</div>
            <div>{new Date(interaction.occurred_at).toLocaleString()}</div>
          </li>
        ))}
      </ul>
    </section>
  )
}
