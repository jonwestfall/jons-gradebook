import { FormEvent, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api } from '../api/client'

type TaskRow = {
  id: number
  title: string
  status: 'open' | 'in_progress' | 'done' | 'canceled'
  priority: 'low' | 'medium' | 'high'
  due_at?: string | null
  note?: string | null
  linked_student_id?: number | null
  linked_course_id?: number | null
  linked_interaction_id?: number | null
  linked_advising_meeting_id?: number | null
  source: string
  created_at: string
  updated_at: string
}

type TaskTargets = {
  students: { id: number; name: string; email?: string | null }[]
  courses: { id: number; name: string; section_name?: string | null }[]
}

type RuleRunResult = {
  created_count: number
  skipped_count: number
  evaluated_students: number
}

function dateInputToIso(value: string): string | null {
  if (!value) return null
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return null
  return parsed.toISOString()
}

function isoToDateInput(value?: string | null): string {
  if (!value) return ''
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return ''
  const local = new Date(parsed.getTime() - parsed.getTimezoneOffset() * 60000)
  return local.toISOString().slice(0, 16)
}

export function TaskQueuePage() {
  const [searchParams] = useSearchParams()

  const [tasks, setTasks] = useState<TaskRow[]>([])
  const [targets, setTargets] = useState<TaskTargets | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const [statusFilter, setStatusFilter] = useState<string>(searchParams.get('status') || '')
  const [priorityFilter, setPriorityFilter] = useState<string>('')
  const [studentFilter, setStudentFilter] = useState<string>(searchParams.get('student_id') || '')
  const [courseFilter, setCourseFilter] = useState<string>(searchParams.get('course_id') || '')
  const [search, setSearch] = useState(searchParams.get('search') || '')
  const [sortBy, setSortBy] = useState<'due_at' | 'priority' | 'created_at' | 'updated_at'>('due_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')

  const [title, setTitle] = useState('')
  const [createStatus, setCreateStatus] = useState<'open' | 'in_progress' | 'done' | 'canceled'>('open')
  const [createPriority, setCreatePriority] = useState<'low' | 'medium' | 'high'>('medium')
  const [dueAt, setDueAt] = useState('')
  const [note, setNote] = useState('')
  const [linkedStudentId, setLinkedStudentId] = useState('')
  const [linkedCourseId, setLinkedCourseId] = useState('')

  async function loadTargets() {
    const data = await api.get<TaskTargets>('/tasks/targets')
    setTargets(data)
  }

  async function loadTasks() {
    const params = new URLSearchParams()
    if (statusFilter) params.set('status', statusFilter)
    if (priorityFilter) params.set('priority', priorityFilter)
    if (studentFilter) params.set('student_id', studentFilter)
    if (courseFilter) params.set('course_id', courseFilter)
    if (search.trim()) params.set('search', search.trim())
    params.set('sort_by', sortBy)
    params.set('sort_order', sortOrder)
    params.set('limit', '1000')
    const data = await api.get<TaskRow[]>(`/tasks/?${params.toString()}`)
    setTasks(data)
  }

  useEffect(() => {
    void Promise.all([loadTargets(), loadTasks()]).catch((err) => setError((err as Error).message))
  }, [])

  const taskStats = useMemo(() => {
    const open = tasks.filter((task) => task.status === 'open' || task.status === 'in_progress').length
    const dueSoon = tasks.filter((task) => {
      if (!task.due_at) return false
      const due = Date.parse(task.due_at)
      if (Number.isNaN(due)) return false
      return due <= Date.now() + 3 * 24 * 60 * 60 * 1000 && (task.status === 'open' || task.status === 'in_progress')
    }).length
    return { open, dueSoon }
  }, [tasks])

  function clearFilters() {
    setStatusFilter('')
    setPriorityFilter('')
    setStudentFilter('')
    setCourseFilter('')
    setSearch('')
    setSortBy('due_at')
    setSortOrder('asc')
    setError(null)
    setMessage(null)
  }

  async function createTask(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      await api.post('/tasks/', {
        title: title.trim(),
        status: createStatus,
        priority: createPriority,
        due_at: dateInputToIso(dueAt),
        note: note.trim() || null,
        linked_student_id: linkedStudentId ? Number(linkedStudentId) : null,
        linked_course_id: linkedCourseId ? Number(linkedCourseId) : null,
      })
      setTitle('')
      setCreateStatus('open')
      setCreatePriority('medium')
      setDueAt('')
      setNote('')
      setLinkedStudentId('')
      setLinkedCourseId('')
      await loadTasks()
      setMessage('Task created.')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function patchTask(taskId: number, payload: Record<string, unknown>) {
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      await api.patch(`/tasks/${taskId}`, payload)
      await loadTasks()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function removeTask(taskId: number) {
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      await api.delete(`/tasks/${taskId}`)
      await loadTasks()
      setMessage('Task deleted.')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  async function runRules() {
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      const result = await api.post<RuleRunResult>('/tasks/rules/run')
      await loadTasks()
      setMessage(
        `Rule engine evaluated ${result.evaluated_students} students and created ${result.created_count} tasks (${result.skipped_count} skipped duplicates).`,
      )
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section>
      <h2>Task Queue</h2>
      <p className="subtitle">Single-owner follow-up cockpit for advising and grading interventions.</p>

      <article className="card action-bar">
        <div className="gradebook-toolbar compact-grid">
          <div className="muted-badge">Open Tasks: {taskStats.open}</div>
          <div className="muted-badge">Due in 3 Days: {taskStats.dueSoon}</div>
          <button type="button" onClick={() => void runRules()} disabled={busy}>Run Intervention Rules</button>
          <button type="button" onClick={() => void loadTasks()} disabled={busy}>Refresh</button>
        </div>
      </article>

      <article className="card" style={{ marginTop: '0.8rem' }}>
        <h3>Create Task</h3>
        <form className="form gradebook-toolbar compact-grid" onSubmit={createTask}>
          <input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Task title" required />
          <select value={createStatus} onChange={(event) => setCreateStatus(event.target.value as typeof createStatus)}>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="done">Done</option>
            <option value="canceled">Canceled</option>
          </select>
          <select value={createPriority} onChange={(event) => setCreatePriority(event.target.value as typeof createPriority)}>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <input type="datetime-local" value={dueAt} onChange={(event) => setDueAt(event.target.value)} />
          <select value={linkedStudentId} onChange={(event) => setLinkedStudentId(event.target.value)}>
            <option value="">No linked student</option>
            {(targets?.students || []).map((student) => (
              <option key={student.id} value={student.id}>{student.name}</option>
            ))}
          </select>
          <select value={linkedCourseId} onChange={(event) => setLinkedCourseId(event.target.value)}>
            <option value="">No linked course</option>
            {(targets?.courses || []).map((course) => (
              <option key={course.id} value={course.id}>{course.name}</option>
            ))}
          </select>
          <input value={note} onChange={(event) => setNote(event.target.value)} placeholder="Optional note" />
          <button type="submit" disabled={busy}>{busy ? 'Saving...' : 'Create Task'}</button>
        </form>
      </article>

      <article className="card" style={{ marginTop: '0.8rem' }}>
        <h3>Filters</h3>
        <div className="gradebook-toolbar compact-grid">
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search title or notes" />
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="">All statuses</option>
            <option value="open">Open</option>
            <option value="in_progress">In Progress</option>
            <option value="done">Done</option>
            <option value="canceled">Canceled</option>
          </select>
          <select value={priorityFilter} onChange={(event) => setPriorityFilter(event.target.value)}>
            <option value="">All priorities</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <select value={studentFilter} onChange={(event) => setStudentFilter(event.target.value)}>
            <option value="">All students</option>
            {(targets?.students || []).map((student) => (
              <option key={student.id} value={student.id}>{student.name}</option>
            ))}
          </select>
          <select value={courseFilter} onChange={(event) => setCourseFilter(event.target.value)}>
            <option value="">All courses</option>
            {(targets?.courses || []).map((course) => (
              <option key={course.id} value={course.id}>{course.name}</option>
            ))}
          </select>
          <select value={sortBy} onChange={(event) => setSortBy(event.target.value as typeof sortBy)}>
            <option value="due_at">Sort: Due Date</option>
            <option value="priority">Sort: Priority</option>
            <option value="created_at">Sort: Created</option>
            <option value="updated_at">Sort: Updated</option>
          </select>
          <select value={sortOrder} onChange={(event) => setSortOrder(event.target.value as typeof sortOrder)}>
            <option value="asc">Ascending</option>
            <option value="desc">Descending</option>
          </select>
          <button type="button" onClick={() => void loadTasks()} disabled={busy}>Apply</button>
          <button type="button" onClick={clearFilters} disabled={busy}>Clear</button>
        </div>
      </article>

      <article className="card students-grid-wrap" style={{ marginTop: '0.8rem' }}>
        <table className="students-grid-table prioritize-mobile">
          <thead>
            <tr>
              <th>Task</th>
              <th>Status</th>
              <th>Priority</th>
              <th>Due</th>
              <th>Student</th>
              <th>Course</th>
              <th>Source</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {tasks.map((task) => {
              const student = targets?.students.find((item) => item.id === task.linked_student_id)
              const course = targets?.courses.find((item) => item.id === task.linked_course_id)
              return (
                <tr key={task.id}>
                  <td>
                    <strong>{task.title}</strong>
                    {task.note ? <div className="table-subtle">{task.note}</div> : null}
                  </td>
                  <td>
                    <select value={task.status} onChange={(event) => void patchTask(task.id, { status: event.target.value })}>
                      <option value="open">Open</option>
                      <option value="in_progress">In Progress</option>
                      <option value="done">Done</option>
                      <option value="canceled">Canceled</option>
                    </select>
                  </td>
                  <td>
                    <select value={task.priority} onChange={(event) => void patchTask(task.id, { priority: event.target.value })}>
                      <option value="high">High</option>
                      <option value="medium">Medium</option>
                      <option value="low">Low</option>
                    </select>
                  </td>
                  <td>
                    <input
                      type="datetime-local"
                      value={isoToDateInput(task.due_at)}
                      onChange={(event) => void patchTask(task.id, { due_at: dateInputToIso(event.target.value) })}
                    />
                  </td>
                  <td>
                    {task.linked_student_id && student ? (
                      <Link to={`/students/${task.linked_student_id}`}>{student.name}</Link>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td>{course?.name || '—'}</td>
                  <td>{task.source}</td>
                  <td>
                    <button type="button" onClick={() => void removeTask(task.id)} disabled={busy}>Delete</button>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
        {tasks.length === 0 ? <p>No tasks found for current filters.</p> : null}
      </article>

      {message ? <p>{message}</p> : null}
      {error ? <p className="error">{error}</p> : null}
    </section>
  )
}
