import { ChangeEvent, DragEvent, FormEvent, useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api/client'

type RubricRating = {
  id: number
  title: string
  description?: string | null
  points?: number | null
  display_order: number
}

type RubricCriterionType = 'points' | 'checkbox' | 'narrative'

type RubricCriterion = {
  id: number
  title: string
  criterion_type: RubricCriterionType
  max_points?: number | null
  is_required: boolean
  prompt?: string | null
  display_order: number
  ratings: RubricRating[]
}

type Rubric = {
  id: number
  name: string
  description?: string | null
  max_points?: number | null
  archived_at?: string | null
  is_archived?: boolean
  evaluation_count?: number
  can_delete?: boolean
  criteria: RubricCriterion[]
}

type RubricTargets = {
  students: { id: number; name: string }[]
  courses: { id: number; name: string }[]
  assignments: { id: number; title: string; course_id: number }[]
}

type RubricEvaluation = {
  id: number
  rubric_id: number
  rubric_name?: string | null
  student_profile_id?: number | null
  student_name?: string | null
  course_id?: number | null
  course_name?: string | null
  assignment_id?: number | null
  assignment_title?: string | null
  total_points?: number | null
  created_at: string
}

type EvalDraftByCriterion = Record<
  number,
  {
    rating_id?: number
    points_awarded?: string
    is_checked?: boolean
    narrative_comment?: string
  }
>

type EditorTab = 'forms' | 'visual'

type RubricBackup = {
  version: 1
  exported_at: string
  rubrics: Rubric[]
}

function numberOrNull(value: string) {
  return value.trim() === '' ? null : Number(value)
}

function cloneRubric(rubric: Rubric): Rubric {
  return {
    ...rubric,
    criteria: rubric.criteria.map((criterion) => ({
      ...criterion,
      ratings: criterion.ratings.map((rating) => ({ ...rating })),
    })),
  }
}

function downloadJson(filename: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  URL.revokeObjectURL(url)
}

function filenameSafe(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '') || 'rubric'
}

export function RubricsPage() {
  const [rubrics, setRubrics] = useState<Rubric[]>([])
  const [archivedRubrics, setArchivedRubrics] = useState<Rubric[]>([])
  const [targets, setTargets] = useState<RubricTargets | null>(null)
  const [evaluations, setEvaluations] = useState<RubricEvaluation[]>([])
  const [error, setError] = useState<string | null>(null)
  const [editorTab, setEditorTab] = useState<EditorTab>('visual')
  const [rubricDraft, setRubricDraft] = useState<Rubric | null>(null)
  const [isDraftDirty, setIsDraftDirty] = useState(false)
  const [isSavingDraft, setIsSavingDraft] = useState(false)
  const [rubricMessage, setRubricMessage] = useState<string | null>(null)
  const [restoreInputKey, setRestoreInputKey] = useState(0)
  const draftIdRef = useRef(-1)

  const [newRubricName, setNewRubricName] = useState('')
  const [newRubricDescription, setNewRubricDescription] = useState('')
  const [newRubricMaxPoints, setNewRubricMaxPoints] = useState('')

  const [selectedRubricId, setSelectedRubricId] = useState('')
  const [draggedCriterionId, setDraggedCriterionId] = useState<number | null>(null)

  const [criterionTitle, setCriterionTitle] = useState('')
  const [criterionType, setCriterionType] = useState<RubricCriterionType>('points')
  const [criterionMaxPoints, setCriterionMaxPoints] = useState('')
  const [criterionRequired, setCriterionRequired] = useState(false)
  const [criterionPrompt, setCriterionPrompt] = useState('')

  const [ratingCriterionId, setRatingCriterionId] = useState('')
  const [ratingTitle, setRatingTitle] = useState('')
  const [ratingDescription, setRatingDescription] = useState('')
  const [ratingPoints, setRatingPoints] = useState('')

  const [evalStudentId, setEvalStudentId] = useState('')
  const [evalCourseId, setEvalCourseId] = useState('')
  const [evalAssignmentId, setEvalAssignmentId] = useState('')
  const [evalNotes, setEvalNotes] = useState('')
  const [evalDraftByCriterion, setEvalDraftByCriterion] = useState<EvalDraftByCriterion>({})

  const selectedRubric = useMemo(
    () => rubrics.find((rubric) => String(rubric.id) === selectedRubricId) || null,
    [rubrics, selectedRubricId],
  )

  const editorRubric = rubricDraft && String(rubricDraft.id) === selectedRubricId ? rubricDraft : selectedRubric

  const assignmentOptions = useMemo(() => {
    if (!targets) return []
    if (!evalCourseId) return targets.assignments
    return targets.assignments.filter((assignment) => String(assignment.course_id) === evalCourseId)
  }, [targets, evalCourseId])

  function nextDraftId() {
    const id = draftIdRef.current
    draftIdRef.current -= 1
    return id
  }

  function mergeRubric(updated: Rubric, options?: { resetDraft?: boolean }) {
    setRubrics((current) => current.map((rubric) => (rubric.id === updated.id ? updated : rubric)))
    if (options?.resetDraft || String(updated.id) === selectedRubricId) {
      setRubricDraft(cloneRubric(updated))
      setIsDraftDirty(false)
    }
  }

  function updateDraft(mutator: (draft: Rubric) => Rubric) {
    setRubricDraft((current) => {
      if (!current) return current
      return mutator(cloneRubric(current))
    })
    setIsDraftDirty(true)
    setRubricMessage(null)
  }

  async function loadRubrics() {
    const [rows, archivedRows] = await Promise.all([
      api.get<Rubric[]>('/rubrics/?archive_state=active'),
      api.get<Rubric[]>('/rubrics/?archive_state=archived'),
    ])
    setRubrics(rows)
    setArchivedRubrics(archivedRows)
    if (!selectedRubricId && rows.length > 0) {
      setSelectedRubricId(String(rows[0].id))
      setRatingCriterionId(rows[0].criteria[0] ? String(rows[0].criteria[0].id) : '')
    } else if (selectedRubricId && !rows.some((rubric) => String(rubric.id) === selectedRubricId)) {
      setSelectedRubricId(rows[0] ? String(rows[0].id) : '')
    }
    return rows
  }

  async function loadTargets() {
    const rows = await api.get<RubricTargets>('/rubrics/targets')
    setTargets(rows)
    if (!evalStudentId && rows.students.length > 0) setEvalStudentId(String(rows.students[0].id))
    if (!evalCourseId && rows.courses.length > 0) setEvalCourseId(String(rows.courses[0].id))
  }

  async function loadEvaluations(rubricId?: string) {
    const query = rubricId ? `?rubric_id=${rubricId}&limit=300` : '?limit=300'
    const rows = await api.get<RubricEvaluation[]>(`/rubrics/evaluations${query}`)
    setEvaluations(rows)
  }

  useEffect(() => {
    void Promise.all([loadRubrics(), loadTargets(), loadEvaluations()]).catch((err) => setError((err as Error).message))
  }, [])

  useEffect(() => {
    if (!selectedRubric) {
      setRubricDraft(null)
      setIsDraftDirty(false)
      return
    }

    setRubricDraft((current) => {
      if (current && current.id === selectedRubric.id) return current
      return cloneRubric(selectedRubric)
    })
    setIsDraftDirty((current) => (rubricDraft?.id === selectedRubric.id ? current : false))
  }, [selectedRubricId, selectedRubric])

  useEffect(() => {
    if (!selectedRubric) return
    if (selectedRubric.criteria.length > 0) {
      setRatingCriterionId((current) => {
        if (current && selectedRubric.criteria.some((criterion) => String(criterion.id) === current)) return current
        return String(selectedRubric.criteria[0].id)
      })
    } else {
      setRatingCriterionId('')
    }

    setEvalDraftByCriterion((current) => {
      const nextDraft: EvalDraftByCriterion = {}
      for (const criterion of selectedRubric.criteria) {
        nextDraft[criterion.id] = current[criterion.id] || {
          points_awarded: '',
          is_checked: false,
          narrative_comment: '',
        }
      }
      return nextDraft
    })
  }, [selectedRubric])

  async function createRubric(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      const created = await api.post<Rubric>('/rubrics/', {
        name: newRubricName,
        description: newRubricDescription || null,
        max_points: newRubricMaxPoints ? Number(newRubricMaxPoints) : null,
      })
      setNewRubricName('')
      setNewRubricDescription('')
      setNewRubricMaxPoints('')
      await loadRubrics()
      setSelectedRubricId(String(created.id))
      setRubricDraft(cloneRubric(created))
      setIsDraftDirty(false)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  function addCriterion(event?: FormEvent) {
    event?.preventDefault()
    if (!editorRubric) return
    const criterion: RubricCriterion = {
      id: nextDraftId(),
      title: criterionTitle || `Criterion ${editorRubric.criteria.length + 1}`,
      criterion_type: criterionType,
      max_points: criterionMaxPoints ? Number(criterionMaxPoints) : null,
      is_required: criterionRequired,
      prompt: criterionPrompt || null,
      display_order: editorRubric.criteria.length + 1,
      ratings: [],
    }
    updateDraft((draft) => ({
      ...draft,
      criteria: [...draft.criteria, criterion],
    }))
    setCriterionTitle('')
    setCriterionMaxPoints('')
    setCriterionRequired(false)
    setCriterionPrompt('')
    setRatingCriterionId(String(criterion.id))
  }

  function addRating(event?: FormEvent, criterionId = ratingCriterionId) {
    event?.preventDefault()
    if (!editorRubric || !criterionId) return
    updateDraft((draft) => ({
      ...draft,
      criteria: draft.criteria.map((criterion) => {
        if (String(criterion.id) !== String(criterionId)) return criterion
        const rating: RubricRating = {
          id: nextDraftId(),
          title: ratingTitle || `Level ${criterion.ratings.length + 1}`,
          description: ratingDescription || null,
          points: ratingPoints ? Number(ratingPoints) : null,
          display_order: criterion.ratings.length + 1,
        }
        return { ...criterion, ratings: [...criterion.ratings, rating] }
      }),
    }))
    setRatingTitle('')
    setRatingDescription('')
    setRatingPoints('')
  }

  function updateDraftCriterion(criterionId: number, updates: Partial<RubricCriterion>) {
    updateDraft((draft) => ({
      ...draft,
      criteria: draft.criteria.map((criterion) => (criterion.id === criterionId ? { ...criterion, ...updates } : criterion)),
    }))
  }

  function updateDraftRating(criterionId: number, ratingId: number, updates: Partial<RubricRating>) {
    updateDraft((draft) => ({
      ...draft,
      criteria: draft.criteria.map((criterion) =>
        criterion.id === criterionId
          ? {
              ...criterion,
              ratings: criterion.ratings.map((rating) => (rating.id === ratingId ? { ...rating, ...updates } : rating)),
            }
          : criterion,
      ),
    }))
  }

  function deleteDraftCriterion(criterionId: number) {
    updateDraft((draft) => ({
      ...draft,
      criteria: draft.criteria
        .filter((criterion) => criterion.id !== criterionId)
        .map((criterion, index) => ({ ...criterion, display_order: index + 1 })),
    }))
  }

  function deleteDraftRating(criterionId: number, ratingId: number) {
    updateDraft((draft) => ({
      ...draft,
      criteria: draft.criteria.map((criterion) =>
        criterion.id === criterionId
          ? {
              ...criterion,
              ratings: criterion.ratings
                .filter((rating) => rating.id !== ratingId)
                .map((rating, index) => ({ ...rating, display_order: index + 1 })),
            }
          : criterion,
      ),
    }))
  }

  function duplicateDraftCriterion(criterionId: number) {
    if (!editorRubric) return
    const source = editorRubric.criteria.find((criterion) => criterion.id === criterionId)
    if (!source) return

    const duplicate: RubricCriterion = {
      ...source,
      id: nextDraftId(),
      title: `${source.title} Copy`,
      ratings: source.ratings.map((rating, index) => ({
        ...rating,
        id: nextDraftId(),
        display_order: index + 1,
      })),
    }
    const sourceIndex = editorRubric.criteria.findIndex((criterion) => criterion.id === criterionId)
    updateDraft((draft) => {
      const nextCriteria = [...draft.criteria]
      nextCriteria.splice(sourceIndex + 1, 0, duplicate)
      return {
        ...draft,
        criteria: nextCriteria.map((criterion, index) => ({ ...criterion, display_order: index + 1 })),
      }
    })
  }

  function reorderCriterion(targetCriterionId: number) {
    if (!editorRubric || draggedCriterionId === null || draggedCriterionId === targetCriterionId) return

    const ordered = [...editorRubric.criteria]
    const fromIndex = ordered.findIndex((criterion) => criterion.id === draggedCriterionId)
    const toIndex = ordered.findIndex((criterion) => criterion.id === targetCriterionId)
    if (fromIndex < 0 || toIndex < 0) return

    const [moved] = ordered.splice(fromIndex, 1)
    ordered.splice(toIndex, 0, moved)
    updateDraft((draft) => ({
      ...draft,
      criteria: ordered.map((criterion, index) => ({ ...criterion, display_order: index + 1 })),
    }))
    setDraggedCriterionId(null)
  }

  async function saveVisualRubricDraft() {
    if (!selectedRubric || !rubricDraft) return
    setIsSavingDraft(true)
    setError(null)
    setRubricMessage(null)

    try {
      let serverRubric = selectedRubric
      const draft = cloneRubric(rubricDraft)
      const draftPersistedCriterionIds = new Set(draft.criteria.filter((criterion) => criterion.id > 0).map((criterion) => criterion.id))

      for (const criterion of serverRubric.criteria) {
        if (!draftPersistedCriterionIds.has(criterion.id)) {
          serverRubric = await api.delete<Rubric>(`/rubrics/${serverRubric.id}/criteria/${criterion.id}`)
        }
      }

      for (const [criterionIndex, draftCriterion] of draft.criteria.entries()) {
        let criterionId = draftCriterion.id
        if (criterionId > 0) {
          serverRubric = await api.patch<Rubric>(`/rubrics/${serverRubric.id}/criteria/${criterionId}`, {
            title: draftCriterion.title,
            criterion_type: draftCriterion.criterion_type,
            max_points: draftCriterion.max_points ?? null,
            is_required: draftCriterion.is_required,
            prompt: draftCriterion.prompt || null,
            display_order: criterionIndex + 1,
          })
        } else {
          const beforeIds = new Set(serverRubric.criteria.map((criterion) => criterion.id))
          serverRubric = await api.post<Rubric>(`/rubrics/${serverRubric.id}/criteria`, {
            title: draftCriterion.title,
            criterion_type: draftCriterion.criterion_type,
            max_points: draftCriterion.max_points ?? null,
            is_required: draftCriterion.is_required,
            prompt: draftCriterion.prompt || null,
            display_order: criterionIndex + 1,
          })
          const created = serverRubric.criteria.find((criterion) => !beforeIds.has(criterion.id))
          if (!created) throw new Error('Unable to match restored criterion after save')
          criterionId = created.id
          draftCriterion.id = created.id
        }

        const serverCriterion = serverRubric.criteria.find((criterion) => criterion.id === criterionId)
        const draftPersistedRatingIds = new Set(draftCriterion.ratings.filter((rating) => rating.id > 0).map((rating) => rating.id))
        for (const rating of serverCriterion?.ratings || []) {
          if (!draftPersistedRatingIds.has(rating.id)) {
            serverRubric = await api.delete<Rubric>(`/rubrics/${serverRubric.id}/criteria/${criterionId}/ratings/${rating.id}`)
          }
        }

        for (const [ratingIndex, draftRating] of draftCriterion.ratings.entries()) {
          if (draftRating.id > 0) {
            serverRubric = await api.patch<Rubric>(`/rubrics/${serverRubric.id}/criteria/${criterionId}/ratings/${draftRating.id}`, {
              title: draftRating.title,
              description: draftRating.description || null,
              points: draftRating.points ?? null,
              display_order: ratingIndex + 1,
            })
          } else {
            serverRubric = await api.post<Rubric>(`/rubrics/${serverRubric.id}/criteria/${criterionId}/ratings`, {
              title: draftRating.title,
              description: draftRating.description || null,
              points: draftRating.points ?? null,
              display_order: ratingIndex + 1,
            })
          }
        }
      }

      mergeRubric(serverRubric, { resetDraft: true })
      setRubricMessage('Rubric saved.')
      await loadEvaluations(String(serverRubric.id))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setIsSavingDraft(false)
    }
  }

  function exportRubrics(scope: 'selected' | 'all') {
    const payloadRubrics = scope === 'selected' && selectedRubric ? [selectedRubric] : rubrics
    const payload: RubricBackup = {
      version: 1,
      exported_at: new Date().toISOString(),
      rubrics: payloadRubrics.map(cloneRubric),
    }
    const name = scope === 'selected' && selectedRubric ? filenameSafe(selectedRubric.name) : 'all-rubrics'
    downloadJson(`jons-gradebook-${name}-backup.json`, payload)
  }

  async function restoreRubric(rubric: Rubric, existingNames: Set<string>) {
    let restoredName = rubric.name
    if (existingNames.has(restoredName)) restoredName = `${rubric.name} Restored`
    let suffix = 2
    while (existingNames.has(restoredName)) {
      restoredName = `${rubric.name} Restored ${suffix}`
      suffix += 1
    }
    existingNames.add(restoredName)

    let created = await api.post<Rubric>('/rubrics/', {
      name: restoredName,
      description: rubric.description || null,
      max_points: rubric.max_points ?? null,
    })

    for (const [criterionIndex, criterion] of rubric.criteria.entries()) {
      const beforeIds = new Set(created.criteria.map((row) => row.id))
      created = await api.post<Rubric>(`/rubrics/${created.id}/criteria`, {
        title: criterion.title,
        criterion_type: criterion.criterion_type,
        max_points: criterion.max_points ?? null,
        is_required: criterion.is_required,
        prompt: criterion.prompt || null,
        display_order: criterionIndex + 1,
      })
      const createdCriterion = created.criteria.find((row) => !beforeIds.has(row.id))
      if (!createdCriterion) throw new Error(`Unable to restore criterion "${criterion.title}"`)
      for (const [ratingIndex, rating] of criterion.ratings.entries()) {
        created = await api.post<Rubric>(`/rubrics/${created.id}/criteria/${createdCriterion.id}/ratings`, {
          title: rating.title,
          description: rating.description || null,
          points: rating.points ?? null,
          display_order: ratingIndex + 1,
        })
      }
    }

    return created
  }

  async function archiveSelectedRubric() {
    if (!selectedRubric) return
    setError(null)
    setRubricMessage(null)
    try {
      await api.post<Rubric>(`/rubrics/${selectedRubric.id}/archive`)
      setRubricMessage(`Archived ${selectedRubric.name}.`)
      setSelectedRubricId('')
      setRubricDraft(null)
      setIsDraftDirty(false)
      await loadRubrics()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  async function restoreArchivedRubric(rubric: Rubric) {
    setError(null)
    setRubricMessage(null)
    try {
      const restored = await api.post<Rubric>(`/rubrics/${rubric.id}/restore`)
      await loadRubrics()
      setSelectedRubricId(String(restored.id))
      setRubricDraft(cloneRubric(restored))
      setIsDraftDirty(false)
      setRubricMessage(`Restored ${restored.name}.`)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  async function deleteSelectedRubric() {
    if (!selectedRubric) return
    const confirmed = window.confirm(`Delete "${selectedRubric.name}" permanently? This cannot be undone.`)
    if (!confirmed) return

    setError(null)
    setRubricMessage(null)
    try {
      await api.delete<{ deleted: boolean; rubric_id: number }>(`/rubrics/${selectedRubric.id}`)
      setRubricMessage(`Deleted ${selectedRubric.name}.`)
      setSelectedRubricId('')
      setRubricDraft(null)
      setIsDraftDirty(false)
      await loadRubrics()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  async function restoreRubricsFromJson(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    if (!file) return
    setError(null)
    setRubricMessage(null)

    try {
      const parsed = JSON.parse(await file.text()) as unknown
      let restoredRubrics: Rubric[] = []
      if (Array.isArray(parsed)) {
        restoredRubrics = parsed as Rubric[]
      } else if (parsed && typeof parsed === 'object' && 'rubrics' in parsed && Array.isArray((parsed as { rubrics?: unknown }).rubrics)) {
        restoredRubrics = (parsed as { rubrics: Rubric[] }).rubrics
      } else if (parsed && typeof parsed === 'object' && 'name' in parsed) {
        restoredRubrics = [parsed as Rubric]
      }
      if (restoredRubrics.length === 0) throw new Error('No rubrics found in JSON file')

      const existingNames = new Set(rubrics.map((rubric) => rubric.name))
      let lastRestored: Rubric | null = null
      for (const rubric of restoredRubrics) {
        lastRestored = await restoreRubric(rubric, existingNames)
      }

      await loadRubrics()
      if (lastRestored) {
        setSelectedRubricId(String(lastRestored.id))
        setRubricDraft(cloneRubric(lastRestored))
        setIsDraftDirty(false)
      }
      setRubricMessage(`Restored ${restoredRubrics.length} rubric${restoredRubrics.length === 1 ? '' : 's'} from JSON.`)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setRestoreInputKey((current) => current + 1)
    }
  }

  async function submitEvaluation(event: FormEvent) {
    event.preventDefault()
    if (!selectedRubric) return
    setError(null)
    try {
      const items = selectedRubric.criteria.map((criterion) => {
        const draft = evalDraftByCriterion[criterion.id] || {}
        return {
          criterion_id: criterion.id,
          rating_id: draft.rating_id || null,
          points_awarded: draft.points_awarded ? Number(draft.points_awarded) : null,
          is_checked: draft.is_checked ?? false,
          narrative_comment: draft.narrative_comment || null,
        }
      })

      await api.post('/rubrics/evaluations', {
        rubric_id: selectedRubric.id,
        student_profile_id: evalStudentId ? Number(evalStudentId) : null,
        course_id: evalCourseId ? Number(evalCourseId) : null,
        assignment_id: evalAssignmentId ? Number(evalAssignmentId) : null,
        evaluator_notes: evalNotes || null,
        items,
      })

      setEvalNotes('')
      await loadEvaluations(selectedRubricId)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <section>
      <h2>Rubrics and Reporting</h2>
      <p className="subtitle">Canvas-style rubric templates with criteria/ratings, student scoring, and historical records.</p>

      <div className="rubric-admin-layout">
        <article className="card">
          <h3>Create Rubric Template</h3>
          <form className="form" onSubmit={createRubric}>
            <input value={newRubricName} onChange={(event) => setNewRubricName(event.target.value)} placeholder="Rubric name" required />
            <input value={newRubricDescription} onChange={(event) => setNewRubricDescription(event.target.value)} placeholder="Description (optional)" />
            <input
              type="number"
              step="0.01"
              min={0}
              value={newRubricMaxPoints}
              onChange={(event) => setNewRubricMaxPoints(event.target.value)}
              placeholder="Max points (optional)"
            />
            <button type="submit">Create Rubric</button>
          </form>
        </article>

        <article className="card">
          <h3>Select Rubric</h3>
          <select value={selectedRubricId} onChange={(event) => setSelectedRubricId(event.target.value)}>
            <option value="">Select rubric...</option>
            {rubrics.map((rubric) => (
              <option key={rubric.id} value={rubric.id}>
                {rubric.name}
              </option>
            ))}
          </select>
          {selectedRubric ? (
            <div className="rubric-summary">
              <strong>{selectedRubric.description || 'No description'}</strong>
              <span>{selectedRubric.criteria.length} criteria</span>
              <span>{selectedRubric.max_points ?? 'No'} max points</span>
              <span>{selectedRubric.evaluation_count ?? 0} evaluations</span>
              {isDraftDirty ? <span>Unsaved draft</span> : null}
            </div>
          ) : null}
          {selectedRubric ? (
            <div className="rubric-lifecycle-actions">
              <button type="button" className="secondary-button" onClick={() => void archiveSelectedRubric()}>
                Archive Rubric
              </button>
              {selectedRubric.can_delete ? (
                <button type="button" className="danger-button" onClick={() => void deleteSelectedRubric()}>
                  Delete Permanently
                </button>
              ) : (
                <span className="subtitle">Scored rubrics can be archived, but not deleted.</span>
              )}
            </div>
          ) : null}
        </article>

        <article className="card">
          <h3>Rubric Backup</h3>
          <div className="rubric-backup-actions">
            <button type="button" onClick={() => exportRubrics('selected')} disabled={!selectedRubric}>
              Export Selected JSON
            </button>
            <button type="button" onClick={() => exportRubrics('all')} disabled={rubrics.length === 0}>
              Export All JSON
            </button>
            <label className="file-button">
              Restore JSON
              <input key={restoreInputKey} type="file" accept="application/json,.json" onChange={(event) => void restoreRubricsFromJson(event)} />
            </label>
          </div>
          <p className="subtitle">Restore creates new rubric templates and keeps existing rubrics untouched.</p>
        </article>
      </div>

      <article className="card" style={{ marginTop: '0.8rem' }}>
        <div className="gradebook-toolbar compact-grid">
          <h3>Archived Rubrics</h3>
          <button type="button" className="secondary-button" onClick={() => void loadRubrics()}>
            Refresh Archive
          </button>
        </div>
        {archivedRubrics.length > 0 ? (
          <div className="archive-list">
            {archivedRubrics.map((rubric) => (
              <div key={rubric.id} className="archive-list-row">
                <div>
                  <strong>{rubric.name}</strong>
                  <span>
                    {rubric.criteria.length} criteria · {rubric.evaluation_count ?? 0} evaluations
                    {rubric.archived_at ? ` · Archived ${new Date(rubric.archived_at).toLocaleDateString()}` : ''}
                  </span>
                </div>
                <button type="button" onClick={() => void restoreArchivedRubric(rubric)}>
                  Restore
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="subtitle">No archived rubrics.</p>
        )}
      </article>

      {editorRubric ? (
        <>
          <article className="card rubric-editor-card">
            <div className="segmented-tabs" role="tablist" aria-label="Rubric editor mode">
              <button type="button" className={editorTab === 'visual' ? 'active' : ''} onClick={() => setEditorTab('visual')}>
                Visual Editor
              </button>
              <button type="button" className={editorTab === 'forms' ? 'active' : ''} onClick={() => setEditorTab('forms')}>
                Form Editor
              </button>
            </div>

            {editorTab === 'visual' ? (
              <div>
                <div className="rubric-editor-toolbar">
                  <button type="button" onClick={() => addCriterion()}>
                    Add Row
                  </button>
                  <span className="subtitle">Edits stay in a shared draft while you switch tabs. Use Save Rubric to write them to the database.</span>
                </div>

                <div className="visual-rubric-grid">
                  <div className="visual-rubric-head">
                    <span>Criterion</span>
                    <span>Rating Levels</span>
                    <span>Settings</span>
                  </div>
                  {editorRubric.criteria.length > 0 ? (
                    editorRubric.criteria.map((criterion) => (
                      <div
                        key={criterion.id}
                        className="visual-rubric-row"
                        onDragOver={(event) => event.preventDefault()}
                        onDrop={() => reorderCriterion(criterion.id)}
                      >
                        <div className="visual-rubric-criterion">
                          <button
                            type="button"
                            className="drag-handle"
                            title="Drag row"
                            aria-label={`Drag ${criterion.title}`}
                            draggable
                            onDragStart={(event: DragEvent<HTMLButtonElement>) => {
                              event.dataTransfer.effectAllowed = 'move'
                              setDraggedCriterionId(criterion.id)
                            }}
                          >
                            ::
                          </button>
                          <input
                            value={criterion.title}
                            onChange={(event) => updateDraftCriterion(criterion.id, { title: event.currentTarget.value })}
                            aria-label="Criterion title"
                          />
                          <textarea
                            value={criterion.prompt || ''}
                            onChange={(event) => updateDraftCriterion(criterion.id, { prompt: event.currentTarget.value || null })}
                            placeholder="Prompt / student-facing guidance"
                            aria-label="Criterion prompt"
                          />
                        </div>

                        <div className="visual-rubric-ratings">
                          {criterion.ratings.map((rating) => (
                            <div key={rating.id} className="rating-cell">
                              <div className="rating-cell-top">
                                <input
                                  value={rating.title}
                                  onChange={(event) => updateDraftRating(criterion.id, rating.id, { title: event.currentTarget.value })}
                                  aria-label="Rating title"
                                />
                                <button type="button" className="secondary-button" onClick={() => deleteDraftRating(criterion.id, rating.id)}>
                                  Remove
                                </button>
                              </div>
                              <textarea
                                value={rating.description || ''}
                                onChange={(event) => updateDraftRating(criterion.id, rating.id, { description: event.currentTarget.value || null })}
                                placeholder="Student-facing rating description"
                                aria-label="Rating description"
                              />
                              <input
                                type="number"
                                step="0.01"
                                value={rating.points ?? ''}
                                onChange={(event) => updateDraftRating(criterion.id, rating.id, { points: numberOrNull(event.currentTarget.value) })}
                                placeholder="Points"
                                aria-label="Rating points"
                              />
                            </div>
                          ))}
                          <button type="button" className="add-cell-button" onClick={() => addRating(undefined, String(criterion.id))}>
                            Add Rating
                          </button>
                        </div>

                        <div className="visual-rubric-settings">
                          <select
                            value={criterion.criterion_type}
                            onChange={(event) => updateDraftCriterion(criterion.id, { criterion_type: event.currentTarget.value as RubricCriterionType })}
                          >
                            <option value="points">Points</option>
                            <option value="checkbox">Checklist</option>
                            <option value="narrative">Narrative</option>
                          </select>
                          <input
                            type="number"
                            step="0.01"
                            value={criterion.max_points ?? ''}
                            onChange={(event) => updateDraftCriterion(criterion.id, { max_points: numberOrNull(event.currentTarget.value) })}
                            placeholder="Max"
                          />
                          <label className="inline-check">
                            <input
                              type="checkbox"
                              checked={criterion.is_required}
                              onChange={(event) => updateDraftCriterion(criterion.id, { is_required: event.currentTarget.checked })}
                            />
                            Required
                          </label>
                          <button type="button" className="secondary-button" onClick={() => duplicateDraftCriterion(criterion.id)}>
                            Duplicate Row
                          </button>
                          <button type="button" className="danger-button" onClick={() => deleteDraftCriterion(criterion.id)}>
                            Remove Row
                          </button>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="visual-empty">No rows yet. Add a criterion row to start building this rubric.</div>
                  )}
                </div>

                <div className="visual-save-bar">
                  <div>
                    <strong>{isDraftDirty ? 'Unsaved rubric draft' : 'Rubric draft matches the database'}</strong>
                    <span>{rubricMessage || 'Visual and form edits share the same draft.'}</span>
                  </div>
                  <button type="button" onClick={() => void saveVisualRubricDraft()} disabled={!isDraftDirty || isSavingDraft}>
                    {isSavingDraft ? 'Saving...' : 'Save Rubric'}
                  </button>
                </div>
              </div>
            ) : (
              <div className="gradebook-layout">
                <form className="form" onSubmit={(event) => addCriterion(event)}>
                  <h3>Add Criterion</h3>
                  <input value={criterionTitle} onChange={(event) => setCriterionTitle(event.target.value)} placeholder="Criterion title" required />
                  <select value={criterionType} onChange={(event) => setCriterionType(event.target.value as RubricCriterionType)}>
                    <option value="points">Points</option>
                    <option value="checkbox">Checklist</option>
                    <option value="narrative">Narrative</option>
                  </select>
                  <input type="number" step="0.01" min={0} value={criterionMaxPoints} onChange={(event) => setCriterionMaxPoints(event.target.value)} placeholder="Max points" />
                  <label>
                    <input type="checkbox" checked={criterionRequired} onChange={(event) => setCriterionRequired(event.target.checked)} /> Required
                  </label>
                  <input value={criterionPrompt} onChange={(event) => setCriterionPrompt(event.target.value)} placeholder="Prompt / guidance" />
                  <button type="submit">Add Criterion To Draft</button>
                </form>

                <form className="form" onSubmit={(event) => addRating(event)}>
                  <h3>Add Rating Level</h3>
                  <select value={ratingCriterionId} onChange={(event) => setRatingCriterionId(event.target.value)} required>
                    <option value="">Select criterion...</option>
                    {editorRubric.criteria.map((criterion) => (
                      <option key={criterion.id} value={criterion.id}>
                        {criterion.title}
                      </option>
                    ))}
                  </select>
                  <input value={ratingTitle} onChange={(event) => setRatingTitle(event.target.value)} placeholder="Rating title" required />
                  <input value={ratingDescription} onChange={(event) => setRatingDescription(event.target.value)} placeholder="Rating description" />
                  <input type="number" step="0.01" value={ratingPoints} onChange={(event) => setRatingPoints(event.target.value)} placeholder="Points" />
                  <button type="submit">Add Rating To Draft</button>
                </form>
              </div>
            )}
          </article>

          <article className="card" style={{ marginTop: '0.8rem' }}>
            <h3>Score with Rubric</h3>
            <form className="form" onSubmit={submitEvaluation}>
              <div className="gradebook-toolbar compact-grid">
                <select value={evalStudentId} onChange={(event) => setEvalStudentId(event.target.value)} required>
                  <option value="">Select student...</option>
                  {targets?.students.map((student) => (
                    <option key={student.id} value={student.id}>
                      {student.name}
                    </option>
                  ))}
                </select>
                <select value={evalCourseId} onChange={(event) => setEvalCourseId(event.target.value)}>
                  <option value="">No course</option>
                  {targets?.courses.map((course) => (
                    <option key={course.id} value={course.id}>
                      {course.name}
                    </option>
                  ))}
                </select>
                <select value={evalAssignmentId} onChange={(event) => setEvalAssignmentId(event.target.value)}>
                  <option value="">No assignment</option>
                  {assignmentOptions.map((assignment) => (
                    <option key={assignment.id} value={assignment.id}>
                      {assignment.title}
                    </option>
                  ))}
                </select>
              </div>

              <div className="students-grid-wrap">
                <table className="students-grid-table">
                  <thead>
                    <tr>
                      <th>Criterion</th>
                      <th>Rating</th>
                      <th>Points</th>
                      <th>Checked</th>
                      <th>Comment</th>
                    </tr>
                  </thead>
                  <tbody>
                    {selectedRubric?.criteria.map((criterion) => {
                      const draft = evalDraftByCriterion[criterion.id] || {}
                      return (
                        <tr key={criterion.id}>
                          <td>{criterion.title}</td>
                          <td>
                            <select
                              value={draft.rating_id || ''}
                              onChange={(event) =>
                                setEvalDraftByCriterion((prev) => ({
                                  ...prev,
                                  [criterion.id]: {
                                    ...prev[criterion.id],
                                    rating_id: event.target.value ? Number(event.target.value) : undefined,
                                  },
                                }))
                              }
                            >
                              <option value="">No rating</option>
                              {criterion.ratings.map((rating) => (
                                <option key={rating.id} value={rating.id}>
                                  {rating.title}
                                  {rating.points !== null && rating.points !== undefined ? ` (${rating.points})` : ''}
                                </option>
                              ))}
                            </select>
                          </td>
                          <td>
                            <input
                              type="number"
                              step="0.01"
                              value={draft.points_awarded || ''}
                              onChange={(event) =>
                                setEvalDraftByCriterion((prev) => ({
                                  ...prev,
                                  [criterion.id]: {
                                    ...prev[criterion.id],
                                    points_awarded: event.target.value,
                                  },
                                }))
                              }
                              placeholder={criterion.max_points !== null && criterion.max_points !== undefined ? `max ${criterion.max_points}` : ''}
                            />
                          </td>
                          <td>
                            <input
                              type="checkbox"
                              checked={Boolean(draft.is_checked)}
                              onChange={(event) =>
                                setEvalDraftByCriterion((prev) => ({
                                  ...prev,
                                  [criterion.id]: {
                                    ...prev[criterion.id],
                                    is_checked: event.target.checked,
                                  },
                                }))
                              }
                            />
                          </td>
                          <td>
                            <input
                              value={draft.narrative_comment || ''}
                              onChange={(event) =>
                                setEvalDraftByCriterion((prev) => ({
                                  ...prev,
                                  [criterion.id]: {
                                    ...prev[criterion.id],
                                    narrative_comment: event.target.value,
                                  },
                                }))
                              }
                              placeholder="Criterion comment"
                            />
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>

              <textarea value={evalNotes} onChange={(event) => setEvalNotes(event.target.value)} placeholder="Evaluator notes" />
              <button type="submit" disabled={isDraftDirty}>Save Rubric Evaluation</button>
              {isDraftDirty ? <p className="subtitle">Save the rubric draft before scoring with the latest changes.</p> : null}
            </form>
          </article>

          <article className="card" style={{ marginTop: '0.8rem' }}>
            <div className="gradebook-toolbar compact-grid">
              <h3>Evaluation History</h3>
              <button type="button" onClick={() => void loadEvaluations(selectedRubricId)}>
                Refresh History
              </button>
            </div>
            <div className="students-grid-wrap">
              <table className="students-grid-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Student</th>
                    <th>Course</th>
                    <th>Assignment</th>
                    <th>Total</th>
                  </tr>
                </thead>
                <tbody>
                  {evaluations.map((evaluation) => (
                    <tr key={evaluation.id}>
                      <td>{new Date(evaluation.created_at).toLocaleString()}</td>
                      <td>{evaluation.student_name || 'N/A'}</td>
                      <td>{evaluation.course_name || 'N/A'}</td>
                      <td>{evaluation.assignment_title || 'N/A'}</td>
                      <td>{evaluation.total_points ?? 'N/A'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {evaluations.length === 0 ? <p>No evaluations yet.</p> : null}
            </div>
          </article>
        </>
      ) : null}

      {error ? <p className="error">{error}</p> : null}
      {rubricMessage ? <p className="success">{rubricMessage}</p> : null}
    </section>
  )
}
