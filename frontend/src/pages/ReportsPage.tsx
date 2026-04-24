import { FormEvent, useEffect, useMemo, useState } from 'react'
import { api } from '../api/client'

type ReportStudent = {
  id: number
  name: string
  email?: string | null
}

type ReportRubric = {
  id: number
  name: string
}

type ReportAssignment = {
  id: number
  title: string
  course_id: number
}

type ReportTargets = {
  students: ReportStudent[]
  rubrics: ReportRubric[]
  assignments: ReportAssignment[]
}

type ReportPreview = {
  student_id: number
  student_name: string
  courses: string[]
  grade_overview: { course_name: string; earned: number; possible: number; percent?: number | null }[]
  attendance: Record<string, number>
  rubric_scope: {
    include_all_rubrics: boolean
    rubric_id?: number | null
    assignment_id?: number | null
  }
  rubric_evaluations: {
    id: number
    rubric_name?: string | null
    total_points?: number | null
    max_points?: number | null
    course_name?: string | null
    assignment_title?: string | null
    created_at: string
    evaluator_notes?: string | null
    items: {
      id: number
      criterion_title: string
      criterion_type?: string | null
      criterion_max_points?: number | null
      rating_title?: string | null
      rating_description?: string | null
      points_awarded?: number | null
      is_checked?: boolean | null
      narrative_comment?: string | null
    }[]
  }[]
  recent_interactions: { type: string; summary: string; occurred_at: string }[]
}

type ReportResult = {
  student_id: number
  pdf_path: string
  png_path: string
  pdf_url: string
  png_url: string
  rubric_evaluation_count: number
  interaction_count: number
}

type BulkReportResult = {
  created_count: number
  artifacts: {
    student_id: number
    student_name: string
    pdf_url: string
    png_url: string
  }[]
}

export function ReportsPage() {
  const [targets, setTargets] = useState<ReportTargets | null>(null)
  const [studentId, setStudentId] = useState('')
  const [includeAllRubrics, setIncludeAllRubrics] = useState(true)
  const [rubricId, setRubricId] = useState('')
  const [assignmentId, setAssignmentId] = useState('')

  const [preview, setPreview] = useState<ReportPreview | null>(null)
  const [reportResult, setReportResult] = useState<ReportResult | null>(null)
  const [bulkResult, setBulkResult] = useState<BulkReportResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)

  const selectedStudent = useMemo(
    () => targets?.students.find((student) => String(student.id) === studentId) || null,
    [targets, studentId]
  )

  async function loadTargets() {
    const rows = await api.get<ReportTargets>('/reports/targets')
    setTargets(rows)
    if (!studentId && rows.students.length > 0) {
      setStudentId(String(rows.students[0].id))
    }
  }

  async function loadPreview(targetStudentId: string) {
    if (!targetStudentId) return

    const params = new URLSearchParams()
    params.set('include_all_rubrics', includeAllRubrics ? 'true' : 'false')
    if (!includeAllRubrics && rubricId) params.set('rubric_id', rubricId)
    if (!includeAllRubrics && assignmentId) params.set('assignment_id', assignmentId)

    const response = await api.get<ReportPreview>(`/reports/students/${targetStudentId}/preview?${params.toString()}`)
    setPreview(response)
  }

  useEffect(() => {
    void loadTargets().catch((err) => setError((err as Error).message))
  }, [])

  useEffect(() => {
    if (studentId) {
      void loadPreview(studentId).catch((err) => setError((err as Error).message))
    }
  }, [studentId, includeAllRubrics, rubricId, assignmentId])

  async function generate(event: FormEvent) {
    event.preventDefault()
    if (!studentId) return

    setIsGenerating(true)
    setError(null)
    setBulkResult(null)

    try {
      const payload = {
        include_all_rubrics: includeAllRubrics,
        rubric_id: includeAllRubrics || !rubricId ? null : Number(rubricId),
        assignment_id: includeAllRubrics || !assignmentId ? null : Number(assignmentId),
      }
      const response = await api.post<ReportResult>(`/reports/students/${studentId}`, payload)
      setReportResult(response)
      await loadPreview(studentId)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setIsGenerating(false)
    }
  }

  async function generateAllStudentsAllRubrics() {
    setIsGenerating(true)
    setError(null)
    try {
      const response = await api.post<BulkReportResult>('/reports/students/bulk', {
        include_all_rubrics: true,
      })
      setBulkResult(response)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setIsGenerating(false)
    }
  }

  return (
    <section>
      <h2>Student Reports</h2>
      <p className="subtitle">Generate branded PDF + PNG exports. Scope by student + assignment/rubric, or run all students with all rubrics.</p>

      <article className="card">
        <h3>Generate Student Report</h3>
        <form className="form" onSubmit={generate}>
          <select value={studentId} onChange={(event) => setStudentId(event.target.value)} required>
            <option value="">Select student...</option>
            {targets?.students.map((student) => (
              <option key={student.id} value={student.id}>
                {student.name}
                {student.email ? ` (${student.email})` : ''}
              </option>
            ))}
          </select>

          <label>
            <input
              type="checkbox"
              checked={includeAllRubrics}
              onChange={(event) => setIncludeAllRubrics(event.target.checked)}
            />
            Include all rubrics for this student
          </label>

          {!includeAllRubrics ? (
            <>
              <select value={rubricId} onChange={(event) => setRubricId(event.target.value)}>
                <option value="">Any rubric</option>
                {targets?.rubrics.map((rubric) => (
                  <option key={rubric.id} value={rubric.id}>
                    {rubric.name}
                  </option>
                ))}
              </select>
              <select value={assignmentId} onChange={(event) => setAssignmentId(event.target.value)}>
                <option value="">Any assignment</option>
                {targets?.assignments.map((assignment) => (
                  <option key={assignment.id} value={assignment.id}>
                    {assignment.title}
                  </option>
                ))}
              </select>
            </>
          ) : null}

          <button type="submit" disabled={isGenerating || !studentId}>
            {isGenerating ? 'Generating...' : 'Generate Report'}
          </button>
        </form>
      </article>

      <article className="card" style={{ marginTop: '0.8rem' }}>
        <h3>Bulk Reports</h3>
        <p className="subtitle">Create one report per student including all rubrics.</p>
        <button type="button" onClick={() => void generateAllStudentsAllRubrics()} disabled={isGenerating}>
          {isGenerating ? 'Running...' : 'Generate All Students (All Rubrics)'}
        </button>
      </article>

      {reportResult ? (
        <article className="card" style={{ marginTop: '0.8rem' }}>
          <h3>Latest Export</h3>
          <div>Student: {selectedStudent?.name || studentId}</div>
          <div>
            PDF: <a href={reportResult.pdf_url} target="_blank" rel="noreferrer">Download PDF</a>
          </div>
          <div>
            PNG: <a href={reportResult.png_url} target="_blank" rel="noreferrer">Download PNG</a>
          </div>
          <div>Rubric evaluations included: {reportResult.rubric_evaluation_count}</div>
          <div>Recent interactions included: {reportResult.interaction_count}</div>
        </article>
      ) : null}

      {bulkResult ? (
        <article className="card" style={{ marginTop: '0.8rem' }}>
          <h3>Bulk Export Results</h3>
          <div>Created reports: {bulkResult.created_count}</div>
          <div className="students-grid-wrap" style={{ marginTop: '0.5rem' }}>
            <table className="students-grid-table">
              <thead>
                <tr>
                  <th>Student</th>
                  <th>PDF</th>
                  <th>PNG</th>
                </tr>
              </thead>
              <tbody>
                {bulkResult.artifacts.map((artifact) => (
                  <tr key={artifact.student_id}>
                    <td>{artifact.student_name}</td>
                    <td>
                      <a href={artifact.pdf_url} target="_blank" rel="noreferrer">Download PDF</a>
                    </td>
                    <td>
                      <a href={artifact.png_url} target="_blank" rel="noreferrer">Download PNG</a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </article>
      ) : null}

      {preview ? (
        <article className="card" style={{ marginTop: '0.8rem' }}>
          <h3>Preview Data</h3>
          <div><strong>Student:</strong> {preview.student_name}</div>
          <div><strong>Courses:</strong> {preview.courses.length > 0 ? preview.courses.join(', ') : 'None'}</div>
          <div>
            <strong>Rubric scope:</strong>{' '}
            {preview.rubric_scope.include_all_rubrics
              ? 'All rubrics'
              : `Filtered${preview.rubric_scope.rubric_id ? ` rubric #${preview.rubric_scope.rubric_id}` : ''}${preview.rubric_scope.assignment_id ? ` assignment #${preview.rubric_scope.assignment_id}` : ''}`}
          </div>

          <h4>Recent Rubric Evaluations</h4>
          <div className="rubric-report-stack">
            {preview.rubric_evaluations.length > 0 ? (
              preview.rubric_evaluations.slice(0, 8).map((evaluation) => (
                <section key={evaluation.id} className="rubric-report-block">
                  <header className="rubric-report-header">
                    <div>
                      <strong>{evaluation.rubric_name || 'Rubric'}</strong>
                      <span>{evaluation.assignment_title || evaluation.course_name || 'General'}</span>
                    </div>
                    <div className="rubric-score-pill">
                      {evaluation.total_points ?? 'N/A'}
                      {evaluation.max_points !== null && evaluation.max_points !== undefined ? ` / ${evaluation.max_points}` : ''}
                    </div>
                  </header>
                  <div className="rubric-report-meta">{evaluation.created_at.slice(0, 10)}</div>
                  <div className="rubric-report-grid">
                    {evaluation.items?.length > 0 ? (
                      evaluation.items.map((item) => (
                        <div key={item.id} className="rubric-report-row">
                          <div>
                            <strong>{item.criterion_title}</strong>
                            <span>{item.criterion_type || 'criterion'}</span>
                          </div>
                          <div>
                            <strong>{item.rating_title || (item.is_checked ? 'Checked' : 'No rating')}</strong>
                            <span>{item.rating_description || item.narrative_comment || 'No additional feedback'}</span>
                          </div>
                          <div className="rubric-report-points">
                            {item.points_awarded ?? 'N/A'}
                            {item.criterion_max_points !== null && item.criterion_max_points !== undefined ? ` / ${item.criterion_max_points}` : ''}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="rubric-report-row muted-row">No criterion-level details saved for this evaluation.</div>
                    )}
                  </div>
                  {evaluation.evaluator_notes ? <p className="rubric-report-notes">{evaluation.evaluator_notes}</p> : null}
                </section>
              ))
            ) : (
              <div className="card">No rubric evaluations for current scope.</div>
            )}
          </div>
        </article>
      ) : null}

      {error ? <p className="error">{error}</p> : null}
    </section>
  )
}
