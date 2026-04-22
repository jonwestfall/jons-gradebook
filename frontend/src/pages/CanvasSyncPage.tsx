import { useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'

type SyncRun = {
  id: number
  trigger_type: string
  status: string
  started_at: string
  finished_at?: string | null
  error_message?: string | null
  event_counts?: {
    created: number
    updated: number
    deleted: number
  }
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

type SyncEvent = {
  id: number
  entity_type: string
  action: string
  canvas_course_id?: string | null
  canvas_item_id?: string | null
  local_item_id?: number | null
  detail: Record<string, unknown>
  created_at: string
}

type SyncEventPage = {
  total: number
  offset: number
  limit: number
  events: SyncEvent[]
}

type SyncRunDetail = {
  id: number
  snapshot_counts: {
    courses: number
    assignments: number
    enrollments: number
    submissions: number
  }
  event_counts: {
    created: number
    updated: number
    deleted: number
  }
  recent_events: SyncEvent[]
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
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null)
  const [selectedRunDetail, setSelectedRunDetail] = useState<SyncRunDetail | null>(null)
  const [runEvents, setRunEvents] = useState<SyncEvent[]>([])
  const [runEventsTotal, setRunEventsTotal] = useState(0)
  const [runEventsOffset, setRunEventsOffset] = useState(0)
  const runEventsPageSize = 50
  const [eventActionFilter, setEventActionFilter] = useState<'all' | 'created' | 'updated' | 'deleted'>('all')
  const [eventEntityFilter, setEventEntityFilter] = useState<'all' | 'course' | 'enrollment' | 'assignment' | 'submission'>('all')

  const [loading, setLoading] = useState(false)
  const [discovering, setDiscovering] = useState(false)
  const [savingSelection, setSavingSelection] = useState(false)
  const [savingMappingField, setSavingMappingField] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [showCoursePicker, setShowCoursePicker] = useState(false)
  const [coursePickerMode, setCoursePickerMode] = useState<'replace' | 'add'>('replace')
  const [courseSearch, setCourseSearch] = useState('')
  const [courseTermFilter, setCourseTermFilter] = useState('all')
  const [coursePage, setCoursePage] = useState(1)
  const [error, setError] = useState<string | null>(null)

  const selectedCount = useMemo(() => courses.filter((course) => course.is_selected).length, [courses])
  const mappingTargets = ['first_name', 'last_name', 'email', 'student_number', 'institution_name'] as const
  const coursePageSize = 12

  const courseTermOptions = useMemo(() => {
    const terms = new Set<string>()
    courses.forEach((course) => {
      const term = (course.term_name || '').trim()
      if (term) terms.add(term)
    })
    return ['all', ...Array.from(terms).sort((a, b) => a.localeCompare(b))]
  }, [courses])

  const filteredCourses = useMemo(() => {
    const query = courseSearch.trim().toLowerCase()
    return courses.filter((course) => {
      if (courseTermFilter !== 'all' && (course.term_name || '') !== courseTermFilter) return false
      if (!query) return true
      const haystack = [course.name, course.course_code || '', course.term_name || '', course.canvas_course_id]
        .join(' ')
        .toLowerCase()
      return haystack.includes(query)
    })
  }, [courseSearch, courseTermFilter, courses])

  const pagedCourses = useMemo(() => {
    const start = (coursePage - 1) * coursePageSize
    return filteredCourses.slice(start, start + coursePageSize)
  }, [coursePage, filteredCourses])

  const coursePageCount = Math.max(1, Math.ceil(filteredCourses.length / coursePageSize))

  async function loadRuns() {
    const data = await api.get<SyncRun[]>('/canvas/sync/runs')
    setRuns(data)
    if (data.length > 0 && selectedRunId === null) {
      const newestId = data[0].id
      setSelectedRunId(newestId)
      await loadRunDetail(newestId)
    }
  }

  async function loadRunDetail(runId: number, offset = runEventsOffset) {
    const detail = await api.get<SyncRunDetail>(`/canvas/sync/runs/${runId}`)
    setSelectedRunDetail(detail)
    const params = new URLSearchParams()
    if (eventActionFilter !== 'all') params.set('action', eventActionFilter)
    if (eventEntityFilter !== 'all') params.set('entity_type', eventEntityFilter)
    const actionQuery = params.toString() ? `?${params.toString()}` : ''
    const separator = actionQuery ? '&' : '?'
    const page = await api.get<SyncEventPage>(
      `/canvas/sync/runs/${runId}/events${actionQuery}${separator}limit=${runEventsPageSize}&offset=${offset}`,
    )
    setRunEvents(page.events)
    setRunEventsTotal(page.total)
    setRunEventsOffset(page.offset)
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

  async function discoverCourses(showPicker = false, mode: 'replace' | 'add' = 'replace') {
    setDiscovering(true)
    setError(null)
    try {
      const data = await api.get<CanvasCourse[]>('/canvas/courses/discover')
      setCourses(data)
      setCheckedIds(new Set(data.filter((course) => course.is_selected).map((course) => course.canvas_course_id)))
      if (showPicker) {
        setCoursePickerMode(mode)
        setShowCoursePicker(true)
        setCoursePage(1)
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

  useEffect(() => {
    setCoursePage(1)
  }, [courseSearch, courseTermFilter])

  useEffect(() => {
    if (!selectedRunId) return
    void loadRunDetail(selectedRunId, 0)
  }, [selectedRunId, eventActionFilter, eventEntityFilter])

  function summarizeEventDetail(event: SyncEvent): string {
    const detail = event.detail || {}
    if (event.entity_type === 'assignment') {
      const title = typeof detail.title === 'string' ? detail.title : null
      const reason = typeof detail.reason === 'string' ? detail.reason : null
      if (title && reason) return `${title} (${reason})`
      if (title) return title
    }
    if (event.entity_type === 'enrollment') {
      const studentName = typeof detail.student_name === 'string' ? detail.student_name : null
      const reason = typeof detail.reason === 'string' ? detail.reason : null
      if (studentName && reason) return `${studentName} (${reason})`
      if (studentName) return studentName
    }
    if (event.entity_type === 'submission') {
      const status = typeof detail.status === 'string' ? detail.status : null
      const score = typeof detail.score === 'number' ? detail.score : null
      if (status && score !== null) return `status=${status}, score=${score}`
      if (status) return `status=${status}`
    }
    if (event.entity_type === 'course') {
      const name = typeof detail.name === 'string' ? detail.name : null
      if (name) return name
    }
    return JSON.stringify(detail)
  }

  return (
    <section>
      <h2>Canvas Sync</h2>
      <p>Choose the Canvas classes to import, then run sync to update only those selected classes.</p>

      <div className="card">
        <p>
          Selected classes: <strong>{selectedCount}</strong>
        </p>
        <button onClick={() => void discoverCourses(true, 'replace')} disabled={discovering}>
          {discovering ? 'Loading classes...' : selectedCount === 0 ? 'Choose Initial Classes' : 'Review / Replace Selection'}
        </button>{' '}
        <button onClick={() => void discoverCourses(true, 'add')} disabled={discovering}>
          Discover + Add More Classes
        </button>{' '}
        <button onClick={runManualSync} disabled={loading || selectedCount === 0}>
          {loading ? 'Syncing...' : 'Run Manual Sync'}
        </button>
        <p className="table-subtle">
          Review/Replace sets the exact persistent allowlist. Discover+Add keeps your existing allowlist and only adds
          newly checked classes.
        </p>
        {selectedCount === 0 ? <p className="warning">No classes selected yet. Choose classes first.</p> : null}
      </div>

      {showCoursePicker ? (
        <article className="card">
          <h3>Select Canvas Classes</h3>
          <p>
            {coursePickerMode === 'replace'
              ? 'Replace mode: checked classes become your persistent allowlist.'
              : 'Add mode: checked classes are added to your current allowlist; existing classes remain selected.'}
          </p>
          <div className="gradebook-toolbar compact-grid">
            <input
              value={courseSearch}
              onChange={(event) => setCourseSearch(event.target.value)}
              placeholder="Filter by course title, code, term, or ID"
            />
            <select value={courseTermFilter} onChange={(event) => setCourseTermFilter(event.target.value)}>
              {courseTermOptions.map((term) => (
                <option key={term} value={term}>
                  {term === 'all' ? 'All Terms' : term}
                </option>
              ))}
            </select>
            <div className="table-subtle">
              Showing {pagedCourses.length} of {filteredCourses.length} matching courses
            </div>
          </div>
          <div className="list">
            {pagedCourses.map((course) => (
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
            {pagedCourses.length === 0 ? <p>No courses match current filters.</p> : null}
          </div>
          <div className="gradebook-toolbar compact-grid">
            <button onClick={() => setCoursePage((prev) => Math.max(1, prev - 1))} disabled={coursePage <= 1}>
              Previous Page
            </button>
            <div className="table-subtle">
              Page {coursePage} of {coursePageCount}
            </div>
            <button
              onClick={() => setCoursePage((prev) => Math.min(coursePageCount, prev + 1))}
              disabled={coursePage >= coursePageCount}
            >
              Next Page
            </button>
          </div>
          <button onClick={() => void saveSelection('replace')} disabled={savingSelection}>
            {savingSelection ? 'Saving...' : 'Save Exact Selection (Replace)'}
          </button>{' '}
          <button onClick={() => void saveSelection('add')} disabled={savingSelection}>
            {savingSelection ? 'Saving...' : 'Add Checked Classes (Keep Existing)'}
          </button>{' '}
          <button onClick={() => setShowCoursePicker(false)} disabled={savingSelection}>
            Cancel
          </button>
        </article>
      ) : null}

      <details className="card" open>
        <summary><strong>Student Metadata Mapping</strong></summary>
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
      </details>

      <details className="card">
        <summary><strong>Canvas Metadata Preview</strong></summary>
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
      </details>

      {error ? <p className="error">{error}</p> : null}

      <details className="card" open>
        <summary><strong>Sync Runs</strong></summary>
        <ul className="list">
          {runs.map((run) => (
            <li key={run.id} className="card" style={{ cursor: 'pointer' }} onClick={() => setSelectedRunId(run.id)}>
              <strong>Run #{run.id}</strong>
              <div>{run.trigger_type}</div>
              <div>Status: {run.status}</div>
              <div>Started: {new Date(run.started_at).toLocaleString()}</div>
              {run.finished_at ? <div>Finished: {new Date(run.finished_at).toLocaleString()}</div> : null}
              {run.event_counts ? (
                <div>
                  Changes: +{run.event_counts.created} / ~{run.event_counts.updated} / -{run.event_counts.deleted}
                </div>
              ) : null}
              {run.error_message ? <div className="error">{run.error_message}</div> : null}
            </li>
          ))}
        </ul>
      </details>

      {selectedRunDetail ? (
        <article className="card">
          <h3>Import Audit Trail (Run #{selectedRunDetail.id})</h3>
          <p>
            Snapshots: courses {selectedRunDetail.snapshot_counts.courses}, assignments{' '}
            {selectedRunDetail.snapshot_counts.assignments}, enrollments {selectedRunDetail.snapshot_counts.enrollments},
            submissions {selectedRunDetail.snapshot_counts.submissions}
          </p>
          <p>
            Events: created {selectedRunDetail.event_counts.created}, updated {selectedRunDetail.event_counts.updated},
            deleted {selectedRunDetail.event_counts.deleted}
          </p>
          <div className="form">
            <label>
              Event Filter
              <select
                value={eventActionFilter}
                onChange={(event) =>
                  setEventActionFilter(event.target.value as 'all' | 'created' | 'updated' | 'deleted')
                }
              >
                <option value="all">All</option>
                <option value="created">Created</option>
                <option value="updated">Updated</option>
                <option value="deleted">Deleted</option>
              </select>
            </label>
            <label>
              Entity Filter
              <select
                value={eventEntityFilter}
                onChange={(event) =>
                  setEventEntityFilter(
                    event.target.value as 'all' | 'course' | 'enrollment' | 'assignment' | 'submission',
                  )
                }
              >
                <option value="all">All</option>
                <option value="course">Courses</option>
                <option value="enrollment">Enrollments</option>
                <option value="assignment">Assignments</option>
                <option value="submission">Submissions</option>
              </select>
            </label>
            <button
              onClick={() => {
                if (!selectedRunId) return
                const nextOffset = Math.max(0, runEventsOffset - runEventsPageSize)
                void loadRunDetail(selectedRunId, nextOffset)
              }}
              disabled={!selectedRunId || runEventsOffset === 0}
            >
              Newer
            </button>
            <button
              onClick={() => {
                if (!selectedRunId) return
                const nextOffset = runEventsOffset + runEventsPageSize
                if (nextOffset >= runEventsTotal) return
                void loadRunDetail(selectedRunId, nextOffset)
              }}
              disabled={!selectedRunId || runEventsOffset + runEventsPageSize >= runEventsTotal}
            >
              Older
            </button>
          </div>
          <p>
            Showing {runEvents.length} of {runEventsTotal} events
          </p>
          <p>
            Deleted enrollment events indicate Canvas no longer returns that enrollment; deleted assignment events mean
            Canvas removed or unpublished it and the local Canvas-linked assignment is archived/hidden.
          </p>
          <div className="card" style={{ overflow: 'auto', maxHeight: '360px' }}>
            <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 860 }}>
              <thead>
                <tr>
                  <th style={{ textAlign: 'left', padding: '0.35rem' }}>Time</th>
                  <th style={{ textAlign: 'left', padding: '0.35rem' }}>Entity</th>
                  <th style={{ textAlign: 'left', padding: '0.35rem' }}>Action</th>
                  <th style={{ textAlign: 'left', padding: '0.35rem' }}>Canvas IDs</th>
                  <th style={{ textAlign: 'left', padding: '0.35rem' }}>Details</th>
                </tr>
              </thead>
              <tbody>
                {runEvents.map((event) => (
                  <tr key={event.id}>
                    <td style={{ borderTop: '1px solid #d5c8aa', padding: '0.35rem', whiteSpace: 'nowrap' }}>
                      {new Date(event.created_at).toLocaleString()}
                    </td>
                    <td style={{ borderTop: '1px solid #d5c8aa', padding: '0.35rem' }}>{event.entity_type}</td>
                    <td style={{ borderTop: '1px solid #d5c8aa', padding: '0.35rem' }}>{event.action}</td>
                    <td style={{ borderTop: '1px solid #d5c8aa', padding: '0.35rem' }}>
                      {event.canvas_course_id || '—'} / {event.canvas_item_id || '—'}
                    </td>
                    <td style={{ borderTop: '1px solid #d5c8aa', padding: '0.35rem' }}>
                      {summarizeEventDetail(event)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      ) : null}
    </section>
  )
}
