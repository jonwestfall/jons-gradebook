import { FormEvent, useEffect, useState } from 'react'
import { api } from '../api/client'

type Rubric = {
  id: number
  name: string
  description?: string | null
  max_points?: number | null
}

export function RubricsPage() {
  const [rubrics, setRubrics] = useState<Rubric[]>([])
  const [name, setName] = useState('')

  async function load() {
    setRubrics(await api.get<Rubric[]>('/rubrics/'))
  }

  async function createRubric(event: FormEvent) {
    event.preventDefault()
    await api.post('/rubrics/', { name })
    setName('')
    await load()
  }

  useEffect(() => {
    void load()
  }, [])

  return (
    <section>
      <h2>Rubrics and Checklists</h2>
      <form className="form" onSubmit={createRubric}>
        <input value={name} onChange={(event) => setName(event.target.value)} placeholder="Rubric name" required />
        <button type="submit">Create Rubric</button>
      </form>
      <ul className="list">
        {rubrics.map((rubric) => (
          <li key={rubric.id} className="card">
            <h3>{rubric.name}</h3>
            <div>{rubric.description || 'No description'}</div>
            <div>Max points: {rubric.max_points || 'N/A'}</div>
          </li>
        ))}
      </ul>
    </section>
  )
}
