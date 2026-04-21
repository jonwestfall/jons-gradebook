import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'

type SyncRun = {
  id: number
  trigger_type: string
  status: string
  started_at: string
  finished_at?: string | null
  error_message?: string | null
}

type CanvasCourse = {
  canvas_course_id: string
  name: string
  course_code?: string | null
  term_name?: string | null
  term_start_at?: string | null
  term_end_at?: string | null
  is_selected: boolean
}

function formatDate(value?: string | null): string {
  if (!value) return 'N/A'
  return new Date(value).toLocaleDateString()
}

export function CanvasSyncPage() {
  const [runs, setRuns] = useState<SyncRun[]>([])
  const [courses, setCourses] = useState<CanvasCourse[]>([])
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set())
  const [loading, setLoading] = useState(false)
  const [discovering, setDiscovering] = useState(false)
  const [savingSelection, setSavingSelection] = useState(false)
  const [showCoursePicker, setShowCoursePicker] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selectedCount = useMemo(() => courses.filter((course) => course.is_selected).length, [courses])

  async function loadRuns() {
    const data = await api.get<SyncRun[]>('/canvas/sync/runs')
    setRuns(data)
  }

  async function discoverCourses(showPicker = false) {
    setDiscovering(true)
    setError(null)
    try {
      const data = await api.get<CanvasCourse[]>('/canvas/courses/discover')
      setCourses(data)
      setCheckedIds(new Set(data.filter((course) => course.is_selected).map((course) => course.canvas_course_id)))
      if (showPicker) {
        setShowCoursePicker(true)
      }
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setDiscovering(false)
    }
  }

  async function saveSelection(mode: 'replace' | 'add') {
    setSavingSelection(true)
    setError(null)
    try {
      await api.put('/canvas/courses/selected', {
        canvas_course_ids: Array.from(checkedIds),
        mode,
      })
      await discoverCourses(false)
      setShowCoursePicker(false)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSavingSelection(false)
    }
  }

  async function runManualSync() {
    setLoading(true)
    setError(null)
    try {
      await api.post('/canvas/sync', { trigger_type: 'manual', snapshot_label: 'Manual sync from UI' })
      await loadRuns()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }

  function toggleChecked(id: string) {
    setCheckedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  useEffect(() => {
    void loadRuns()
    void discoverCourses(false)
  }, [])

  return (
    <section>
      <h2>Canvas Sync</h2>
      <p>Choose the Canvas classes to import, then run sync to update only those selected classes.</p>

      <div className="card">
        <p>
          Selected classes: <strong>{selectedCount}</strong>
        </p>
        <button onClick={() => void discoverCourses(true)} disabled={discovering}>
          {discovering ? 'Loading classes...' : selectedCount === 0 ? 'Choose Classes' : 'Manage Classes'}
        </button>{' '}
        <button onClick={() => void discoverCourses(true)} disabled={discovering}>
          Add Classes
        </button>{' '}
        <button onClick={runManualSync} disabled={loading || selectedCount === 0}>
          {loading ? 'Syncing...' : 'Run Manual Sync'}
        </button>
        {selectedCount === 0 ? <p className="warning">No classes selected yet. Choose classes first.</p> : null}
      </div>

      {showCoursePicker ? (
        <article className="card">
          <h3>Select Canvas Classes</h3>
          <p>Canvas course list includes term details; choose classes to sync now and going forward.</p>
          <div className="list">
            {courses.map((course) => (
              <label key={course.canvas_course_id} className="card" style={{ display: 'block' }}>
                <input
                  type="checkbox"
                  checked={checkedIds.has(course.canvas_course_id)}
                  onChange={() => toggleChecked(course.canvas_course_id)}
                />{' '}
                <strong>{course.name}</strong>
                <div>Course ID: {course.canvas_course_id}</div>
                <div>Code: {course.course_code || 'N/A'}</div>
                <div>Term: {course.term_name || 'N/A'}</div>
                <div>
                  Dates: {formatDate(course.term_start_at)} - {formatDate(course.term_end_at)}
                </div>
              </label>
            ))}
          </div>
          <button onClick={() => void saveSelection('replace')} disabled={savingSelection}>
            {savingSelection ? 'Saving...' : 'Save Selection (Replace)'}
          </button>{' '}
          <button onClick={() => void saveSelection('add')} disabled={savingSelection}>
            {savingSelection ? 'Saving...' : 'Add Checked Classes'}
          </button>{' '}
          <button onClick={() => setShowCoursePicker(false)} disabled={savingSelection}>
            Cancel
          </button>
        </article>
      ) : null}

      {error ? <p className="error">{error}</p> : null}

      <ul className="list">
        {runs.map((run) => (
          <li key={run.id} className="card">
            <strong>Run #{run.id}</strong>
            <div>{run.trigger_type}</div>
            <div>Status: {run.status}</div>
            <div>Started: {new Date(run.started_at).toLocaleString()}</div>
            {run.finished_at ? <div>Finished: {new Date(run.finished_at).toLocaleString()}</div> : null}
            {run.error_message ? <div className="error">{run.error_message}</div> : null}
          </li>
        ))}
      </ul>
    </section>
  )
}
