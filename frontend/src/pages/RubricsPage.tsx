import { FormEvent, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'

type RubricRating = {
  id: number
  title: string
  description?: string | null
  points?: number | null
  display_order: number
}

type RubricCriterion = {
  id: number
  title: string
  criterion_type: 'points' | 'checkbox' | 'narrative'
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

export function RubricsPage() {
  const [rubrics, setRubrics] = useState<Rubric[]>([])
  const [targets, setTargets] = useState<RubricTargets | null>(null)
  const [evaluations, setEvaluations] = useState<RubricEvaluation[]>([])
  const [error, setError] = useState<string | null>(null)

  const [newRubricName, setNewRubricName] = useState('')
  const [newRubricDescription, setNewRubricDescription] = useState('')
  const [newRubricMaxPoints, setNewRubricMaxPoints] = useState('')

  const [selectedRubricId, setSelectedRubricId] = useState('')

  const [criterionTitle, setCriterionTitle] = useState('')
  const [criterionType, setCriterionType] = useState<'points' | 'checkbox' | 'narrative'>('points')
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
    [rubrics, selectedRubricId]
  )

  const assignmentOptions = useMemo(() => {
    if (!targets) return []
    if (!evalCourseId) return targets.assignments
    return targets.assignments.filter((assignment) => String(assignment.course_id) === evalCourseId)
  }, [targets, evalCourseId])

  async function loadRubrics() {
    const rows = await api.get<Rubric[]>('/rubrics/')
    setRubrics(rows)
    if (!selectedRubricId && rows.length > 0) {
      setSelectedRubricId(String(rows[0].id))
      setRatingCriterionId(rows[0].criteria[0] ? String(rows[0].criteria[0].id) : '')
    }
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
    if (!selectedRubric) return
    if (selectedRubric.criteria.length > 0) {
      setRatingCriterionId((current) => {
        if (current && selectedRubric.criteria.some((criterion) => String(criterion.id) === current)) return current
        return String(selectedRubric.criteria[0].id)
      })
    } else {
      setRatingCriterionId('')
    }

    const nextDraft: EvalDraftByCriterion = {}
    for (const criterion of selectedRubric.criteria) {
      nextDraft[criterion.id] = evalDraftByCriterion[criterion.id] || {
        points_awarded: '',
        is_checked: false,
        narrative_comment: '',
      }
    }
    setEvalDraftByCriterion(nextDraft)
  }, [selectedRubric])

  async function createRubric(event: FormEvent) {
    event.preventDefault()
    setError(null)
    try {
      await api.post('/rubrics/', {
        name: newRubricName,
        description: newRubricDescription || null,
        max_points: newRubricMaxPoints ? Number(newRubricMaxPoints) : null,
      })
      setNewRubricName('')
      setNewRubricDescription('')
      setNewRubricMaxPoints('')
      await loadRubrics()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  async function addCriterion(event: FormEvent) {
    event.preventDefault()
    if (!selectedRubricId) return
    setError(null)
    try {
      await api.post(`/rubrics/${selectedRubricId}/criteria`, {
        title: criterionTitle,
        criterion_type: criterionType,
        max_points: criterionMaxPoints ? Number(criterionMaxPoints) : null,
        is_required: criterionRequired,
        prompt: criterionPrompt || null,
      })
      setCriterionTitle('')
      setCriterionMaxPoints('')
      setCriterionRequired(false)
      setCriterionPrompt('')
      await loadRubrics()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  async function addRating(event: FormEvent) {
    event.preventDefault()
    if (!selectedRubricId || !ratingCriterionId) return
    setError(null)
    try {
      await api.post(`/rubrics/${selectedRubricId}/criteria/${ratingCriterionId}/ratings`, {
        title: ratingTitle,
        description: ratingDescription || null,
        points: ratingPoints ? Number(ratingPoints) : null,
      })
      setRatingTitle('')
      setRatingDescription('')
      setRatingPoints('')
      await loadRubrics()
    } catch (err) {
      setError((err as Error).message)
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
      <p className="subtitle">Canvas-style rubric templates with criteria/ratings, then evaluate students and keep historical scoring records.</p>

      <div className="gradebook-layout">
        <article className="card">
          <h3>Create Rubric Template</h3>
          <form className="form" onSubmit={createRubric}>
            <input value={newRubricName} onChange={(event) => setNewRubricName(event.target.value)} placeholder="Rubric name" required />
            <input
              value={newRubricDescription}
              onChange={(event) => setNewRubricDescription(event.target.value)}
              placeholder="Description (optional)"
            />
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
            <div style={{ marginTop: '0.55rem' }}>
              <div><strong>Description:</strong> {selectedRubric.description || 'None'}</div>
              <div><strong>Max points:</strong> {selectedRubric.max_points ?? 'N/A'}</div>
              <div><strong>Criteria:</strong> {selectedRubric.criteria.length}</div>
            </div>
          ) : null}
        </article>
      </div>

      {selectedRubric ? (
        <>
          <div className="gradebook-layout" style={{ marginTop: '0.8rem' }}>
            <article className="card">
              <h3>Add Criterion</h3>
              <form className="form" onSubmit={addCriterion}>
                <input value={criterionTitle} onChange={(event) => setCriterionTitle(event.target.value)} placeholder="Criterion title" required />
                <select value={criterionType} onChange={(event) => setCriterionType(event.target.value as 'points' | 'checkbox' | 'narrative')}>
                  <option value="points">Points</option>
                  <option value="checkbox">Checklist</option>
                  <option value="narrative">Narrative</option>
                </select>
                <input
                  type="number"
                  step="0.01"
                  min={0}
                  value={criterionMaxPoints}
                  onChange={(event) => setCriterionMaxPoints(event.target.value)}
                  placeholder="Max points (optional)"
                />
                <label>
                  <input type="checkbox" checked={criterionRequired} onChange={(event) => setCriterionRequired(event.target.checked)} /> Required
                </label>
                <input value={criterionPrompt} onChange={(event) => setCriterionPrompt(event.target.value)} placeholder="Prompt / guidance" />
                <button type="submit">Add Criterion</button>
              </form>
            </article>

            <article className="card">
              <h3>Add Rating Level</h3>
              <form className="form" onSubmit={addRating}>
                <select value={ratingCriterionId} onChange={(event) => setRatingCriterionId(event.target.value)} required>
                  <option value="">Select criterion...</option>
                  {selectedRubric.criteria.map((criterion) => (
                    <option key={criterion.id} value={criterion.id}>
                      {criterion.title}
                    </option>
                  ))}
                </select>
                <input value={ratingTitle} onChange={(event) => setRatingTitle(event.target.value)} placeholder="Rating title (e.g., Proficient)" required />
                <input value={ratingDescription} onChange={(event) => setRatingDescription(event.target.value)} placeholder="Rating description" />
                <input
                  type="number"
                  step="0.01"
                  value={ratingPoints}
                  onChange={(event) => setRatingPoints(event.target.value)}
                  placeholder="Points (optional)"
                />
                <button type="submit">Add Rating</button>
              </form>
            </article>
          </div>

          <article className="card" style={{ marginTop: '0.8rem' }}>
            <h3>Current Rubric Structure</h3>
            <div className="students-grid-wrap">
              <table className="students-grid-table">
                <thead>
                  <tr>
                    <th>Criterion</th>
                    <th>Type</th>
                    <th>Max</th>
                    <th>Required</th>
                    <th>Prompt</th>
                    <th>Ratings</th>
                  </tr>
                </thead>
                <tbody>
                  {selectedRubric.criteria.map((criterion) => (
                    <tr key={criterion.id}>
                      <td>{criterion.title}</td>
                      <td>{criterion.criterion_type}</td>
                      <td>{criterion.max_points ?? 'N/A'}</td>
                      <td>{criterion.is_required ? 'Yes' : 'No'}</td>
                      <td>{criterion.prompt || ''}</td>
                      <td>
                        {criterion.ratings.length > 0
                          ? criterion.ratings.map((rating) => `${rating.title}${rating.points !== null && rating.points !== undefined ? ` (${rating.points})` : ''}`).join(', ')
                          : 'No ratings'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
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
                    {selectedRubric.criteria.map((criterion) => {
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
              <button type="submit">Save Rubric Evaluation</button>
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
    </section>
  )
}
