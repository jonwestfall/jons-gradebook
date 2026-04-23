import { FormEvent, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'
import { readLocalStorage, writeLocalStorage } from '../utils/storage'

type Interaction = {
  id: number
  interaction_type: string
  custom_type?: string | null
  display_type?: string | null
  summary: string
  notes?: string | null
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

type SavedInteractionView = {
  name: string
  search: string
  startDate: string
  endDate: string
  filterType: string
  sortBy: 'occurred_at' | 'interaction_type' | 'summary' | 'id'
  sortOrder: 'asc' | 'desc'
  limit: number
}

const interactionTypeOptions = [
  { value: 'all', label: 'All Types' },
  { value: 'manual_note', label: 'Manual Note' },
  { value: 'office_visit', label: 'Office Visit' },
  { value: 'email_log', label: 'Email Log' },
  { value: 'attendance', label: 'Attendance' },
  { value: 'file_upload', label: 'File Upload' },
  { value: 'advising_meeting', label: 'Advising Meeting' },
]

const CORE_INTERACTION_LABEL_TO_VALUE: Record<string, string> = {
  'Manual Note': 'manual_note',
  'Office Visit': 'office_visit',
  'Email Log': 'email_log',
  Attendance: 'attendance',
  'File Upload': 'file_upload',
  'Advising Meeting': 'advising_meeting',
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
  const [isLoading, setIsLoading] = useState(false)

  const [search, setSearch] = useState('')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [filterType, setFilterType] = useState('all')
  const [configuredInteractionTypes, setConfiguredInteractionTypes] = useState<string[]>([])
  const [sortBy, setSortBy] = useState<'occurred_at' | 'interaction_type' | 'summary' | 'id'>('occurred_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [limit, setLimit] = useState(400)
  const [savedViews, setSavedViews] = useState<SavedInteractionView[]>([])
  const [viewName, setViewName] = useState('')

  const viewStorageKey = 'interactions_saved_views'

  async function loadTargets() {
    const targetRows = await api.get<InteractionTargets>('/interactions/targets')
    setTargets(targetRows)
    if (!targetId && targetRows.students.length > 0) {
      setTargetId(String(targetRows.students[0].id))
    }
  }

  async function loadSettings() {
    const settings = await api.get<{ interaction_categories: string[] }>('/settings/options')
    const categories = settings.interaction_categories || []
    setConfiguredInteractionTypes(categories)
    if (categories.length > 0 && !categories.includes(interactionType)) {
      setInteractionType(categories[0])
    }
  }

  function persistViews(next: SavedInteractionView[]) {
    setSavedViews(next)
    writeLocalStorage(viewStorageKey, JSON.stringify(next))
  }

  function saveCurrentView() {
    const name = viewName.trim()
    if (!name) return
    const withoutSame = savedViews.filter((view) => view.name.toLowerCase() !== name.toLowerCase())
    const nextView: SavedInteractionView = {
      name,
      search,
      startDate,
      endDate,
      filterType,
      sortBy,
      sortOrder,
      limit,
    }
    persistViews([nextView, ...withoutSame].slice(0, 12))
    setViewName('')
  }

  function applyView(view: SavedInteractionView) {
    setSearch(view.search)
    setStartDate(view.startDate)
    setEndDate(view.endDate)
    setFilterType(view.filterType)
    setSortBy(view.sortBy)
    setSortOrder(view.sortOrder)
    setLimit(view.limit)
    void loadInteractions({
      search: view.search,
      startDate: view.startDate,
      endDate: view.endDate,
      filterType: view.filterType,
      sortBy: view.sortBy,
      sortOrder: view.sortOrder,
      limit: view.limit,
    })
  }

  function deleteView(name: string) {
    const next = savedViews.filter((view) => view.name !== name)
    persistViews(next)
  }

  async function loadInteractions(
    overrides?: Partial<{
      search: string
      startDate: string
      endDate: string
      filterType: string
      sortBy: 'occurred_at' | 'interaction_type' | 'summary' | 'id'
      sortOrder: 'asc' | 'desc'
      limit: number
    }>
  ) {
    setIsLoading(true)
    setError(null)
    try {
      const nextSearch = overrides?.search ?? search
      const nextStartDate = overrides?.startDate ?? startDate
      const nextEndDate = overrides?.endDate ?? endDate
      const nextFilterType = overrides?.filterType ?? filterType
      const nextSortBy = overrides?.sortBy ?? sortBy
      const nextSortOrder = overrides?.sortOrder ?? sortOrder
      const nextLimit = overrides?.limit ?? limit

      const params = new URLSearchParams()
      if (nextSearch.trim()) params.set('search', nextSearch.trim())
      if (nextStartDate) params.set('start_date', nextStartDate)
      if (nextEndDate) params.set('end_date', nextEndDate)
      if (nextFilterType !== 'all') {
        const mappedType = CORE_INTERACTION_LABEL_TO_VALUE[nextFilterType] || nextFilterType
        if (Object.values(CORE_INTERACTION_LABEL_TO_VALUE).includes(mappedType)) {
          params.set('interaction_type', mappedType)
        } else {
          params.set('custom_type', nextFilterType)
        }
      }
      params.set('sort_by', nextSortBy)
      params.set('sort_order', nextSortOrder)
      params.set('limit', String(nextLimit))
      const rows = await api.get<Interaction[]>(`/interactions/?${params.toString()}`)
      setInteractions(rows)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void Promise.all([loadTargets(), loadInteractions(), loadSettings()])
    const raw = readLocalStorage(viewStorageKey)
    if (raw) {
      try {
        const parsed = JSON.parse(raw) as SavedInteractionView[]
        if (Array.isArray(parsed)) {
          setSavedViews(parsed)
        }
      } catch {
        // no-op
      }
    }
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
      const mappedType = CORE_INTERACTION_LABEL_TO_VALUE[interactionType] || interactionType
      const isCore = Object.values(CORE_INTERACTION_LABEL_TO_VALUE).includes(mappedType)
      await api.post('/interactions/bulk', {
        interaction_type: isCore ? mappedType : 'manual_note',
        custom_type: isCore ? null : interactionType,
        occurred_at: new Date().toISOString(),
        summary,
        notes,
        target_scope: targetScope,
        target_id: targetScope === 'advisees' ? null : Number(targetId),
      })
      setSummary('')
      setNotes('')
      await loadInteractions()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  function clearFilters() {
    setSearch('')
    setStartDate('')
    setEndDate('')
    setFilterType('all')
    setSortBy('occurred_at')
    setSortOrder('desc')
    setLimit(400)
  }

  return (
    <section>
      <h2>Interactions</h2>
      <p className="subtitle">Create notes for one student, everyone in a class, or all advisees. Filter and sort by dates/type to review past interactions.</p>

      <article className="card">
        <h3>Create Interaction</h3>
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
            {(configuredInteractionTypes.length > 0
              ? configuredInteractionTypes
              : interactionTypeOptions.filter((option) => option.value !== 'all').map((option) => option.label)
            ).map((label) => (
              <option key={label} value={label}>
                {label}
              </option>
            ))}
          </select>

          <input value={summary} onChange={(event) => setSummary(event.target.value)} placeholder="Interaction summary" required />
          <textarea value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="Notes (optional)" />
          <button type="submit">Create Interaction</button>
        </form>
      </article>

      <article className="card action-bar" style={{ marginTop: '0.8rem' }}>
        <h3>Find Interactions</h3>
        <div className="gradebook-toolbar compact-grid">
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search summary/notes" />
          <input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} />
          <input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} />
          <select value={filterType} onChange={(event) => setFilterType(event.target.value)}>
            <option value="all">All Types</option>
            {(configuredInteractionTypes.length > 0
              ? configuredInteractionTypes
              : interactionTypeOptions.filter((option) => option.value !== 'all').map((option) => option.label)
            ).map((label) => (
              <option key={label} value={label}>
                {label}
              </option>
            ))}
          </select>
          <select value={sortBy} onChange={(event) => setSortBy(event.target.value as 'occurred_at' | 'interaction_type' | 'summary' | 'id')}>
            <option value="occurred_at">Sort By Date</option>
            <option value="interaction_type">Sort By Type</option>
            <option value="summary">Sort By Summary</option>
            <option value="id">Sort By ID</option>
          </select>
          <select value={sortOrder} onChange={(event) => setSortOrder(event.target.value as 'asc' | 'desc')}>
            <option value="desc">Newest First</option>
            <option value="asc">Oldest First</option>
          </select>
          <input type="number" min={1} max={1000} value={limit} onChange={(event) => setLimit(Number(event.target.value) || 200)} placeholder="Limit" />
          <button type="button" onClick={() => void loadInteractions()} disabled={isLoading}>
            {isLoading ? 'Loading...' : 'Apply Filters'}
          </button>
          <button
            type="button"
            onClick={() => {
              clearFilters()
              void loadInteractions({
                search: '',
                startDate: '',
                endDate: '',
                filterType: 'all',
                sortBy: 'occurred_at',
                sortOrder: 'desc',
                limit: 400,
              })
            }}
          >
            Clear
          </button>
        </div>
        <div className="gradebook-toolbar compact-grid" style={{ marginTop: '0.5rem' }}>
          <input
            value={viewName}
            onChange={(event) => setViewName(event.target.value)}
            placeholder="Save this filter set as..."
          />
          <button type="button" onClick={saveCurrentView}>Save View</button>
        </div>
        <div className="chip-row" style={{ marginTop: '0.5rem' }}>
          {savedViews.map((view) => (
            <span key={view.name} className="chip">
              <button type="button" onClick={() => applyView(view)}>{view.name}</button>
              <button type="button" onClick={() => deleteView(view.name)} title={`Delete view ${view.name}`}>x</button>
            </span>
          ))}
          {savedViews.length === 0 ? <span className="table-subtle">No saved views yet.</span> : null}
        </div>
      </article>

      {error ? <p className="error">{error}</p> : null}

      <article className="card students-grid-wrap" style={{ marginTop: '0.8rem' }}>
        <table className="students-grid-table prioritize-mobile">
          <thead>
            <tr>
              <th>Date</th>
              <th>Type</th>
              <th>Target</th>
              <th>Summary</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            {interactions.map((interaction) => (
              <tr key={interaction.id}>
                <td>{new Date(interaction.occurred_at).toLocaleString()}</td>
                <td>{interaction.display_type || interaction.custom_type || interaction.interaction_type.replace('_', ' ')}</td>
                <td>
                  {interaction.advisee_name
                    ? `Advisee: ${interaction.advisee_name}`
                    : interaction.student_name
                      ? `Student: ${interaction.student_name}`
                      : 'General'}
                </td>
                <td>{interaction.summary}</td>
                <td>{interaction.notes || ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!isLoading && interactions.length === 0 ? <p>No interactions found for current filters.</p> : null}
      </article>
    </section>
  )
}
