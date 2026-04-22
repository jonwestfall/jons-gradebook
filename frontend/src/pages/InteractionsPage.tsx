import { FormEvent, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'

type Interaction = {
  id: number
  interaction_type: string
  summary: string
  occurred_at: string
  student_profile_id?: number | null
  advisee_id?: number | null
  student_name?: string | null
  advisee_name?: string | null
}

type InteractionTargets = {
  students: { id: number; name: string; email?: string | null }[]
  courses: { id: number; name: string; section_name?: string | null; student_count: number }[]
  advisees: { id: number; name: string; student_profile_id?: number | null }[]
}

export function InteractionsPage() {
  const [interactions, setInteractions] = useState<Interaction[]>([])
  const [targets, setTargets] = useState<InteractionTargets | null>(null)

  const [targetScope, setTargetScope] = useState<'student' | 'course' | 'advisees'>('student')
  const [targetId, setTargetId] = useState('')
  const [interactionType, setInteractionType] = useState('manual_note')
  const [summary, setSummary] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState<string | null>(null)

  async function load() {
    const [interactionRows, targetRows] = await Promise.all([
      api.get<Interaction[]>('/interactions/'),
      api.get<InteractionTargets>('/interactions/targets'),
    ])
    setInteractions(interactionRows)
    setTargets(targetRows)

    if (!targetId && targetRows.students.length > 0) {
      setTargetId(String(targetRows.students[0].id))
    }
  }

  useEffect(() => {
    void load().catch((err) => setError((err as Error).message))
  }, [])

  const scopeOptions = useMemo(() => {
    if (!targets) return []
    if (targetScope === 'student') {
      return targets.students.map((student) => ({ value: String(student.id), label: `${student.name}${student.email ? ` (${student.email})` : ''}` }))
    }
    if (targetScope === 'course') {
      return targets.courses.map((course) => ({ value: String(course.id), label: `${course.name}${course.section_name ? ` (${course.section_name})` : ''} - ${course.student_count} students` }))
    }
    return []
  }, [targets, targetScope])

  useEffect(() => {
    if (targetScope === 'advisees') {
      setTargetId('')
      return
    }
    if (scopeOptions.length > 0) {
      setTargetId((current) => (scopeOptions.some((item) => item.value === current) ? current : scopeOptions[0].value))
    }
  }, [targetScope, scopeOptions])

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await api.post('/interactions/bulk', {
        interaction_type: interactionType,
        occurred_at: new Date().toISOString(),
        summary,
        notes,
        target_scope: targetScope,
        target_id: targetScope === 'advisees' ? null : Number(targetId),
      })
      setSummary('')
      setNotes('')
      await load()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <section>
      <h2>Recent Interactions</h2>
      <p>Create notes for one student, everyone in a class, or all advisees at once.</p>
      <form className="form" onSubmit={submit}>
        <select value={targetScope} onChange={(event) => setTargetScope(event.target.value as 'student' | 'course' | 'advisees')}>
          <option value="student">Single Student</option>
          <option value="course">All Students in a Class</option>
          <option value="advisees">All Advisees</option>
        </select>

        {targetScope !== 'advisees' ? (
          <select value={targetId} onChange={(event) => setTargetId(event.target.value)}>
            {scopeOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        ) : (
          <div className="card">This note will be created for all advisees in the system.</div>
        )}

        <select value={interactionType} onChange={(event) => setInteractionType(event.target.value)}>
          <option value="manual_note">Manual Note</option>
          <option value="office_visit">Office Visit</option>
          <option value="email_log">Email Log</option>
          <option value="attendance">Attendance</option>
          <option value="file_upload">File Upload</option>
        </select>

        <input value={summary} onChange={(event) => setSummary(event.target.value)} placeholder="Interaction summary" required />
        <textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Notes (optional)" />
        <button type="submit">Create Interaction</button>
      </form>

      {error ? <p className="error">{error}</p> : null}

      <ul className="list">
        {interactions.map((interaction) => (
          <li key={interaction.id} className="card">
            <strong>{interaction.interaction_type}</strong>
            <div>{interaction.summary}</div>
            <div>
              Target:{' '}
              {interaction.advisee_name
                ? `Advisee ${interaction.advisee_name}`
                : interaction.student_name
                  ? `Student ${interaction.student_name}`
                  : 'General'}
            </div>
            <div>{new Date(interaction.occurred_at).toLocaleString()}</div>
          </li>
        ))}
      </ul>
    </section>
  )
}
