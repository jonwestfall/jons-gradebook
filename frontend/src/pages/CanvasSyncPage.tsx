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

type StudentMapping = {
  target_field: string
  source_paths: string[]
  default_source_paths: string[]
}

type StudentMappingResponse = {
  mappings: StudentMapping[]
  common_source_paths: string[]
}

type MetadataPreview = {
  canvas_course_id: string
  sample_count: number
  labels: { source_path: string; sample_values: string[] }[]
  rows: {
    canvas_user_id: string
    name: string
    sample_values: Record<string, string>
  }[]
}

function formatDate(value?: string | null): string {
  if (!value) return 'N/A'
  return new Date(value).toLocaleDateString()
}

export function CanvasSyncPage() {
  const [runs, setRuns] = useState<SyncRun[]>([])
  const [courses, setCourses] = useState<CanvasCourse[]>([])
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set())
  const [mappingData, setMappingData] = useState<StudentMappingResponse | null>(null)
  const [mappingDrafts, setMappingDrafts] = useState<Record<string, string>>({})
  const [metadataPreview, setMetadataPreview] = useState<MetadataPreview | null>(null)
  const [previewCourseId, setPreviewCourseId] = useState<string>('')

  const [loading, setLoading] = useState(false)
  const [discovering, setDiscovering] = useState(false)
  const [savingSelection, setSavingSelection] = useState(false)
  const [savingMappingField, setSavingMappingField] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [showCoursePicker, setShowCoursePicker] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const selectedCount = useMemo(() => courses.filter((course) => course.is_selected).length, [courses])
  const mappingTargets = ['first_name', 'last_name', 'email', 'student_number', 'institution_name'] as const

  async function loadRuns() {
    const data = await api.get<SyncRun[]>('/canvas/sync/runs')
    setRuns(data)
  }

  async function loadStudentMapping() {
    const data = await api.get<StudentMappingResponse>('/canvas/student-metadata/mapping')
    setMappingData(data)
    setMappingDrafts(
      Object.fromEntries(data.mappings.map((mapping) => [mapping.target_field, mapping.source_paths.join(', ')])),
    )
  }

  async function loadMetadataPreview(targetCourseId?: string) {
    setPreviewLoading(true)
    setError(null)
    try {
      const query = targetCourseId ? `?canvas_course_id=${encodeURIComponent(targetCourseId)}` : ''
      const data = await api.get<MetadataPreview>(`/canvas/student-metadata/preview${query}`)
      setMetadataPreview(data)
      setPreviewCourseId(data.canvas_course_id)
    } catch (err) {
      setMetadataPreview(null)
      setError((err as Error).message)
    } finally {
      setPreviewLoading(false)
    }
  }

  async function saveStudentMapping(targetField: string) {
    setSavingMappingField(targetField)
    setError(null)
    try {
      const raw = mappingDrafts[targetField] || ''
      const sourcePaths = raw
        .split(',')
        .map((value) => value.trim())
        .filter(Boolean)

      await api.put('/canvas/student-metadata/mapping', {
        target_field: targetField,
        source_paths: sourcePaths,
      })

      await loadStudentMapping()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSavingMappingField(null)
    }
  }

  async function applyPreviewPathToTarget(targetField: string, sourcePath: string) {
    setSavingMappingField(targetField)
    setError(null)
    try {
      const existingRaw = mappingDrafts[targetField] || ''
      const existing = existingRaw
        .split(',')
        .map((value) => value.trim())
        .filter(Boolean)

      const nextPaths = [sourcePath, ...existing.filter((value) => value !== sourcePath)]
      setMappingDrafts((prev) => ({ ...prev, [targetField]: nextPaths.join(', ') }))

      await api.put('/canvas/student-metadata/mapping', {
        target_field: targetField,
        source_paths: nextPaths,
      })

      await loadStudentMapping()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSavingMappingField(null)
    }
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
    void loadStudentMapping()
    void loadMetadataPreview()
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

      <article className="card">
        <h3>Student Metadata Mapping</h3>
        <p>
          Configure how Canvas student metadata maps to local student columns. Use comma-separated source paths in
          priority order.
        </p>
        {mappingData ? (
          <>
            <p>Common source paths: {mappingData.common_source_paths.join(', ')}</p>
            <div className="list">
              {mappingData.mappings.map((mapping) => (
                <div key={mapping.target_field} className="card">
                  <strong>{mapping.target_field}</strong>
                  <div>Default: {mapping.default_source_paths.join(', ')}</div>
                  <input
                    value={mappingDrafts[mapping.target_field] || ''}
                    onChange={(event) =>
                      setMappingDrafts((prev) => ({ ...prev, [mapping.target_field]: event.target.value }))
                    }
                    placeholder="user.email, user.primary_email"
                  />
                  <button
                    onClick={() => void saveStudentMapping(mapping.target_field)}
                    disabled={savingMappingField === mapping.target_field}
                  >
                    {savingMappingField === mapping.target_field ? 'Saving...' : 'Save Mapping'}
                  </button>
                </div>
              ))}
            </div>
          </>
        ) : (
          <p>Loading mapping configuration...</p>
        )}
      </article>

      <article className="card">
        <h3>Canvas Metadata Preview</h3>
        <p>
          Preview raw metadata labels from your Canvas enrollment payload so you can choose reliable mapping paths for
          this installation.
        </p>
        <div className="form">
          <select
            value={previewCourseId}
            onChange={(event) => {
              const nextCourseId = event.target.value
              setPreviewCourseId(nextCourseId)
            }}
          >
            {courses.length === 0 ? <option value="">No discovered courses</option> : null}
            {courses.map((course) => (
              <option key={`preview-${course.canvas_course_id}`} value={course.canvas_course_id}>
                {course.name} ({course.canvas_course_id})
              </option>
            ))}
          </select>
          <button
            onClick={() => void loadMetadataPreview(previewCourseId || undefined)}
            disabled={previewLoading || courses.length === 0}
          >
            {previewLoading ? 'Loading Preview...' : 'Refresh Preview'}
          </button>
        </div>
        {metadataPreview ? (
          <>
            <p>
              Preview course ID: <strong>{metadataPreview.canvas_course_id}</strong> | Student samples:{' '}
              <strong>{metadataPreview.sample_count}</strong>
            </p>
            <div className="card" style={{ overflow: 'auto', maxHeight: '340px' }}>
              <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 760 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: '0.45rem' }}>Canvas Metadata Label</th>
                    <th style={{ textAlign: 'left', padding: '0.45rem' }}>Sample Values</th>
                    <th style={{ textAlign: 'left', padding: '0.45rem' }}>Quick Mapping</th>
                  </tr>
                </thead>
                <tbody>
                  {metadataPreview.labels.map((label) => (
                    <tr key={label.source_path}>
                      <td style={{ borderTop: '1px solid #d5c8aa', padding: '0.45rem', fontFamily: 'monospace' }}>
                        {label.source_path}
                      </td>
                      <td style={{ borderTop: '1px solid #d5c8aa', padding: '0.45rem' }}>
                        {label.sample_values.length > 0 ? label.sample_values.join(' | ') : '—'}
                      </td>
                      <td style={{ borderTop: '1px solid #d5c8aa', padding: '0.45rem' }}>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.35rem' }}>
                          {mappingTargets.map((targetField) => (
                            <button
                              key={`${label.source_path}-${targetField}`}
                              onClick={() => void applyPreviewPathToTarget(targetField, label.source_path)}
                              disabled={savingMappingField === targetField}
                              style={{ padding: '0.25rem 0.5rem', fontSize: '0.82rem' }}
                            >
                              {savingMappingField === targetField ? 'Saving...' : `Use for ${targetField}`}
                            </button>
                          ))}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          <p>No metadata preview loaded yet.</p>
        )}
      </article>

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
